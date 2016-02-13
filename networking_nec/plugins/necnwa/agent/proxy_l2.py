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

import re
import time

from neutron.common import topics
from neutron.plugins.common import constants as n_constants
from neutron.plugins.ml2 import driver_api as api
from oslo_log import helpers
from oslo_log import log as logging

from networking_nec._i18n import _LE, _LI, _LW
from networking_nec.common import utils
from networking_nec.plugins.necnwa.common import constants as nwa_const
from networking_nec.plugins.necnwa.common import exceptions as nwa_exc
from networking_nec.plugins.necnwa.l2.rpc import nwa_l2_server_api
from networking_nec.plugins.necnwa.l2.rpc import tenant_binding_api


LOG = logging.getLogger(__name__)

KEY_CREATE_TENANT_NW = 'CreateTenantNW'
WAIT_AGENT_NOTIFIER = 20
# WAIT_AGENT_NOTIFIER = 1

VLAN_OWN_GDV = '_GD'
VLAN_OWN_TFW = '_TFW'


def catch_exception_and_update_tenant_binding(method):

    def wrapper(obj, context, **kwargs):
        try:
            return method(obj, context, **kwargs)
        except nwa_exc.AgentProxyException as e:
            tenant_id = kwargs.get('tenant_id')
            nwa_tenant_id = kwargs.get('nwa_tenant_id')
            nwa_data = e.value
            return obj.proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data)

    return wrapper


def check_vlan(network_id, nwa_data):
    # dev_key = 'VLAN_' + network_id + '_.*_VlanID$'
    #  TFW, GDV: VLAN_' + network_id + '_.*_VlanID$
    #  TLB:      VLAN_LB_' + network_id + '_.*_VlanID$
    vlan_pat = re.compile(r'VLAN_.*_' + network_id + '_.*_VlanID$')
    matched = [k for k in nwa_data if vlan_pat.match(k)]
    if matched:
        LOG.debug("find device in network(ids=%s)", network_id)
    return len(matched)


def count_device_id(device_id, nwa_data):
    dev_pat = re.compile(r'DEV_' + device_id + '_')
    matched = [k for k in nwa_data if dev_pat.match(k)]
    if matched:
        LOG.debug("found device with device_id=%s", device_id)
    return len(matched)


def check_segment(network_id, res_name, nwa_data, dev_type):
    dev_pat = re.compile(r'DEV_.*_' + network_id + '_' + res_name)
    matched = [k for k in nwa_data
               if dev_pat.match(k) and dev_type == nwa_data[k]]
    if matched:
        LOG.debug("find device in network(id=%s),"
                  " resource_group_name=%s, type=%s" %
                  (network_id, res_name, dev_type))
    return len(matched)


def check_segment_gd(network_id, res_name, nwa_data):
    return check_segment(network_id, res_name, nwa_data,
                         nwa_const.NWA_DEVICE_GDV)


def check_segment_tfw(network_id, res_name, nwa_data):
    return check_segment(network_id, res_name, nwa_data,
                         nwa_const.NWA_DEVICE_TFW)


