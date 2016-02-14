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

from neutron.common import topics
from oslo_log import log as logging

from networking_nec.plugins.necnwa.l2.rpc import nwa_l2_server_api
from networking_nec.plugins.necnwa.l2.rpc import tenant_binding_api

LOG = logging.getLogger(__name__)

KEY_CREATE_TENANT_NW = 'CreateTenantNW'
WAIT_AGENT_NOTIFIER = 20
# WAIT_AGENT_NOTIFIER = 1

VLAN_OWN_GDV = '_GD'
VLAN_OWN_TFW = '_TFW'

all_deny_rule = {"Policy": {"Rules": [{"action": "deny"}]}}
all_allow_rule = {"Policy": {"Rules": [{"action": "allow"}]}}

all_permit_policies = {
    "policies": [{"policy_id": "65535",
                  "originating_address_group_id": "all",
                  "delivery_address_group_id": "all",
                  "delivery_address_type": "0",
                  "device_type": "1",
                  "fwl_service_id_data": ["ALL"],
                  "used_global_ip_out": "0"}],
    "operation_type": "Update"
}

all_deny_policies = {
    "policies": [{"policy_id": "65535",
                  "originating_address_group_id": "all",
                  "delivery_address_group_id": "all",
                  "delivery_address_type": "0",
                  "device_type": "0",
                  "fwl_service_id_data": ["ALL"],
                  "used_global_ip_out": "0"}],
    "operation_type": "Update"
}


class AgentProxyFWaaS(object):

    def __init__(self, agent_top, client, proxy_tenant, proxy_l2, fwaas):
        self.nwa_tenant_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN)
        self.nwa_l2_rpc = nwa_l2_server_api.NwaL2ServerRpcApi(topics.PLUGIN)
        self.agent_top = agent_top
        self.client = client
        self.proxy_tenant = proxy_tenant
        self.proxy_l2 = proxy_l2
        self.fwaas = fwaas

    def _setting_fw_policy_all_deny(self, context, tfw, **kwargs):

        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        rcode, body = self.client.setting_fw_policy(
            nwa_tenant_id,
            tfw,
            all_deny_policies
        )
        if (
                rcode == 200 and
                body['status'] == 'SUCCESS'
        ):
            LOG.debug("success body=%s", body)
        else:
            LOG.debug("success error=%s", body)

    def _setting_fw_policy_all_permit(self, context, tfw, **kwargs):

        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        rcode, body = self.client.setting_fw_policy(
            nwa_tenant_id,
            tfw,
            all_permit_policies
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCESS'
        ):
            LOG.debug("success body=%s", body)
        else:
            LOG.debug("success error=%s", body)

    def _dummy_ok(self, context, rcode, jbody, *args, **kargs):
        pass

    def _dummy_ng(self, context, rcode, jbody, *args, **kargs):
        pass
