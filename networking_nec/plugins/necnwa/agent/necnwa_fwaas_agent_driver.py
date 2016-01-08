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

from neutron.common import topics
from oslo_log import log as logging

from networking_nec.plugins.necnwa import necnwa_utils

from neutron.agent.l3.agent import (
    L3PluginApi
)

from networking_nec.plugins.necnwa.agent.agent_base_driver import (
    NECNWAAgentBaseDriver,
    POLICY_RULE,
    POLICY_PERMIT,
    POLICY_DENY,
    POLICY_CREATE,
    POLICY_UPDATE,
    POLICY_DELETE
)

from neutron.plugins.common import constants as n_constants
from neutron_fwaas.services.firewall.agents.firewall_agent_api import FWaaSPluginApiMixin
from networking_nec.plugins.necnwa.agent import necnwa_agent_rpc

LOG = logging.getLogger(__name__)


class NECNWAFirewallAgentDriver(NECNWAAgentBaseDriver):

    def __init__(self, agent, context):
        super(NECNWAFirewallAgentDriver, self).__init__(agent, context)

        self.fwaas_plugin_rpc = FWaaSPluginApiMixin(
            necnwa_agent_rpc.NWA_FIREWALL_PLUGIN,
            self.conf.host
        )
        self.l3_plugin_rpc = L3PluginApi(
            topics.L3PLUGIN,
            self.conf.host)

        self.context = context

    # Rpc
    def update_status(self, context, firewall_id, status):
        self.fwaas_plugin_rpc.set_firewall_status(context, firewall_id, status)

    # FWaaS NWA API call
    def create_firewall(self, context, **kwargs):
        LOG.debug("kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))

        firewall = kwargs.get('firewall')

        all_routers = self.l3_plugin_rpc.get_routers(context)
        
        routers = [
            router['id']
            for router in all_routers
            if router['tenant_id'] == firewall['tenant_id']]

        tid = firewall['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)

        router_ids = firewall['add-router-ids']

        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        for router_id in router_ids:
            if 'DEV_' + router_id + '_TenantFWName' in nwa_data.keys():
                tfw = nwa_data['DEV_' + router_id + '_TenantFWName']
                self.nwa_setting_fw_policy(context, tid, nwa_tid, tfw, firewall, POLICY_RULE, POLICY_CREATE)

        self.fwaas_plugin_rpc.set_firewall_status(context, firewall['id'], n_constants.ACTIVE)

        return

    def update_firewall(self, context, **kwargs):
        LOG.debug("kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))

        firewall = kwargs.get('firewall')
        tid = firewall['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)

        add_router_ids = firewall['add-router-ids']
        del_router_ids = firewall['del-router-ids']
        router_ids = firewall['router_ids']

        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        for router_id in firewall['router_ids']:
            if 'DEV_' + router_id + '_TenantFWName' in nwa_data.keys():
                tfw = nwa_data['DEV_' + router_id + '_TenantFWName']
                # set rules
                LOG.debug("set policy in router.")
                self.nwa_setting_fw_policy(context, tid, nwa_tid, tfw, firewall, POLICY_RULE, POLICY_UPDATE)

        for router_id in add_router_ids:
            if router_id in router_ids:
                continue

            router_key = 'DEV_' + router_id + '_TenantFWName'
            if router_key in nwa_data.keys():
                tfw = nwa_data[router_key]
                # set all deny
                LOG.debug("set policy in router.")
                #self.nwa_setting_fw_policy(context, tid, nwa_tid, tfw, firewall, POLICY_RULE, POLICY_CREATE)
                self.nwa_setting_fw_policy(context, tid, nwa_tid, tfw, firewall, POLICY_RULE, POLICY_UPDATE)

        for router_id in del_router_ids:
            router_key = 'DEV_' + router_id + '_TenantFWName'
            if router_key in nwa_data.keys():
                tfw = nwa_data[router_key]
                # set all permit
                LOG.debug("remove policy in router.(set all permit)")
                #self.nwa_setting_fw_policy(context, tid, nwa_tid, tfw, firewall, POLICY_RULE, POLICY_DELETE)
                self.nwa_setting_fw_policy(context, tid, nwa_tid, tfw, firewall, POLICY_PERMIT, POLICY_UPDATE)

        self.fwaas_plugin_rpc.set_firewall_status(context, firewall['id'], n_constants.ACTIVE)

        return

    def delete_firewall(self, context, **kwargs):
        LOG.debug("kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))

        firewall = kwargs.get('firewall')
        tid = firewall['tenant_id']
        nwa_tid = necnwa_utils.get_nwa_tenant_id(tid)

        router_ids = firewall['del-router-ids']

        if not router_ids:
            return

        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        for router_id in router_ids:
            if 'DEV_' + router_id + '_TenantFWName' in nwa_data.keys():
                tfw = nwa_data['DEV_' + router_id + '_TenantFWName']
                # set all deny or empty rules
                self.nwa_setting_fw_policy(context, tid, nwa_tid, tfw, firewall, POLICY_RULE, POLICY_DELETE)

        self.fwaas_plugin_rpc.firewall_deleted(context, firewall['id'])

        return
