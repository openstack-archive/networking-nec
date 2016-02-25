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

from copy import deepcopy
import re

from neutron.common import topics
from neutron.plugins.common import constants as n_constants
from neutron_lbaas.services.loadbalancer.agent \
    import agent_api as lbaas_agent_api
from neutron_lbaas.services.loadbalancer import constants as lb_const
from oslo_config import cfg
from oslo_log import helpers
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec.nwa.common import constants as nwa_const
from networking_nec.nwa.common import exceptions as nwa_exc
from networking_nec.nwa.common import utils as nwa_com_utils
from networking_nec.nwa.l2.rpc import nwa_l2_server_api
from networking_nec.nwa.l2.rpc import tenant_binding_api


LOG = logging.getLogger(__name__)

POLICY_MAP = {
    nwa_const.POLICY_TYPE_POOL: [
        'id', 'vip_id', 'name', 'description', 'protocol',
        'subnet_id', 'lb_method', 'health_monitors', 'members',
        'admin_state_up', 'status'],
    nwa_const.POLICY_TYPE_VIP: [
        'id', 'name', 'description', 'protocol', 'protocol_port',
        'pool_id', 'session_persistence', 'connection_limit',
        'admin_state_up', 'status', 'port_id'],
    nwa_const.POLICY_TYPE_MEMBER: [
        'id', 'pool_id', 'address', 'protocol_port', 'weight',
        'admin_state_up', 'status'],
    nwa_const.POLICY_TYPE_HEALTHMONITOR: [
        'id', 'type', 'delay', 'timeoit', 'maxretries',
        'http_method', 'url_path', 'expected_codes',
        'admin_state_up', 'status', 'pools']
}


