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

from mock import MagicMock
from mock import patch
import six

from neutron.common.test_lib import test_config
from neutron.tests import base
from oslo_config import cfg

from networking_nec.nwa.l2 import plugin


class TestNECNWAL2Plugin(base.BaseTestCase):

    @patch('networking_nec.nwa.l2.plugin.NECNWAL2Plugin._setup_rpc')
    @patch('neutron.plugins.ml2.managers.TypeManager.initialize')
    def setUp(self, f1, f2):
        super(TestNECNWAL2Plugin, self).setUp()
        l3_plugin = ('neutron.tests.unit.test_l3_plugin.'
                     'TestL3NatServicePlugin')

        service_plugins = {'l3_plugin_name': l3_plugin}

        cfg.CONF.set_override(
            'service_plugins',
            [test_config.get(key, default)
             for key, default in six.iteritems(service_plugins or {})]
        )

        f1.return_value = None
        f2.return_value = None

        self.l2_plugin = plugin.NECNWAL2Plugin()

    def test_extend_network_dict_providor_no_id(self):
        context = MagicMock()
        network = {}

        result = self.l2_plugin._extend_network_dict_provider(context,
                                                              network)

        self.assertIsNone(result)

    @patch('neutron.plugins.ml2.db.get_network_segments')
    def test_extend_network_dict_provider_segment_none(self, f1):
        context = MagicMock()
        network = {'id': '99f771b4-af69-45cc-942f-a76be4e8cd1d'}
        f1.return_value = None

        result = self.l2_plugin._extend_network_dict_provider(context,
                                                              network)
        self.assertIsNone(result)

    @patch('neutron.plugins.ml2.db.get_network_segments')
    def test_extend_network_dict_provider_segment_one(self, f1):
        context = MagicMock()
        network = {'id': '99f771b4-af69-45cc-942f-a76be4e8cd1d'}
        f1.return_value = [{'segmentation_id': 1000,
                            'network_type': 'vlan',
                            'physical_network': 'OpenStack/DC1/APP'}]

        result = self.l2_plugin._extend_network_dict_provider(context,
                                                              network)
        self.assertIsNone(result)

    @patch('neutron.plugins.ml2.db.get_network_segments')
    def test_extend_network_dict_provider_segment_multi(self, f1):
        context = MagicMock()
        network = {'id': '99f771b4-af69-45cc-942f-a76be4e8cd1d'}
        f1.return_value = [{'segmentation_id': 1000,
                            'network_type': 'vlan',
                            'physical_network': 'OpenStack/DC1/APP'},
                           {'segmentation_id': 1001,
                            'network_type': 'vlan',
                            'physical_network': 'OpenStack/DC1/APP'}]

        result = self.l2_plugin._extend_network_dict_provider(context,
                                                              network)
        self.assertIsNone(result)

    @patch('neutron.common.rpc.Connection.create_consumer')
    def test_start_rpc_listeners(self, f1):
        self.l2_plugin.notifier = MagicMock()
        self.l2_plugin.type_manager = MagicMock()
        self.l2_plugin.start_rpc_listeners()

    @patch('neutron.db.db_base_plugin_common.'
           'DbBasePluginCommon._make_network_dict')
    @patch('networking_nec.nwa.l2.plugin.'
           'NECNWAL2Plugin._extend_network_dict_provider')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.get_network')
    def test_get_network(self, f1, f2, f3):
        id = "99f771b4-af69-45cc-942f-a76be4e8cd1d"
        context = MagicMock()
        fields = MagicMock()
        self.l2_plugin.get_network(context, id, fields)

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.get_networks')
    def test_get_networks(self, f1):
        context = MagicMock()
        filters = MagicMock()
        fields = MagicMock()
        sorts = MagicMock()
        limit = MagicMock()
        marker = MagicMock()
        page_reverse = False
        result = self.l2_plugin.get_networks(context, filters, fields,
                                             sorts, limit, marker,
                                             page_reverse)
        self.assertTrue(result)

    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_queue')
    @patch('networking_nec.nwa.l2.plugin.NECNWAL2Plugin._is_alive_nwa_agent')
    def test_create_nwa_agent_tenant_queue(self, f1, f2):
        context = MagicMock()
        tid = 'Tenant1'
        f1.return_value = True
        f2.return_value = None
        self.l2_plugin._create_nwa_agent_tenant_queue(context, tid)

    def test_create_nwa_agent_tenant_queue_not_alive(self):
        context = MagicMock()
        tid = 'Tenant1'
        self.l2_plugin._create_nwa_agent_tenant_queue(context, tid)

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.delete_network')
    @patch('networking_nec.nwa.l2.plugin.'
           'NECNWAL2Plugin._create_nwa_agent_tenant_queue')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.create_network')
    def test_create_delete_network(self, f1, f2, f3):
        context = MagicMock()
        context.tenant_id = 'Tenant1'
        network = {'id': '99f771b4-af69-45cc-942f-a76be4e8cd1d'}

        result = self.l2_plugin.create_network(context, network)

        self.assertTrue(result)

        result = self.l2_plugin.delete_network(context, result.id)

        self.assertTrue(result)

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.create_port')
    def test_create_port(self, f1):
        context = MagicMock()
        port = MagicMock()

        result = self.l2_plugin.create_port(context, port)
        self.assertTrue(result)

    @patch('networking_nec.nwa.l2.rpc.nwa_agent_api.'
           'NECNWAAgentApi.get_nwa_rpc_servers')
    def test_get_nwa_topics(self, f1):
        context = MagicMock()
        id = 'Tenant1'  # Tenant ID
        f1.return_value = {'nwa_rpc_servers':
                           [{'tenant_id': 'Tenant1', 'topic': 'topic1'},
                            {'tenant_id': 'Tenant2', 'topic': 'topic2'},
                            {'tenant_id': 'Tenant1', 'topic': 'topic11'}]}

        result = self.l2_plugin.get_nwa_topics(context, id)
        self.assertEqual(len(result), 2)

    @patch('networking_nec.nwa.l2.rpc.nwa_agent_api.'
           'NECNWAAgentApi.get_nwa_rpc_servers')
    def test_get_nwa_topics_not_dict(self, f1):
        context = MagicMock()
        id = 'Tenant1'  # Tenant ID
        f1.return_value = ['topic1', 'topic2']  # not dict

        result = self.l2_plugin.get_nwa_topics(context, id)
        self.assertEqual(len(result), 0)

    def test_get_nwa_proxy(self):
        tid = 'Tenant1'
        result = self.l2_plugin.get_nwa_proxy(tid)

        self.assertTrue(result)

    def test_get_nwa_proxy_in_nwa_proxies(self):
        tid = 'Tenant1'
        proxy = MagicMock()
        self.l2_plugin.nwa_proxies = {tid: proxy}
        result = self.l2_plugin.get_nwa_proxy(tid)

        self.assertEqual(result, proxy)

    @patch('networking_nec.nwa.l2.plugin.NECNWAL2Plugin.get_nwa_topics')
    def test_get_nwa_proxy_with_context(self, f1):
        tid = 'Tenant1'
        context = MagicMock()
        f1.return_value = ['topic1']
        result = self.l2_plugin.get_nwa_proxy(tid, context)

        self.assertTrue(result)

    @patch('networking_nec.nwa.l2.plugin.NECNWAL2Plugin.get_nwa_topics')
    def test_get_nwa_proxy_no_topics(self, f1):
        tid = 'Tenant1'
        context = MagicMock()
        f1.return_value = []
        result = self.l2_plugin.get_nwa_proxy(tid, context)

        self.assertTrue(result)

    @patch('networking_nec.nwa.l2.plugin.NECNWAL2Plugin.get_agents')
    def test_is_alive_nwa_agent(self, f1):
        context = MagicMock()
        f1.return_value = [{'alive': True}, {'alive': False}]

        result = self.l2_plugin._is_alive_nwa_agent(context)
        self.assertTrue(result)

    @patch('networking_nec.nwa.l2.plugin.NECNWAL2Plugin.get_agents')
    def test_is_alive_nwa_agent_not_alive(self, f1):
        context = MagicMock()
        f1.return_value = [{'alive': False}]

        result = self.l2_plugin._is_alive_nwa_agent(context)
        self.assertFalse(result)

    def test_get_port_from_device(self):
        context = MagicMock()
        device = 'device'
        self.l2_plugin.get_port_from_device(context, device)
