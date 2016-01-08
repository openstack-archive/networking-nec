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

import json
import re

from copy import deepcopy

from oslo_log import log as logging
from neutron_lbaas.services.loadbalancer import constants as l_const

from networking_nec.plugins.necnwa import necnwa_utils

from networking_nec.plugins.necnwa.agent.agent_base_driver import (
    NECNWAAgentBaseDriver,
    POLICY_CREATE,
    POLICY_UPDATE,
    POLICY_DELETE,
    POLICY_TYPE_POOL,
    POLICY_TYPE_VIP,
    POLICY_TYPE_MEMBER,
    POLICY_TYPE_HEALTHMONITOR
)

from neutron.plugins.common import constants as n_constants
from neutron_lbaas.services.loadbalancer.agent import agent_api as lbaas_agent_api

LOG = logging.getLogger(__name__)

POLICY_MAP = {
    POLICY_TYPE_POOL: ['id', 'vip_id', 'name', 'description', 'protocol',
                       'subnet_id', 'lb_method', 'health_monitors', 'members',
                       'admin_state_up', 'status'],
    POLICY_TYPE_VIP: ['id', 'name', 'description', 'protocol', 'protocol_port',
                      'pool_id', 'session_persistence', 'connection_limit',
                      'admin_state_up', 'status', 'port_id'],
    POLICY_TYPE_MEMBER: ['id', 'pool_id', 'address', 'protocol_port', 'weight',
                         'admin_state_up', 'status'],
    POLICY_TYPE_HEALTHMONITOR: ['id', 'type', 'delay', 'timeoit', 'maxretries',
                                'http_method', 'url_path', 'expected_codes',
                                'admin_state_up', 'status', 'pools']
}


def check_vlan(network_id, nwa_data):
    dev_key = 'VLAN_' + network_id + '_.*_VlanID$'
    cnt = 0
    for k in nwa_data.keys():
        if re.match(dev_key, k):
            LOG.debug("find device in network(id=%s)" % network_id)
            cnt += 1
    return cnt


