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

from oslo_log import helpers
import oslo_messaging


class NwaAgentRpcCallback(object):

    target = oslo_messaging.Target(version='1.0')

    def __init__(self, context, agent):
        self.context = context
        self.agent = agent

    @helpers.log_method_call
    def get_nwa_rpc_servers(self, context, **kwargs):
        return {'nwa_rpc_servers':
                [
                    {
                        'tenant_id': k,
                        'topic': v['topic']
                    } for k, v in self.agent.rpc_servers.items()
                ]}

    @helpers.log_method_call
    def create_server(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        return self.agent.create_tenant_rpc_server(tenant_id)

    @helpers.log_method_call
    def delete_server(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        return self.agent.delete_tenant_rpc_server(tenant_id)
