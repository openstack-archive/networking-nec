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


from neutron.common import rpc as n_rpc
from oslo_log import log as logging
import oslo_messaging

LOG = logging.getLogger(__name__)

NWA_AGENT_TOPIC = 'nwa_agent'
GENERALDEV = 'generaldev'
TENANTFW = 'tenantfw'
NWA_AGENT_TYPE = 'NEC NWA Agent'
NWA_FIREWALL_PLUGIN = 'NECNWAFWaaS'


class NECNWAAgentApi(object):
    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, topic):
        target = oslo_messaging.Target(topic=topic,
                                       version=self.BASE_RPC_API_VERSION)
        self.client = n_rpc.get_client(target)

    def create_server(self, context, tenant_id):
        cctxt = self.client.prepare()
        return cctxt.cast(context, 'create_server', tenant_id=tenant_id)

    def delete_server(self, context, tenant_id):
        cctxt = self.client.prepare()
        return cctxt.cast(context, 'delete_server', tenant_id=tenant_id)

    def get_nwa_rpc_servers(self, context):
        cctxt = self.client.prepare()
        return cctxt.call(context, 'get_nwa_rpc_servers')


class NECNWAProxyApi(object):
    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, topic, tenant_id):
        target = oslo_messaging.Target(topic='%s-%s' % (topic, tenant_id),
                                       version=self.BASE_RPC_API_VERSION)
        self.client = n_rpc.get_client(target)

    def _send_msg(self, context, msg, blocking=False):
        cctxt = self.client.prepare()
        if blocking:
            return cctxt.call(context, msg)
        else:
            return cctxt.cast(context, msg)

    def get_tenant_queue(self, context):
        return self._send_msg(
            context, self.make_msg('get_tenant_ids')
        )

    def create_general_dev(self, context, tenant_id, nwa_tenant_id, nwa_info):
        cctxt = self.client.prepare()
        return cctxt.cast(
            context,
            'create_general_dev',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    def delete_general_dev(self, context, tenant_id, nwa_tenant_id, nwa_info):
        cctxt = self.client.prepare()
        return cctxt.cast(
            context,
            'delete_general_dev',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )
