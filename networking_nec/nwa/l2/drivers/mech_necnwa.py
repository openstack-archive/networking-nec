# Copyright 2015-2016 NEC Corporation.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from neutron.common import constants as neutron_const
from neutron.common import utils
from neutron.extensions import portbindings
from neutron.extensions import providernet as prov_net
from neutron.plugins.common import constants as plugin_const
from neutron.plugins.ml2 import db
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2.drivers.openvswitch.mech_driver \
    import mech_openvswitch as ovs
from neutron_lib import constants
from oslo_config import cfg
from oslo_log import log as logging

from networking_nec._i18n import _LW
from networking_nec.nwa.common import exceptions as nwa_exc
from networking_nec.nwa.common import utils as nwa_com_utils
from networking_nec.nwa.l2 import utils as nwa_l2_utils
from networking_nec.nwa.l3 import db_api as nwa_l3_db
from networking_nec.nwa.l3.rpc import nwa_l3_proxy_api

LOG = logging.getLogger(__name__)


class NECNWAMechanismDriver(ovs.OpenvswitchMechanismDriver):

    def initialize(self):
        self.resource_groups = nwa_com_utils.load_json_from_file(
            'resource_group', cfg.CONF.NWA.resource_group_file,
            cfg.CONF.NWA.resource_group, default_value=[])

    def _get_l2api_proxy(self, context, tenant_id):
        proxy = context._plugin.get_nwa_proxy(tenant_id,
                                              context._plugin_context)
        return proxy

    def _get_l3api_proxy(self, context, tenant_id):
        proxy = context._plugin.get_nwa_proxy(tenant_id,
                                              context.network._plugin_context)
        return nwa_l3_proxy_api.NwaL3ProxyApi(proxy.client)

    def create_port_precommit(self, context):
        device_owner = context._port['device_owner']
        if device_owner not in (constants.DEVICE_OWNER_ROUTER_INTF,
                                constants.DEVICE_OWNER_ROUTER_GW):
            LOG.warning(_LW("device owner missmatch device_owner=%s"),
                        device_owner)
            return
        self._l3_create_tenant_fw(context)
        self._bind_segment_to_vif_type(context)

    def update_port_precommit(self, context):
        new_port = context.current
        orig_port = context.original
        if (not new_port['device_id'] and orig_port['device_id'] and
                not new_port['device_owner'] and orig_port['device_owner']):
            # device_id and device_owner are clear on VM deleted.
            LOG.debug('original_port=%s', context.original)
            LOG.debug('updated_port=%s', context.current)
            self._l2_delete_general_dev(context, use_original_port=True)

    def delete_port_precommit(self, context):
        tenant_id, nwa_tenant_id = nwa_com_utils.get_tenant_info(context)
        device_owner = context._port['device_owner']
        device_id = context._port['device_id']

        LOG.debug("tenant_id=%(tid)s, nwa_tenant_id=%(nid)s, "
                  "device_owner=%(dev)s",
                  {'tid': tenant_id, 'nid': nwa_tenant_id,
                   'dev': device_owner})

        if device_owner in (constants.DEVICE_OWNER_ROUTER_GW,
                            constants.DEVICE_OWNER_ROUTER_INTF):
            self._l3_delete_tenant_fw(context)
        elif device_owner == constants.DEVICE_OWNER_FLOATINGIP:
            pass
        elif device_owner == '' and device_id == '':
            pass
        else:
            self._l2_delete_general_dev(context)

    def try_to_bind_segment_for_agent(self, context, segment, agent):
        if self._bind_segment_to_vif_type(context, agent):
            device_owner = context._port['device_owner']
            if device_owner not in (constants.DEVICE_OWNER_ROUTER_GW,
                                    constants.DEVICE_OWNER_ROUTER_INTF):
                self._bind_port_nwa_debug_message(context)
                self._l2_create_general_dev(context)
                return True
        LOG.warning(_LW("binding segment not found for agent=%s"), agent)
        return super(
            NECNWAMechanismDriver, self
        ).try_to_bind_segment_for_agent(context, segment, agent)

    def _bind_segment_to_vif_type(self, context, agent=None):
        mappings = {}
        if agent:
            mappings = agent['configurations'].get('bridge_mappings', {})

        for res in self.resource_groups:
            if agent and res['ResourceGroupName'] not in mappings:
                continue
            if res['device_owner'] != context._port['device_owner']:
                continue

            network_id = context.network.current['id']
            dummy_segment = db.get_dynamic_segment(
                context.network._plugin_context.session,
                network_id, physical_network=res['ResourceGroupName'])
            LOG.debug("1st: dummy segment is %s", dummy_segment)
            if not dummy_segment:
                dummy_segment = {
                    api.PHYSICAL_NETWORK: res['ResourceGroupName'],
                    api.NETWORK_TYPE: plugin_const.TYPE_VLAN,
                    api.SEGMENTATION_ID: 0
                }
                db.add_network_segment(
                    context.network._plugin_context.session,
                    network_id, dummy_segment, is_dynamic=True)
            LOG.debug("2nd: dummy segment is %s", dummy_segment)
            context.set_binding(dummy_segment[api.ID],
                                self.vif_type,
                                {portbindings.CAP_PORT_FILTER: True,
                                 portbindings.OVS_HYBRID_PLUG: True})
            return True
        return False

    def _bind_port_nwa_debug_message(self, context):
        network_name, network_id = nwa_l2_utils.get_network_info(context)
        device_owner = context._port['device_owner']

        subnet_ids = []
        if 'fixed_ips' in context._port:
            for fixed_ip in context._port['fixed_ips']:
                subnet_ids.append(fixed_ip['subnet_id'])

        segmentation_id = 0
        if prov_net.PHYSICAL_NETWORK in context.network.current:
            segmentation_id = context.network.current[prov_net.SEGMENTATION_ID]
        else:
            for provider in context.network.current['segments']:
                if (provider.get(prov_net.PHYSICAL_NETWORK) ==
                        nwa_l2_utils.get_physical_network(
                            device_owner, self.resource_groups)):
                    segmentation_id = provider[prov_net.SEGMENTATION_ID]
                    break

        LOG.debug("provider segmentation_id = %s", segmentation_id)
        LOG.debug("_bind_port_nwa %(network_name)s "
                  "%(network_id)s %(device_id)s %(device_owner)s "
                  "%(port_id)s %(mac_address)s %(subnet_ids)s "
                  "%(segmentation_id)s",
                  {'network_name': network_name,
                   'network_id': network_id,
                   'device_id': context._port['device_id'],
                   'device_owner': device_owner,
                   'port_id': context._port['id'],
                   'mac_address': context._port['mac_address'],
                   'subnet_ids': subnet_ids,
                   'segmentation_id': segmentation_id})

    def _l2_create_general_dev(self, context):
        kwargs = self._make_l2api_kwargs(context)
        proxy = self._get_l2api_proxy(context, kwargs['tenant_id'])
        proxy.create_general_dev(context.network._plugin_context, **kwargs)

    def _l2_delete_general_dev(self, context, use_original_port=False):
        try:
            kwargs = self._make_l2api_kwargs(
                context, use_original_port=use_original_port)
            self._l2_delete_segment(context, kwargs['nwa_info'])
            proxy = self._get_l2api_proxy(context, kwargs['tenant_id'])
            kwargs['nwa_info'] = self._revert_dhcp_agent_device_id(
                context, kwargs['nwa_info'])
            proxy.delete_general_dev(context.network._plugin_context, **kwargs)
        except nwa_exc.TenantNotFound as e:
            LOG.warning(_LW("skip delete_general_dev: %s"), e)

    def _make_l2api_kwargs(self, context, use_original_port=False):
        tenant_id, nwa_tenant_id = nwa_com_utils.get_tenant_info(context)
        nwa_info = nwa_l2_utils.portcontext_to_nwa_info(
            context, self.resource_groups, use_original_port)
        return {
            'tenant_id': tenant_id,
            'nwa_tenant_id': nwa_tenant_id,
            'nwa_info': nwa_info
        }

    def _revert_dhcp_agent_device_id(self, context, nwa_info):
        device_owner = context._port['device_owner']
        device_id = context._port['device_id']
        if device_owner == constants.DEVICE_OWNER_DHCP and \
                device_id == neutron_const.DEVICE_ID_RESERVED_DHCP_PORT:
            # get device_id of dhcp agent even if it is reserved.
            nwa_info['device']['id'] = utils.get_dhcp_agent_device_id(
                context.network.current['id'],
                context._port.get('binding:host_id')
            )
        return nwa_info

    def _l2_delete_segment(self, context, nwa_info):
        session = context.network._plugin_context.session
        del_segment = db.get_dynamic_segment(
            session,
            context.network.current['id'],
            physical_network=nwa_info['physical_network'])
        if del_segment:
            LOG.debug('delete_network_segment %s', del_segment)
            db.delete_network_segment(session, del_segment['id'])

    def _l3_create_tenant_fw(self, context):
        device_owner = context._port['device_owner']
        grplst = [res['device_owner'] for res in self.resource_groups]
        if device_owner not in grplst:
            raise nwa_exc.ResourceGroupNameNotFound(device_owner=device_owner)

        kwargs = self._make_l3api_kwargs(context)
        proxy = self._get_l3api_proxy(context, kwargs['tenant_id'])
        proxy.create_tenant_fw(context.network._plugin_context, **kwargs)

    def _l3_delete_tenant_fw(self, context):
        kwargs = self._make_l3api_kwargs(context)
        proxy = self._get_l3api_proxy(context, kwargs['tenant_id'])
        proxy.delete_tenant_fw(context.network._plugin_context, **kwargs)

    def _make_l3api_kwargs(self, context):
        rt_tid = nwa_l3_db.get_tenant_id_by_router(
            context.network._plugin_context.session,
            context._port['device_id']
        )
        nwa_rt_tid = nwa_com_utils.get_nwa_tenant_id(rt_tid)
        nwa_info = nwa_l2_utils.portcontext_to_nwa_info(
            context, self.resource_groups)
        nwa_info['tenant_id'] = rt_tid           # overwrite by router's
        nwa_info['nwa_tenant_id'] = nwa_rt_tid   # tenant_id and nwa_tenant_id
        return {
            'tenant_id': rt_tid,
            'nwa_tenant_id': nwa_rt_tid,
            'nwa_info': nwa_info
        }