class NECNWALBaaSAgentDriver(NECNWAAgentBaseDriver):

    def __init__(self, agent, context):
        super(NECNWALBaaSAgentDriver, self).__init__(agent, context)
        self.lbaas_plugin_rpc = lbaas_agent_api.LbaasAgentApi(
            l_const.LOADBALANCER_PLUGIN,
            self.context,
            self.conf.host
        )

    def update_status(self, obj, obj_id, status):
        return self.lbaas_plugin_rpc.update_status(obj, obj_id, status)

    def _is_setting_policy(self, pool_id):
        device = self.lbaas_plugin_rpc.get_logical_device(pool_id)
        if device['pool']['vip_id']:
            return True
        return False

    # LBaaS NWA API call
    def _create_vip(self, context, vip):
        LOG.debug("vip=%s" % json.dumps(
            vip,
            indent=4,
            sort_keys=True
        ))

        tid = vip['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)
        nwa_data = self.nwa_create_tenant(context, tid, nwa_tid)

        result, nwa_data = self.nwa_create_tenant_nw(
            context, tid, nwa_tid, self.conf.NWA.ResourceGroupName
        )

        logical_config = self.lbaas_plugin_rpc.get_logical_device(
            vip['pool_id']
        )

        LOG.debug("logical_config=%s" % json.dumps(
            logical_config,
            indent=4,
            sort_keys=True
        ))

        net = logical_config['vip']['port']['fixed_ips'][0]['subnet']['cidr'].split('/')

        net_id = logical_config['vip']['port']['network_id']
        network = self.agent.nwa_core_rpc.get_nwa_network(context, net_id)

        vlan_type = 'PublicVLAN' if network['router:external'] is True else 'BusinessVLAN'

        result, nwa_data = self.nwa_create_vlan(
            context, tid, nwa_tid,
            net_id, network['name'],
            logical_config['vip']['subnet_id'],
            net[0], net[1],
            vlan_type)

        LOG.debug("nwa_data=%s" % json.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))

        if self._count_tlb(context, nwa_data):
            result, nwa_data = self.nwa_update_tenant_lb_add(
                context, tid, nwa_tid,
                net_id, vip['pool_id'], vip['id'],
                logical_config['vip']['address'],
                logical_config['vip']['port']['mac_address'],
                vlan_type
            )

            # lb policy unset bug fix.
            result, nwa_data = self.nwa_setting_lb_policy(
                context, tid, nwa_tid, POLICY_TYPE_POOL, POLICY_CREATE,
                logical_config['pool'], vip['id']
            )

            result, nwa_data = self.nwa_setting_lb_policy(
                context, tid, nwa_tid, POLICY_TYPE_VIP, POLICY_CREATE,
                vip, vip['id']
            )

            return

        result, nwa_data = self.nwa_create_tenant_lb(
            context, tid, nwa_tid,
            net_id, vip['pool_id'], vip['id'],
            logical_config['vip']['address'],
            logical_config['vip']['port']['mac_address'],
            vlan_type
        )

        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_POOL, POLICY_CREATE,
            logical_config['pool'], vip['id']
        )

        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_VIP, POLICY_CREATE,
            vip, vip['id']
        )

        for member in logical_config['members']:
            result, nwa_data = self.nwa_setting_lb_policy(
                context, tid, nwa_tid, POLICY_TYPE_MEMBER, POLICY_CREATE,
                member, vip['id']
            )

        return

    def _update_vip(self, context, old_vip, vip):
        LOG.debug("old_vip=%s" % json.dumps(
            old_vip,
            indent=4,
            sort_keys=True
        ))
        LOG.debug("vip=%s" % json.dumps(
            vip,
            indent=4,
            sort_keys=True
        ))

        tid = vip['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)

        if old_vip['address'] != vip['address']:
            network = self.agent.nwa_core_rpc.get_nwa_network_by_subnet_id(
                context, vip['subnet_id']
            )

            old_network = self.agent.nwa_core_rpc.get_nwa_network_by_subnet_id(
                context, old_vip['subnet_id']
            )

            if network['id'] != old_network['id']:
                # create vlan(network):
                logical_config = self.lbaas_plugin_rpc.get_logical_device(
                    vip['pool_id']
                )

                net = logical_config['vip']['port']['fixed_ips'][0]['subnet']['cidr'].split('/')
                vlan_type = 'PublicVLAN' if network['router:external'] is True else 'BusinessVLAN'
                result, nwa_data = self.nwa_create_vlan(
                    context, tid, nwa_tid,
                    network['id'], network['name'],
                    vip['subnet_id'], net[0], net[1],
                    vlan_type
                )
                # update tenant vlan
                old_vlan_type = 'PublicVLAN' if old_network['router:external'] is True else 'BusinessVLAN'
                result, nwa_data = self.nwa_update_tenant_lbn(
                    old_vip['id'], vip['id'],
                    old_network['id'], network['id'],
                    old_vlan_type, vlan_type, vip['address']
                )
                # delete vlan(old_network):
                result, nwa_data = self.nwa_delete_vlan(
                    context, tid, nwa_tid,
                    old_network['id'], vlan_type
                )
            else:
                result, nwa_data = self.nwa_update_tenant_lbn(
                    old_vip['id'], vip['id'],
                    old_network['id'], network['id'],
                    old_vlan_type, vlan_type, vip['address']
                )

        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_VIP, POLICY_UPDATE,
            vip, vip['id'], old_vip
        )
        return

    def _delete_vip(self, context, vip):
        LOG.debug("vip=%s" % json.dumps(
            vip,
            indent=4,
            sort_keys=True
        ))
        tid = vip['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)

        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_VIP, POLICY_DELETE,
            vip, vip['id']
        )

        try:
            logical_config = self.lbaas_plugin_rpc.get_logical_device(
                vip['pool_id']
            )
            pool_conf = logical_config['pool']
        except:
            pool_conf = json.loads(nwa_data['POLICY_' + vip['pool_id']])

        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_POOL, POLICY_DELETE,
            pool_conf, vip['id']
        )

        LOG.debug("pool_conf=%s" % json.dumps(
            pool_conf,
            indent=4,
            sort_keys=True
        ))

        """
        network = self.agent.nwa_core_rpc.get_nwa_network_by_subnet_id(
            context, vip['subnet_id']
        )
        """
        net_id = nwa_data['LB_VIPNET_' + vip['id']]

        vlan_type = nwa_data['LB_VIPLTYPE_' + vip['id']]
        #vlan_type = 'PublicVLAN' if network['router:external'] is True else 'BusinessVLAN'

        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)
        # mod from start
        """
        if self._count_tlb(context, nwa_data) > 1:
            # update tenant lb (disconnect)
            result, nwa_data = self.nwa_update_tenant_lb_remove(
                #context, tid, nwa_tid,  network['id'],
                context, tid, nwa_tid,  net_id,
                vip['id'], vlan_type
            )
            # delete vlan
            result, nwa_data = self.nwa_delete_vlan(
                #context, tid, nwa_tid, network['id'], vlan_type
                context, tid, nwa_tid, net_id, vlan_type
            )

            return

        # delete lb
        result, nwa_data = self.nwa_delete_tenant_lb(
            #context, tid, nwa_tid, vip['id'], network['id'], vlan_type
            context, tid, nwa_tid, vip['id'], net_id, vlan_type
        )

        result, nwa_data = self.nwa_delete_vlan(
            #context, tid, nwa_tid, network['id'], vlan_type
            context, tid, nwa_tid, net_id, vlan_type
        )
        """
        # mod from end
        # mod to start
        if self._count_tlb(context, nwa_data) > 1:
            # update tenant lb (disconnect)
            result, nwa_data = self.nwa_update_tenant_lb_remove(
                #context, tid, nwa_tid,  network['id'],
                context, tid, nwa_tid,  net_id,
                vip['id'], vlan_type
            )
        else:
            # delete lb
            result, nwa_data = self.nwa_delete_tenant_lb(
                #context, tid, nwa_tid, vip['id'], network['id'], vlan_type
                context, tid, nwa_tid, vip['id'], net_id, vlan_type
            )

        if check_vlan(net_id, nwa_data):
            return

        result, nwa_data = self.nwa_delete_vlan(
            #context, tid, nwa_tid, network['id'], vlan_type
            context, tid, nwa_tid, net_id, vlan_type
        )
        # mod to end

        if result is False:
            return

        result, nwa_data = self.nwa_delete_tenant_nw(
            context, tid, nwa_tid
        )

        if result is False:
            return

        self.nwa_delete_tenant(
            context, tid, nwa_tid
        )

        return

    def _create_member(self, context, member):
        LOG.debug("member=%s" % json.dumps(
            member,
            indent=4,
            sort_keys=True
        ))
        tid = member['tenant_id']

        if not self._is_setting_policy(member['pool_id']):
            return

        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)
        vip_id = self._get_vip_id_by_pool_id(member['pool_id'])

        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_MEMBER, POLICY_CREATE,
            member, vip_id
        )
        return

    def _update_member(self, context, old_member, member):
        LOG.debug("old_member=%s" % json.dumps(
            old_member,
            indent=4,
            sort_keys=True
        ))
        LOG.debug("member=%s" % json.dumps(
            member,
            indent=4,
            sort_keys=True
        ))

        if not self._is_setting_policy(member['pool_id']):
            return

        tid = member['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)
        vip_id = self._get_vip_id_by_pool_id(member['pool_id'])

        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_MEMBER, POLICY_UPDATE,
            member, vip_id, old_member
        )
        return

    def _delete_member(self, context, member):
        LOG.debug("member=%s" % json.dumps(
            member,
            indent=4,
            sort_keys=True
        ))
        tid = member['tenant_id']

        if not self._is_setting_policy(member['pool_id']):
            return

        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)
        vip_id = self._get_vip_id_by_pool_id(member['pool_id'])

        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_MEMBER, POLICY_DELETE,
            member, vip_id
        )
        return

    def _create_pool_health_monitor(self, context, health_mon, pool_id):
        LOG.debug("health_mon=%s" % json.dumps(
            health_mon,
            indent=4,
            sort_keys=True
        ))
        tid = health_mon['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)

        for hm in health_mon['pools']:
            health_mon_policy = deepcopy(health_mon)
            health_mon_policy['pools'] = [hm]
            vip_id = self._get_vip_id_by_pool_id(hm['pool_id'])

            result, nwa_data = self.nwa_setting_lb_policy(
                context, tid, nwa_tid, POLICY_TYPE_HEALTHMONITOR, POLICY_CREATE,
                health_mon_policy, vip_id
            )

        return

    def _update_pool_health_monitor(self, context, old_health_mon, health_mon, pool_id):
        LOG.debug("old_health_mon=%s" % json.dumps(
            old_health_mon,
            indent=4,
            sort_keys=True
        ))
        LOG.debug("health_mon=%s" % json.dumps(
            health_mon,
            indent=4,
            sort_keys=True
        ))
        tid = health_mon['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)

        """
        result, nwa_data = self.nwa_setting_lb_policy(
            context, tid, nwa_tid, POLICY_TYPE_HEALTHMONITOR, POLICY_UPDATE,
            health_mon, health_mon['pool_id'], old_health_mon
        )
        """
        for hm in health_mon['pools']:
            health_mon_policy = deepcopy(health_mon)
            health_mon_policy['pools'] = [hm]
            vip_id = self._get_vip_id_by_pool_id(hm['pool_id'])

            result, nwa_data = self.nwa_setting_lb_policy(
                context, tid, nwa_tid, POLICY_TYPE_HEALTHMONITOR, POLICY_UPDATE,
                health_mon_policy, vip_id
            )
        return

    def _delete_pool_health_monitor(self, context, health_mon, pool_id):
        LOG.debug("health_mon=%s" % json.dumps(
            health_mon,
            indent=4,
            sort_keys=True
        ))
        tid = health_mon['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)

        for hm in health_mon['pools']:
            health_mon_policy = deepcopy(health_mon)
            health_mon_policy['pools'] = [hm]
            vip_id = self._get_vip_id_by_pool_id(hm['pool_id'])
            result, nwa_data = self.nwa_setting_lb_policy(
                context, tid, nwa_tid, POLICY_TYPE_HEALTHMONITOR, POLICY_DELETE,
                health_mon_policy, vip_id
            )

        return

    # driver api.
    def create_pool(self, context, pool):
        LOG.debug("pool=%s" % json.dumps(
            pool,
            indent=4,
            sort_keys=True
        ))
        self.update_status('pool', pool['id'], n_constants.ACTIVE)

    def update_pool(self, context, old_pool, pool):
        LOG.debug("old_pool=%s" % json.dumps(
            old_pool,
            indent=4,
            sort_keys=True
        ))
        LOG.debug("pool=%s" % json.dumps(
            pool,
            indent=4,
            sort_keys=True
        ))
        self.update_status('pool', pool['id'], n_constants.ACTIVE)

    def delete_pool(self, context, pool):
        LOG.debug("pool=%s" % json.dumps(
            pool,
            indent=4,
            sort_keys=True
        ))

    def create_vip(self, context, vip):
        self._create_vip(context, vip)
        self.lbaas_plugin_rpc.update_status(
            'vip', vip['id'], n_constants.ACTIVE
        )

    def update_vip(self, context, old_vip, vip):
        self._update_vip(context, old_vip, vip)
        self.lbaas_plugin_rpc.update_status(
            'vip', vip['id'], n_constants.ACTIVE
        )

    def delete_vip(self, context, vip):
        LOG.debug("vip=%s" % json.dumps(
            vip,
            indent=4,
            sort_keys=True
        ))
        self._delete_vip(context, vip)

    def create_member(self, context, member):
        self._create_member(context, member)

        self.lbaas_plugin_rpc.update_status(
            'member', member['id'], n_constants.ACTIVE
        )

    def update_member(self, context, old_member, member):
        self._update_member(context, old_member, member)
        self.lbaas_plugin_rpc.update_status(
            'member', member['id'], n_constants.ACTIVE
        )

    def delete_member(self, context, member):
        self._delete_member(context, member)

    def create_pool_health_monitor(self, context, health_monitor, pool_id):
        self._create_pool_health_monitor(context, health_monitor, pool_id)

    def update_pool_health_monitor(self, context, old_health_monitor,
                                   health_monitor, pool_id):
        self._update_pool_health_monitor(
            context, old_health_monitor, health_monitor, pool_id
        )

    def delete_pool_health_monitor(self, context, health_monitor, pool_id):
        self._delete_pool_health_monitor(context, health_monitor, pool_id)

    def _get_vip_id_by_pool_id(self, pool_id):
        logical_config = self.lbaas_plugin_rpc.get_logical_device(
            pool_id
        )
        return logical_config['vip']['id']

    def _create_policy_data(self, ptype, obj):
        for key in obj.keys():
            if not key in POLICY_MAP[ptype]:
                obj.pop(key)

        return obj