# pylint: disable=too-many-instance-attributes
class AgentProxyLBaaS(object):

    def __init__(self, context, agent_top, client):
        self.nwa_tenant_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN)
        self.nwa_l2_rpc = nwa_l2_server_api.NwaL2ServerRpcApi(topics.PLUGIN)
        self.agent_top = agent_top
        self.client = client
        self.context = context
        self.conf = cfg.CONF
        self.res_name = cfg.CONF.NWA.resource_group_name
        self.lbaas_plugin_rpc = lbaas_agent_api.LbaasAgentApi(
            lb_const.LOADBALANCER_PLUGIN,
            self.context,
            self.conf.host
        )

    @property
    def proxy_tenant(self):
        return self.agent_top.proxy_tenant

    @property
    def proxy_l2(self):
        return self.agent_top.proxy_l2

    # driver api.
    @helpers.log_method_call
    def create_pool(self, context, pool):
        self.update_status('pool', pool['id'], n_constants.ACTIVE)

    @helpers.log_method_call
    def update_pool(self, context, old_pool, pool):
        self.update_status('pool', pool['id'], n_constants.ACTIVE)

    @helpers.log_method_call
    def delete_pool(self, context, pool):
        pass

    @helpers.log_method_call
    def create_vip(self, context, vip):
        pass

    @helpers.log_method_call
    def update_vip(self, context, old_vip, vip):
        self._update_vip(context, old_vip, vip)
        self.lbaas_plugin_rpc.update_status(
            'vip', vip['id'], n_constants.ACTIVE)

    @helpers.log_method_call
    def delete_vip(self, context, vip):
        self._delete_vip(context, vip)

    @helpers.log_method_call
    def create_member(self, context, member):
        self._create_member(context, member)
        self.lbaas_plugin_rpc.update_status(
            'member', member['id'], n_constants.ACTIVE
        )

    @helpers.log_method_call
    def update_member(self, context, old_member, member):
        self._update_member(context, old_member, member)
        self.lbaas_plugin_rpc.update_status(
            'member', member['id'], n_constants.ACTIVE)

    @helpers.log_method_call
    def delete_member(self, context, member):
        self._delete_member(context, member)

    @helpers.log_method_call
    def create_pool_health_monitor(self, context, health_monitor, pool_id):
        self._create_pool_health_monitor(context, health_monitor, pool_id)

    @helpers.log_method_call
    def update_pool_health_monitor(self, context, old_health_monitor,
                                   health_monitor, pool_id):
        self._update_pool_health_monitor(
            context, old_health_monitor, health_monitor, pool_id)

    @helpers.log_method_call
    def delete_pool_health_monitor(self, context, health_monitor, pool_id):
        self._delete_pool_health_monitor(context, health_monitor, pool_id)

    @helpers.log_method_call
    def _get_vip_id_by_pool_id(self, pool_id):
        logical_config = self.lbaas_plugin_rpc.get_logical_device(
            pool_id
        )
        return logical_config['vip']['id']

    @helpers.log_method_call
    def _create_policy_data(self, ptype, obj):
        for key in obj.keys():
            if key not in POLICY_MAP[ptype]:
                obj.pop(key)
        return obj

    def _count_tlb(self, context, nwa_data):
        lbvip_pat = re.compile('r^LB_VIP_.*')
        return len([k for k in nwa_data if lbvip_pat.match(k)])

    @helpers.log_method_call
    def _create_vip(self, context, vip):
        logical_config = self.lbaas_plugin_rpc.get_logical_device(
            vip['pool_id']
        )
        tenant_id = vip['tenant_id']
        nwa_tenant_id = nwa_com_utils.get_nwa_tenant_id(tenant_id)
        vip_port = logical_config['vip']['port']
        net = vip_port['fixed_ips'][0]['subnet']['cidr'].split('/')
        net_id = logical_config['vip']['port']['network_id']
        network = self.nwa_l2_rpc.get_nwa_network(context, net_id)
        vlan_type = ('PublicVLAN'
                     if network['router:external'] else 'BusinessVLAN')
        nwa_data = self.proxy_l2.ensure_l2_network(
            context, **{
                'tenant_id': tenant_id,
                'nwa_tenant_id': nwa_tenant_id,
                'nwa_info': {
                    'subnet': {
                        'netaddr': net[0],
                        'mask': net[1]
                    },
                    'network': {
                        'vlan_type': vlan_type
                    }
                }
            })

        if self._count_tlb(context, nwa_data):
            __result, nwa_data = self._nwa_update_tenant_lb_add(
                context, tenant_id, nwa_tenant_id,
                net_id, vip['pool_id'], vip['id'],
                logical_config['vip']['address'],
                logical_config['vip']['port']['mac_address'], vlan_type
            )
            # lb policy unset bug fix.
            __result, nwa_data = self._nwa_setting_lb_policy(
                context, tenant_id, nwa_tenant_id,
                nwa_const.POLICY_TYPE_POOL, nwa_const.POLICY_CREATE,
                logical_config['pool'], vip['id']
            )
            __result, nwa_data = self._nwa_setting_lb_policy(
                context, tenant_id, nwa_tenant_id,
                nwa_const.POLICY_TYPE_VIP, nwa_const.POLICY_CREATE, vip,
                vip['id']
            )
            return

        __result, nwa_data = self._nwa_create_tenant_lb(
            context, tenant_id, nwa_tenant_id,
            net_id, vip['pool_id'], vip['id'],
            logical_config['vip']['address'],
            logical_config['vip']['port']['mac_address'],
            vlan_type
        )

        __result, nwa_data = self._nwa_setting_lb_policy(
            context, tenant_id, nwa_tenant_id, nwa_const.POLICY_TYPE_POOL,
            nwa_const.POLICY_CREATE,
            logical_config['pool'], vip['id']
        )

        __result, nwa_data = self._nwa_setting_lb_policy(
            context, tenant_id, nwa_tenant_id, nwa_const.POLICY_TYPE_VIP,
            nwa_const.POLICY_CREATE,
            vip, vip['id']
        )

        for member in logical_config['members']:
            __result, nwa_data = self._nwa_setting_lb_policy(
                context, tenant_id, nwa_tenant_id,
                nwa_const.POLICY_TYPE_MEMBER, nwa_const.POLICY_CREATE,
                member, vip['id']
            )

    # pylint: disable=too-many-locals
    @helpers.log_method_call
    def _update_vip(self, context, old_vip, vip):
        tenant_id = vip['tenant_id']
        nwa_tenant_id = nwa_com_utils.get_nwa_tenant_id(tenant_id)

        if vip['address'] != old_vip['address']:
            network = self.nwa_l2_rpc.get_nwa_network_by_subnet_id(
                context, vip['subnet_id']
            )
            old_network = self.nwa_l2_rpc.get_nwa_network_by_subnet_id(
                context, old_vip['subnet_id']
            )

            if network['id'] != old_network['id']:
                # create vlan(network):
                logical_config = self.lbaas_plugin_rpc.get_logical_device(
                    vip['pool_id']
                )

                vip_port = logical_config['vip']['port']
                net = vip_port['fixed_ips'][0]['subnet']['cidr'].split('/')
                vlan_type = ('PublicVLAN' if network['router:external']
                             else 'BusinessVLAN')
                nwa_data = self.proxy_l2._create_vlan_network(
                    context, **{
                        'tenant_id': tenant_id,
                        'nwa_tenant_id': nwa_tenant_id,
                        'nwa_info': {
                            'subnet': {
                                'netaddr': net[0],
                                'mask': net[1]
                            },
                            'network': {
                                'vlan_type': vlan_type
                            }
                        }})
                # update tenant vlan
                old_vlan_type = ('PublicVLAN'
                                 if old_network['router:external']
                                 else 'BusinessVLAN')
                result, __ = self.nwa_update_tenant_lbn(
                    context, tenant_id, old_vip['id'], vip['id'],
                    nwa_tenant_id, old_network['id'], network['id'],
                    old_vlan_type, vlan_type, vip['address']
                )
                if not result:
                    return
                # delete vlan(old_network):
                nwa_data = self.proxy_l2._delete_vlan_network(
                    context, **{
                        'tenant_id': tenant_id,
                        'nwa_tenant_id': nwa_tenant_id,
                        'nwa_info': {
                            'network': {
                                'vlan_type': vlan_type,
                                'id': old_network['id']
                            },
                            'physical_network': None,
                        },
                        'nwa_data': nwa_data})
            else:
                result, __ = self.nwa_update_tenant_lbn(
                    context, tenant_id, old_vip['id'], vip['id'],
                    nwa_tenant_id, old_network['id'], network['id'],
                    old_vlan_type, vlan_type, vip['address']
                )
                if not result:
                    return

        return self._nwa_setting_lb_policy(
            context, tenant_id, nwa_tenant_id, nwa_const.POLICY_TYPE_VIP,
            nwa_const.POLICY_UPDATE, vip, vip['id'], old_vip
        )

    @helpers.log_method_call
    def _delete_vip(self, context, vip):
        tenant_id = vip['tenant_id']
        nwa_tenant_id = nwa_com_utils.get_nwa_tenant_id(tenant_id)

        __result, nwa_data = self._nwa_setting_lb_policy(
            context, tenant_id, nwa_tenant_id, nwa_const.POLICY_TYPE_VIP,
            nwa_const.POLICY_DELETE, vip, vip['id']
        )

        try:
            logical_config = self.lbaas_plugin_rpc.get_logical_device(
                vip['pool_id']
            )
            pool_conf = logical_config['pool']
        except Exception:
            pool_conf = jsonutils.loads(nwa_data['POLICY_' + vip['pool_id']])

        __result, nwa_data = self._nwa_setting_lb_policy(
            context, tenant_id, nwa_tenant_id, nwa_const.POLICY_TYPE_POOL,
            nwa_const.POLICY_DELETE, pool_conf, vip['id']
        )

        net_id = nwa_data['LB_VIPNET_' + vip['id']]
        vlan_type = nwa_data['LB_VIPLTYPE_' + vip['id']]

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id)
        if self._count_tlb(context, nwa_data) > 1:
            # update tenant lb (disconnect)
            __result, nwa_data = self._nwa_update_tenant_lb_remove(
                context, tenant_id, nwa_tenant_id, net_id, vip['id'], vlan_type
            )
        else:
            # delete lb
            __result, nwa_data = self._nwa_delete_tenant_lb(
                context, tenant_id, nwa_tenant_id, vip['id'], net_id, vlan_type
            )

        self.proxy_l2.terminate_l2_network_network(
            context, nwa_data, **{
                'tenant_id': tenant_id,
                'nwa_tenant_id': nwa_tenant_id,
                'nwa_info': {
                    'network': {
                        'vlan_type': vlan_type,
                        'id': net_id
                    },
                    'physical_network': None
                },
                'nwa_data': nwa_data})

    def update_status(self, obj, obj_id, status):
        return self.lbaas_plugin_rpc.update_status(obj, obj_id, status)

    def _is_setting_policy(self, pool_id):
        device = self.lbaas_plugin_rpc.get_logical_device(pool_id)
        if device['pool']['vip_id']:
            return True
        return False

    @helpers.log_method_call
    def _create_member(self, context, member):
        tid = member['tenant_id']

        if not self._is_setting_policy(member['pool_id']):
            return

        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)
        vip_id = self._get_vip_id_by_pool_id(member['pool_id'])

        return self._nwa_setting_lb_policy(
            context, tid, nwa_tid, nwa_const.POLICY_TYPE_MEMBER,
            nwa_const.POLICY_CREATE,
            member, vip_id
        )

    @helpers.log_method_call
    def _update_member(self, context, old_member, member):
        if not self._is_setting_policy(member['pool_id']):
            return

        tid = member['tenant_id']
        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)
        vip_id = self._get_vip_id_by_pool_id(member['pool_id'])

        return self._nwa_setting_lb_policy(
            context, tid, nwa_tid, nwa_const.POLICY_TYPE_MEMBER,
            nwa_const.POLICY_UPDATE,
            member, vip_id, old_member
        )

    @helpers.log_method_call
    def _delete_member(self, context, member):
        tid = member['tenant_id']

        if not self._is_setting_policy(member['pool_id']):
            return

        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)
        vip_id = self._get_vip_id_by_pool_id(member['pool_id'])

        self._nwa_setting_lb_policy(
            context, tid, nwa_tid, nwa_const.POLICY_TYPE_MEMBER,
            nwa_const.POLICY_DELETE,
            member, vip_id
        )

    @helpers.log_method_call
    def _create_pool_health_monitor(self, context, health_mon, pool_id):
        tid = health_mon['tenant_id']
        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)

        for hm in health_mon['pools']:
            health_mon_policy = deepcopy(health_mon)
            health_mon_policy['pools'] = [hm]
            vip_id = self._get_vip_id_by_pool_id(hm['pool_id'])

            self._nwa_setting_lb_policy(
                context, tid, nwa_tid, nwa_const.POLICY_TYPE_HEALTHMONITOR,
                nwa_const.POLICY_CREATE,
                health_mon_policy, vip_id
            )

    @helpers.log_method_call
    def _update_pool_health_monitor(self, context, old_health_mon, health_mon,
                                    pool_id):
        tid = health_mon['tenant_id']
        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)

        for hm in health_mon['pools']:
            health_mon_policy = deepcopy(health_mon)
            health_mon_policy['pools'] = [hm]
            vip_id = self._get_vip_id_by_pool_id(hm['pool_id'])

            self._nwa_setting_lb_policy(
                context, tid, nwa_tid, nwa_const.POLICY_TYPE_HEALTHMONITOR,
                nwa_const.POLICY_UPDATE,
                health_mon_policy, vip_id
            )

    @helpers.log_method_call
    def _delete_pool_health_monitor(self, context, health_mon, pool_id):
        tid = health_mon['tenant_id']
        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)

        for hm in health_mon['pools']:
            health_mon_policy = deepcopy(health_mon)
            health_mon_policy['pools'] = [hm]
            vip_id = self._get_vip_id_by_pool_id(hm['pool_id'])
            self._nwa_setting_lb_policy(
                context, tid, nwa_tid, nwa_const.POLICY_TYPE_HEALTHMONITOR,
                nwa_const.POLICY_DELETE,
                health_mon_policy, vip_id
            )

    def _nwa_create_tenant_lb(self, context, tid, nwa_tid, net_id, __pool_id,
                              vip_id, address, __mac, vlan_type):
        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)

        lb_key = 'LB_' + vlan_type
        if lb_key in nwa_data.keys():
            raise nwa_exc.DriverError(
                api="CreateTenantLB",
                msg="already in lb key. key=%s" % lb_key)

        rcode, body = self.client.lbaas.create_tenant_lb(
            context,
            nwa_tid,
            self.res_name,
            nwa_data['NW_' + net_id + '_nwa_network_name'],
            vlan_type,
            address
        )
        if rcode != 200 or body['status'] != 'SUCCESS':
            raise nwa_exc.DriverError(
                api="CreateTenantLB",
                msg=("responce error rcode=%d, status=%s" %
                     (rcode, body['status']))
            )

        # TenantLB Params
        nwa_data[lb_key] = 'TLB'
        nwa_data[lb_key +
                 '_LogicalLBName'] = body['resultdata']['TenantLBInfo']

        # TenantLB Sub Params
        nwa_data['LB_VIP_' + vip_id] = vip_id
        nwa_data['LB_VIPNET_' + vip_id] = net_id
        nwa_data['LB_VIPLTYPE_' + vip_id] = vlan_type

        nwa_data['DEV_' + vip_id +
                 '_LogicalLBName'] = body['resultdata']['TenantLBInfo']
        nwa_data['DEV_' + vip_id + '_' + net_id + '_ip_address'] = address

        vlan_key = 'VLAN_' + net_id
        seg_vlan_key = ('VLAN_LB_' + net_id + '_' + self.res_name +
                        '_VlanID')
        if nwa_data[vlan_key + '_CreateVlan'] == '':
            nwa_data[seg_vlan_key] = body['resultdata']['VlanID']
        else:
            nwa_data[seg_vlan_key] = nwa_data[vlan_key + '_VlanID']

        LOG.debug("nwa_data=%s", jsonutils.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))
        self.nwa_tenant_rpc.set_nwa_tenant_binding(
            context, tid, nwa_tid, nwa_data
        )
        return True, nwa_data

    def _nwa_update_tenant_lb_add(
            self, context, tid, nwa_tid, net_id,
            __pool_id, vip_id, address, __mac, vlan_type):
        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)

        vip_key = 'LB_VIP_' + vip_id
        if vip_key in nwa_data.keys():
            raise nwa_exc.DriverError(
                api="UpdateTenantLB(connect)",
                msg="already in vip key. key=%s" % vip_key)

        rcode, body = self.client.lbaas.update_tenant_lbn(
            context,
            nwa_tid,
            nwa_data['LB_' + vlan_type + '_LogicalLBName'],
            [['connect', nwa_data['NW_' + net_id + '_nwa_network_name'],
              address, vlan_type]]
        )
        if rcode != 200 or body['status'] != 'SUCCESS':
            raise nwa_exc.DriverError(
                api="UpdateTenantLB(connect)",
                msg=("responce error rcode=%d, status=%s" %
                     (rcode, body['status'])))

        # TenantLB Sub Params
        nwa_data['LB_VIP_' + vip_id] = vip_id
        nwa_data['LB_VIPNET_' + vip_id] = net_id
        nwa_data['LB_VIPLTYPE_' + vip_id] = vlan_type
        nwa_data['DEV_' + vip_id +
                 '_LogicalLBName'] = body['resultdata']['TenantLBInfo']
        nwa_data['DEV_' + vip_id + '_' + net_id + '_ip_address'] = address

        vlan_key = 'VLAN_' + net_id
        seg_vlan_key = ('VLAN_LB_' + net_id + '_' + self.res_name +
                        '_VlanID')
        if nwa_data[vlan_key + '_CreateVlan'] == '':
            nwa_data[seg_vlan_key] = body['resultdata']['VlanID']
        else:
            nwa_data[seg_vlan_key] = nwa_data[vlan_key + '_VlanID']

        LOG.debug("nwa_data=%s", jsonutils.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))
        self.nwa_tenant_rpc.set_nwa_tenant_binding(
            context, tid, nwa_tid, nwa_data
        )
        return True, nwa_data

    def _nwa_update_tenant_lb_remove(
            self, context, tid, nwa_tid, net_id, vip_id, vlan_type):
        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)

        vip_key = 'LB_VIP_' + vip_id
        if vip_key not in nwa_data.keys():
            raise nwa_exc.DriverError(
                api="UpdateTenantLB(disconnect)",
                msg="vip key not found. key=%s" % vip_key)

        logical_name = nwa_data['NW_' + net_id + '_nwa_network_name']
        device_name = nwa_data['DEV_' + vip_id + '_LogicalLBName']
        address = nwa_data['DEV_' + vip_id + '_' + net_id + '_ip_address']

        rcode, body = self.client.lbaas.update_tenant_lbn(
            context,
            nwa_tid,
            device_name,
            [['disconnect', logical_name, address, vlan_type]]
        )
        if rcode != 200 or body['status'] != 'SUCCESS':
            raise nwa_exc.DriverError(
                api="UpdateTenantLB(disconnect)",
                msg=("responce error rcode=%d, status=%s" %
                     (rcode, body['status'])))

        # TenantLB Sub params
        nwa_data.pop('LB_VIP_' + vip_id)
        nwa_data.pop('LB_VIPNET_' + vip_id)
        nwa_data.pop('LB_VIPLTYPE_' + vip_id)
        nwa_data.pop('DEV_' + vip_id + '_LogicalLBName')
        nwa_data.pop('DEV_' + vip_id + '_' + net_id + '_ip_address')

        seg_vlan_key = ('VLAN_LB_' + net_id + '_' + self.res_name +
                        '_VlanID')
        nwa_data.pop(seg_vlan_key)

        LOG.debug("nwa_data=%s", jsonutils.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))
        self.nwa_tenant_rpc.set_nwa_tenant_binding(
            context, tid, nwa_tid, nwa_data
        )
        return True, nwa_data

    def nwa_update_tenant_lbn(
            self, context, tid, old_vip_id, vip_id, nwa_tid,
            old_net_id, net_id, old_vlan_type, vlan_type, address
    ):
        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)

        vip_key = 'LB_VIP_' + old_vip_id
        if vip_key not in nwa_data.keys():
            msg = "vip key not found. key=%s" % vip_key
            raise nwa_exc.DriverError(
                api="UpdateTenantLB(disconnect,connect)",
                msg=msg)

        old_logical_name = nwa_data['NW_' + old_net_id + '_nwa_network_name']
        old_address = nwa_data['DEV_' + old_vip_id + '_' + old_net_id +
                               '_ip_address']

        logical_name = nwa_data['NW_' + net_id + '_nwa_network_name']
        device_name = nwa_data['DEV_' + old_vip_id + '_LogicalLBName']

        rcode, body = self.client.lbaas.update_tenant_lbn(
            context,
            nwa_tid,
            device_name,
            [['disconnect', old_logical_name, old_address, old_vlan_type],
             ['connect', logical_name, address, vlan_type]]
        )
        if (
                rcode == 200 and
                body['status'] == 'SUCCESS'
        ):
            # TenantLB Sub Params Delete.
            nwa_data.pop('LB_VIP_' + old_vip_id)
            nwa_data.pop('LB_VIPNET_' + old_vip_id)
            nwa_data.pop('LB_VIPLTYPE_' + old_vip_id)
            nwa_data.pop('DEV_' + old_vip_id + '_LogicalLBName')
            nwa_data.pop('DEV_' + old_vip_id + '_' + net_id + '_ip_address')

            nwa_data.pop('VLAN_LB_' + old_net_id + '_' + self.res_name +
                         '_VlanID')

            # TenantLB Sub Params Add.
            nwa_data['LB_VIP_' + vip_id] = vip_id
            nwa_data['LB_VIPNET_' + vip_id] = net_id
            nwa_data['LB_VIPLTYPE_' + vip_id] = vlan_type
            nwa_data['DEV_' + vip_id +
                     '_LogicalLBName'] = body['resultdata']['TenantLBInfo']
            nwa_data['DEV_' + vip_id + '_' + net_id + '_ip_address'] = address

            vlan_key = 'VLAN_' + net_id
            seg_vlan_key = ('VLAN_LB_' + net_id + '_' + self.res_name +
                            '_VlanID')

            if nwa_data[vlan_key + '_CreateVlan'] == '':
                nwa_data[seg_vlan_key] = body['resultdata']['VlanID']
            else:
                nwa_data[seg_vlan_key] = nwa_data[vlan_key + '_VlanID']

            LOG.debug("nwa_data=%s", jsonutils.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            self.nwa_tenant_rpc.set_nwa_tenant_binding(
                context, tid, nwa_tid, nwa_data
            )
        else:
            msg = ("responce error rcode=%d, status=%s" %
                   (rcode, body['status']))
            raise nwa_exc.DriverError(
                api="UpdateTenantLB(disconnect,connect)", msg=msg)

        return True, nwa_data

    def _nwa_delete_tenant_lb(self, context, tid, nwa_tid, vip_id, net_id,
                              vlan_type):

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)
        device_name = nwa_data['DEV_' + vip_id + '_LogicalLBName']

        lb_key = 'LB_' + vlan_type
        if lb_key not in nwa_data.keys():
            msg = "lb key not found. key=%s" % lb_key
            raise nwa_exc.DriverError(api="DeleteTenantLB", msg=msg)

        rcode, body = self.client.lbaas.delete_tenant_lb(
            context,
            nwa_tid,
            device_name
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCESS'
        ):
            LOG.debug("DeleteTenantLB SUCCESS.")
            # TenantLB
            nwa_data.pop(lb_key)
            nwa_data.pop(lb_key + '_LogicalLBName')

            # TenantLB Sub params
            nwa_data.pop('LB_VIP_' + vip_id)
            nwa_data.pop('LB_VIPNET_' + vip_id)
            nwa_data.pop('LB_VIPLTYPE_' + vip_id)
            nwa_data.pop('DEV_' + vip_id + '_LogicalLBName')
            nwa_data.pop('DEV_' + vip_id + '_' + net_id + '_ip_address')

            seg_vlan_key = ('VLAN_LB_' + net_id + '_' + self.res_name +
                            '_VlanID')
            nwa_data.pop(seg_vlan_key)

            LOG.debug("nwa_data=%s", jsonutils.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            self.nwa_tenant_rpc.set_nwa_tenant_binding(
                context, tid, nwa_tid, nwa_data
            )
        else:
            msg = ("responce error rcode=%d, status=%s" %
                   (rcode, body['status']))
            raise nwa_exc.DriverError(
                api="DeleteTenantLB(disconnect)", msg=msg)

        return True, nwa_data

    def _nwa_setting_lb_policy(self, context, tid, nwa_tid, res_type, op_type,
                               obj, vip_id, old_obj=None):

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)
        lb_name = nwa_data['DEV_' + vip_id + '_LogicalLBName']

        policy = {res_type: deepcopy(obj)}
        policy['operation_type'] = op_type
        policy['resource_type'] = res_type

        if (
                op_type != nwa_const.POLICY_CREATE and
                ('POLICY_' + obj['id']) in nwa_data.keys()
        ):
            policy["old_%s" % res_type] = jsonutils.loads(nwa_data['POLICY_' +
                                                                   obj['id']])

        LOG.debug("policy=%s", jsonutils.dumps(
            policy,
            indent=4,
            sort_keys=True
        ))

        rcode, body = self.client.lbaas.setting_lb_policy(
            context,
            nwa_tid,
            lb_name,
            policy
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCESS'
        ):
            LOG.debug("SettingLBPolicy Success.")
            if op_type == nwa_const.POLICY_DELETE:
                nwa_data.pop('POLICY_' + obj['id'])
            else:
                nwa_data['POLICY_' + obj['id']] = jsonutils.dumps(obj)

            self.nwa_tenant_rpc.set_nwa_tenant_binding(
                context, tid, nwa_tid, nwa_data
            )

        else:
            raise nwa_exc.DriverError(api="SettingLBPolicy", msg=None)

        return True, nwa_data
