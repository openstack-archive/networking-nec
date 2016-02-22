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
import oslo_messaging


class TenantBindingServerRpcApi(object):

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, topic):
        target = oslo_messaging.Target(topic=topic,
                                       version=self.BASE_RPC_API_VERSION)
        self.client = n_rpc.get_client(target)

    def get_nwa_tenant_binding(self, context, tenant_id, nwa_tenant_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'get_nwa_tenant_binding',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id
        )

    def add_nwa_tenant_binding(self, context, tenant_id,
                               nwa_tenant_id, nwa_data):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'add_nwa_tenant_binding',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data
        )

    def set_nwa_tenant_binding(self, context, tenant_id,
                               nwa_tenant_id, nwa_data):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'set_nwa_tenant_binding',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data
        )

    def delete_nwa_tenant_binding(self, context, tenant_id,
                                  nwa_tenant_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'delete_nwa_tenant_binding',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id
        )

    def update_tenant_rpc_servers(self, context, rpc_servers):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'update_tenant_rpc_servers',
            servers=rpc_servers
        )
