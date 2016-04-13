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

import eventlet
import mock

from networking_nec.nwa.agent import server_manager
from networking_nec.nwa.common import constants as nwa_const
from networking_nec.tests.unit.nwa.agent import base


class TestAgentServerManager(base.TestNWAAgentBase):

    @mock.patch('oslo_messaging.server.MessageHandlingServer')
    def test_create_tenant_rpc_server(self, f1):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        rd = self.agent.server_manager.create_tenant_rpc_server(tenant_id)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['result'], 'SUCCESS')
        self.assertEqual(rd['tenant_id'], tenant_id)

    def _wait_greenpool_resized(self, *args, **kwargs):
        class Server(object):
            def start(self):
                eventlet.sleep(5)
        return Server()

    @mock.patch('oslo_messaging.server.MessageHandlingServer')
    def test_create_tenant_rpc_server_greenpool_resize(self, mhs):
        poolsize = 3
        manager = server_manager.ServerManager(self.agent.topic, self.agent,
                                               size=poolsize)
        mhs.side_effect = self._wait_greenpool_resized
        for i in range(poolsize + 1):
            tenant_id = 'T-%d' % i
            rd = manager.create_tenant_rpc_server(tenant_id)
            self.assertIsInstance(rd, dict)
            self.assertEqual(rd['result'], 'SUCCESS')
            self.assertEqual(rd['tenant_id'], tenant_id)
        self.assertEqual(manager.greenpool_size,
                         poolsize + nwa_const.NWA_GREENPOOL_ADD_SIZE)

    @mock.patch('oslo_messaging.rpc.server.get_rpc_server')
    @mock.patch('networking_nec.nwa.agent.nwa_agent')
    @mock.patch('neutron.common.rpc.Connection')
    @mock.patch('neutron.agent.rpc.PluginReportStateAPI')
    @mock.patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi')
    def test_create_tenant_rpc_server_fail(self, f1, f2, f3, f4, f5):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.agent.server_manager.rpc_servers[tenant_id] = {
            'server': None,
            'topic': "%s-%s" % (self.agent.topic, tenant_id)
        }
        rd = self.agent.server_manager.create_tenant_rpc_server(tenant_id)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['result'], 'FAILED')

    @mock.patch('oslo_messaging.rpc.server.get_rpc_server')
    def test_delete_tenant_rpc_server(self, f1):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.agent.server_manager.rpc_servers = {
            tenant_id: {
                'server': f1,
                'topic': "%s-%s" % (self.agent.topic, tenant_id)
            }
        }
        rd = self.agent.server_manager.delete_tenant_rpc_server(tenant_id)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['result'], 'SUCCESS')
        self.assertEqual(rd['tenant_id'], tenant_id)

    def test_delete_tenant_rpc_server_fail(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.agent.server_manager.rpc_servers = {}
        rd = self.agent.server_manager.delete_tenant_rpc_server(tenant_id)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['result'], 'FAILED')
