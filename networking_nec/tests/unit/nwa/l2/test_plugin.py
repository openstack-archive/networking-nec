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
from oslo_log import log as logging

from networking_nec.plugins.necnwa.l2 import plugin

LOG = logging.getLogger(__name__)


class TestNECNWAL2Plugin(base.BaseTestCase):

    @patch('networking_nec.plugins.necnwa.l2.plugin.'
           'NECNWAL2Plugin._setup_rpc')
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
    @patch('networking_nec.plugins.necnwa.l2.plugin.'
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