class AgentProxyL2(object):

    def __init__(self, agent_top, client, proxy_tenant):
        self.nwa_tenant_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN)
        self.nwa_l2_rpc = nwa_l2_server_api.NwaL2ServerRpcApi(topics.PLUGIN)
        self.agent_top = agent_top
        self.client = client
        self.proxy_tenant = proxy_tenant

    @utils.log_method_return_value()
    @helpers.log_method_call
    def _create_tenant_nw(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')

        # get resource group name for NWA TenantNW.
        resource_group_name = nwa_info['resource_group_name_nw']
        nwa_data = kwargs.get('nwa_data')

        if KEY_CREATE_TENANT_NW not in nwa_data:
            LOG.debug("nwa_tenant_id=%s, resource_group_name_nw=%s" %
                      (nwa_tenant_id, resource_group_name))
            rcode, body = self.client.create_tenant_nw(
                self._dummy_ok,
                self._dummy_ng,
                context,
                nwa_tenant_id,
                resource_group_name
            )

            if rcode == 200 and body['status'] == 'SUCCESS':
                LOG.debug("CreateTenantNW succeed.")
                nwa_data[KEY_CREATE_TENANT_NW] = True
                return nwa_data
            else:
                LOG.error(_LE("CreateTenantNW Failed."))
                raise nwa_exc.AgentProxyException(value=nwa_data)

    @utils.log_method_return_value()
    def _delete_tenant_nw(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')

        rcode, body = self.client.delete_tenant_nw(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
        )

        if rcode == 200 and body['status'] == 'SUCCESS':
            LOG.debug("DeleteTenantNW SUCCESS.")
            nwa_data.pop(KEY_CREATE_TENANT_NW)
        else:
            LOG.error(_LE("DeleteTenantNW %s."), body['status'])
            raise nwa_exc.AgentProxyException(value=nwa_data)

        return nwa_data

    def _update_nwa_data(self, nwa_data, nwa_info, result_data):
        network_id = nwa_info['network']['id']
        nw_net = 'NW_' + network_id

        nwa_data[nw_net] = nwa_info['network']['name']
        nwa_data[nw_net + '_network_id'] = network_id
        nwa_data[nw_net + '_subnet_id'] = nwa_info['subnet']['id']
        nwa_data[nw_net + '_subnet'] = nwa_info['subnet']['netaddr']
        nwa_data[nw_net + '_nwa_network_name'] = result_data['LogicalNWName']

        vp_net = 'VLAN_' + network_id
        nwa_data[vp_net + '_CreateVlan'] = ''

        if result_data['VlanID'] != '':
            nwa_data[vp_net + '_VlanID'] = result_data['VlanID']
        else:
            nwa_data[vp_net + '_VlanID'] = ''
        nwa_data[vp_net] = 'physical_network'

    @utils.log_method_return_value()
    def _create_vlan(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        network_id = nwa_info['network']['id']
        nw_vlan_key = 'VLAN_' + network_id
        if nw_vlan_key in nwa_data:
            LOG.warning(_LW("aleady in vlan_key %s"), nw_vlan_key)
            return nwa_data

        rcode, body = self.client.create_vlan(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            nwa_info['subnet']['netaddr'],
            nwa_info['subnet']['mask'],
            nwa_info['network']['vlan_type'],
            openstack_network_id=network_id
        )

        if rcode == 200 and body['status'] == 'SUCCESS':
            # create vlan succeed.
            LOG.debug("CreateVlan succeed.")
            self._update_nwa_data(nwa_data, nwa_info, body['resultdata'])
        else:
            # create vlan failed.
            LOG.error(_LE("CreateVlan Failed."))
            raise nwa_exc.AgentProxyException(value=nwa_data)

        return nwa_data

    @utils.log_method_return_value()
    def _delete_vlan(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        vlan_type = nwa_info['network']['vlan_type']
        physical_network = nwa_info['physical_network']
        network_id = nwa_info['network']['id']

        # delete vlan
        rcode, body = self.client.delete_vlan(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            nwa_data['NW_' + network_id + '_nwa_network_name'],
            vlan_type
        )

        if rcode == 200 and body['status'] == 'SUCCESS':
            LOG.debug("DeleteVlan SUCCESS.")

            nw_net = 'NW_' + network_id
            nwa_data.pop(nw_net)
            nwa_data.pop(nw_net + '_network_id')
            nwa_data.pop(nw_net + '_subnet_id')
            nwa_data.pop(nw_net + '_subnet')
            nwa_data.pop(nw_net + '_nwa_network_name')

            vp_net = 'VLAN_' + network_id
            nwa_data.pop(vp_net)
            nwa_data.pop(vp_net + '_VlanID')
            nwa_data.pop(vp_net + '_CreateVlan')

            self.nwa_l2_rpc.release_dynamic_segment_from_agent(
                context, physical_network,
                network_id
            )

        else:
            LOG.debug("DeleteVlan FAILED.")
            self.proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
            raise nwa_exc.AgentProxyException(value=nwa_data)

        return nwa_data

    @helpers.log_method_call
    @catch_exception_and_update_tenant_binding
    def create_general_dev(self, context, **kwargs):
        """Create GeneralDev wrapper.

        @param context: contains user information.
        @param kwargs:
        @return: dict of status and msg.
        """

        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')

        network_id = nwa_info['network']['id']
        resource_group_name = nwa_info['resource_group_name']

        LOG.debug("tenant_id=%s, network_id=%s, device_owner=%s" % (
            tenant_id, network_id, nwa_info['device']['owner']
        ))

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        # create tenant
        if not nwa_data:
            nwa_data = self.proxy_tenant.create_tenant(context, **kwargs)
            if not self.proxy_tenant.update_tenant_binding(
                    context, tenant_id, nwa_tenant_id,
                    nwa_data, nwa_created=True):
                return None

        # create tenant nw
        if KEY_CREATE_TENANT_NW not in nwa_data:
            # raise AgentProxyException if fail
            self._create_tenant_nw(context, nwa_data=nwa_data, **kwargs)

        # create vlan
        nw_vlan_key = 'NW_' + network_id
        if nw_vlan_key not in nwa_data:
            # raise AgentProxyException if fail
            self._create_vlan(context, nwa_data=nwa_data, **kwargs)

        # create general dev
        if not check_segment_gd(network_id, resource_group_name, nwa_data):
            # raise AgentProxyException if fail
            ret_val = self._create_general_dev(
                context, nwa_data=nwa_data, **kwargs)
            nwa_data = ret_val
        else:
            ret_val = self._create_general_dev_data(
                nwa_data=nwa_data, **kwargs)
            if ret_val:
                nwa_data = ret_val
            # agent waits for notifier issue for libviert.
            time.sleep(WAIT_AGENT_NOTIFIER)
        # create general dev end

        ret = self.proxy_tenant.update_tenant_binding(
            context, tenant_id, nwa_tenant_id, nwa_data,
            nwa_created=False
        )

        segment = {
            api.PHYSICAL_NETWORK: nwa_info['physical_network'],
            api.NETWORK_TYPE: n_constants.TYPE_VLAN,
            api.SEGMENTATION_ID: self._get_vlan_id(nwa_data, network_id,
                                                   resource_group_name)
        }

        self.nwa_l2_rpc.update_port_state_with_notifier(
            context, nwa_info['device']['id'], self.agent_top.agent_id,
            nwa_info['port']['id'], segment, network_id
        )

        return ret

    def _get_vlan_id(self, nwa_data, network_id, resource_group_name):
        return int(nwa_data['VLAN_' + network_id + '_' +
                            resource_group_name + '_GD_VlanID'], 10)

    def _append_device_for_gdv(self, nwa_info, nwa_data):
        network_name = nwa_info['network']['name']
        network_id = nwa_info['network']['id']
        device_id = nwa_info['device']['id']
        device_owner = nwa_info['device']['owner']
        ipaddr = nwa_info['port']['ip']
        macaddr = nwa_info['port']['mac']
        resource_group_name = nwa_info['resource_group_name']

        dev_key = 'DEV_' + device_id
        nwa_data[dev_key] = 'device_id'
        nwa_data[dev_key + '_device_owner'] = device_owner

        net_key = dev_key + '_' + network_id
        nwa_data[net_key] = network_name
        nwa_data[net_key + '_ip_address'] = ipaddr
        nwa_data[net_key + '_mac_address'] = macaddr
        nwa_data[net_key + '_' +
                 resource_group_name] = nwa_const.NWA_DEVICE_GDV

        return nwa_data

    @utils.log_method_return_value()
    def _create_general_dev_data(self, **kwargs):
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        self._append_device_for_gdv(nwa_info, nwa_data)

        return nwa_data

    @utils.log_method_return_value()
    @helpers.log_method_call
    def _create_general_dev(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        network_id = nwa_info['network']['id']
        resource_group_name = nwa_info['resource_group_name']

        vlan_key = 'VLAN_' + network_id + '_' + resource_group_name
        port_type = None

        logical_name = nwa_data['NW_' + network_id + '_nwa_network_name']
        rcode, body = self.client.create_general_dev(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            resource_group_name,
            logical_name,
            port_type=port_type
        )

        if rcode == 200 and body['status'] == 'SUCCESS':
            LOG.debug("CreateGeneralDev SUCCESS")

            vlan_key = 'VLAN_' + network_id
            if vlan_key not in nwa_data:
                LOG.error(_LE("not create vlan."))
                raise nwa_exc.AgentProxyException(value=nwa_data)

            seg_key = ('VLAN_' + network_id + '_' + resource_group_name +
                       VLAN_OWN_GDV)
            if nwa_data[vlan_key + '_CreateVlan'] == '':
                nwa_data[seg_key + '_VlanID'] = body['resultdata']['VlanID']
            else:
                nwa_data[seg_key + '_VlanID'] = nwa_data[vlan_key + '_VlanID']
            nwa_data[seg_key] = 'physical_network'

            self._append_device_for_gdv(nwa_info, nwa_data)
        else:
            LOG.debug("CreateGeneralDev %s", body['status'])
            raise nwa_exc.AgentProxyException(value=nwa_data)

        return nwa_data

    @helpers.log_method_call
    @catch_exception_and_update_tenant_binding
    def delete_general_dev(self, context, **kwargs):
        """Delete GeneralDev.

        @param context: contains user information.
        @param kwargs:
        @return: dict of status and msg.
        """

        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        network_id = nwa_info['network']['id']
        resource_group_name = nwa_info['resource_group_name']

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        # rpc return empty.
        if not nwa_data:
            LOG.error(_LE('nwa_tenant_binding not found.'
                          ' tenant_id=%(tenant_id)s,'
                          ' nwa_tenant_id=%(nwa_tenant_id)s') %
                      {'tenant_id': tenant_id,
                       'nwa_tenant_id': nwa_tenant_id})
            return {'result': 'FAILED'}

        gd_count = check_segment_gd(network_id, resource_group_name, nwa_data)

        if 1 < gd_count:
            nwa_data = self._delete_general_dev_data(
                nwa_data=nwa_data, **kwargs)
            raise nwa_exc.AgentProxyException(value=nwa_data)

        # delete general dev
        # raise AgentProxyException if fail
        nwa_data = self._delete_general_dev(context,
                                            nwa_data=nwa_data, **kwargs)
        # delete general dev end

        # port check on segment.
        if check_vlan(network_id, nwa_data):
            raise nwa_exc.AgentProxyException(value=nwa_data)

        # delete vlan
        # raise AgentProxyException if fail
        nwa_data = self._delete_vlan(context, nwa_data=nwa_data, **kwargs)
        # delete vlan end.

        # tenant network check.
        for k in nwa_data:
            if re.match('NW_.*', k):
                raise nwa_exc.AgentProxyException(value=nwa_data)

        LOG.info(_LI("delete_tenant_nw"))
        # raise AgentProxyException if fail
        nwa_data = self._delete_tenant_nw(context, nwa_data=nwa_data, **kwargs)

        # delete tenant
        LOG.info(_LI("delete_tenant"))
        nwa_data = self.proxy_tenant.delete_tenant(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        # delete tenant end.

        # delete nwa_tenant binding.
        LOG.info(_LI("delete_nwa_tenant_binding"))
        return self.nwa_tenant_rpc.delete_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

    @utils.log_method_return_value()
    def _delete_general_dev_data(self, **kwargs):
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        device_id = nwa_info['device']['id']
        network_id = nwa_info['network']['id']
        resource_group_name = nwa_info['resource_group_name']

        vp_net = ('VLAN_' + network_id + '_' + resource_group_name +
                  VLAN_OWN_GDV)

        dev_key = 'DEV_' + device_id
        if dev_key in nwa_data:
            nwa_data.pop(dev_key + '_' + network_id)
            nwa_data.pop(dev_key + '_' + network_id + '_ip_address')
            nwa_data.pop(dev_key + '_' + network_id + '_mac_address')
            nwa_data.pop(dev_key + '_' + network_id + '_' +
                         resource_group_name)
            if count_device_id(device_id, nwa_data) == 1:
                nwa_data.pop(dev_key)
                nwa_data.pop(dev_key + '_device_owner')

        if not check_segment_gd(network_id, resource_group_name, nwa_data):
            nwa_data.pop(vp_net)
            nwa_data.pop(vp_net + '_VlanID')

        return nwa_data

    @utils.log_method_return_value()
    @helpers.log_method_call
    def _delete_general_dev(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        network_id = nwa_info['network']['id']
        resource_group = nwa_info['resource_group_name']

        # delete general dev
        logical_name = nwa_data['NW_' + network_id + '_nwa_network_name']
        rcode, body = self.client.delete_general_dev(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            resource_group,
            logical_name,
        )
        if rcode != 200:
            LOG.debug("DeleteGeneralDev Error: invalid response."
                      " rcode = %d" % rcode)
            # error port send to plugin
            raise nwa_exc.AgentProxyException(value=nwa_data)

        if body['status'] == 'SUCCESS':
            LOG.debug("DeleteGeneralDev SUCCESS")
            nwa_data = self._delete_general_dev_data(**kwargs)
        else:
            LOG.debug("DeleteGeneralDev %s", body['status'])
            raise nwa_exc.AgentProxyException(value=nwa_data)
        # delete general dev end

        return nwa_data

    def _dummy_ok(self, context, rcode, jbody, *args, **kargs):
        pass

    def _dummy_ng(self, context, rcode, jbody, *args, **kargs):
        pass
