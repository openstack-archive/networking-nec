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

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class NwaAgentRpcCallback(object):
    RPC_API_VERSION = '1.0'

    def __init__(self, context, agent):
        self.context = context
        self.agent = agent

    def get_nwa_rpc_servers(self, context, **kwargs):
        LOG.debug("kwargs=%s", kwargs)
        return {'nwa_rpc_servers':
                [
                    {
                        'tenant_id': k,
                        'topic': v['topic']
                    } for k, v in self.agent.rpc_servers.items()
                ]}

    def create_server(self, context, **kwargs):
        LOG.debug("kwargs=%s", kwargs)
        tenant_id = kwargs.get('tenant_id')
        return self.agent.create_tenant_rpc_server(tenant_id)

    def delete_server(self, context, **kwargs):
        LOG.debug("kwargs=%s", kwargs)
        tenant_id = kwargs.get('tenant_id')
        return self.agent.delete_tenant_rpc_server(tenant_id)
