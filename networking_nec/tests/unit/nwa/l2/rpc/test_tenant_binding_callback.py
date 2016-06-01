# Copyright 2016 NEC Corporation.  All rights reserved.
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

import mock
from neutron.tests import base

from networking_nec.nwa.l2.rpc import tenant_binding_callback as tenant_cb


class TestTenantBindingServerRpcCallback(base.BaseTestCase):

    def setUp(self):
        super(TestTenantBindingServerRpcCallback, self).setUp()
        self.rpc_context = mock.MagicMock()
        self.callback = tenant_cb.TenantBindingServerRpcCallback()

    @mock.patch('neutron.db.api.get_session')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    @mock.patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_queues')
    def test_update_tenant_rpc_servers_both_empty(self, gntq, gs, gp):
        gntq.return_value = []
        kwargs = {'servers': []}
        rd = self.callback.update_tenant_rpc_servers(self.rpc_context,
                                                     **kwargs)
        self.assertEqual(rd, {'servers': []})

    @mock.patch('neutron.db.api.get_session')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    @mock.patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_queues')
    def test_update_tenant_rpc_servers_both_equal(self, gntq, plugin, gs):
        q1 = mock.MagicMock()
        q1.tenant_id = 'T-1'
        gntq.return_value = [q1]
        kwargs = {'servers': [{'tenant_id': 'T-1'}]}
        rd = self.callback.update_tenant_rpc_servers(self.rpc_context,
                                                     **kwargs)
        self.assertEqual(rd, {'servers': []})
        self.assertEqual(plugin.nwa_rpc.create_server.call_count, 0)
        self.assertEqual(plugin.nwa_rpc.delete_server.call_count, 0)

    @mock.patch('neutron.db.api.get_session')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    @mock.patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_queues')
    def test_update_tenant_rpc_servers_create(self, gntq, gp, gs):
        q1 = mock.MagicMock()
        q1.tenant_id = 'T-2'
        gntq.return_value = [q1]
        plugin = mock.MagicMock()
        gp.return_value = plugin
        plugin.nwa_rpc.create_server = mock.MagicMock()
        kwargs = {'servers': []}
        rd = self.callback.update_tenant_rpc_servers(self.rpc_context,
                                                     **kwargs)
        self.assertEqual(rd, {'servers': [{'tenant_id': 'T-2'}]})
        self.assertEqual(plugin.nwa_rpc.create_server.call_count, 1)
        self.assertEqual(plugin.nwa_rpc.delete_server.call_count, 0)

    @mock.patch('neutron.db.api.get_session')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    @mock.patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_queues')
    def test_update_tenant_rpc_servers_delete(self, gntq, gp, gs):
        gntq.return_value = []
        plugin = mock.MagicMock()
        gp.return_value = plugin
        plugin.nwa_rpc.create_server = mock.MagicMock()
        kwargs = {'servers': [{'tenant_id': 'T-1'}]}
        rd = self.callback.update_tenant_rpc_servers(self.rpc_context,
                                                     **kwargs)
        self.assertEqual(rd, {'servers': []})
        self.assertEqual(plugin.nwa_rpc.create_server.call_count, 0)
        self.assertEqual(plugin.nwa_rpc.delete_server.call_count, 1)
