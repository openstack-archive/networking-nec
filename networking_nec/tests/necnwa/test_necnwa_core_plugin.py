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

from neutron.common import constants as q_const
from neutron.common.test_lib import test_config
from neutron.extensions import portbindings
from neutron.tests import base
from oslo_config import cfg
from oslo_log import log as logging

from networking_nec.plugins.necnwa.necnwa_core_plugin import \
    NECNWACorePlugin
from networking_nec.plugins.necnwa.necnwa_core_plugin import \
    NECNWAServerRpcCallbacks

LOG = logging.getLogger(__name__)


class TestNECNWACorePlugin(base.BaseTestCase):

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._setup_rpc')
    @patch('neutron.plugins.ml2.managers.TypeManager.initialize')
    def setUp(self, f1, f2):
        super(TestNECNWACorePlugin, self).setUp()
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

        self.core_plugin = NECNWACorePlugin()

    @patch('neutron.plugins.ml2.db.get_network_segments')
    def test_extend_network_dict_provider_segment_none(self, f1):
        context = MagicMock()
        network = {'id': '99f771b4-af69-45cc-942f-a76be4e8cd1d'}
        f1.return_value = None

        result = self.core_plugin._extend_network_dict_provider(context,
                                                                network)
        self.assertIsNone(result)

    @patch('neutron.plugins.ml2.db.get_network_segments')
    def test_extend_network_dict_provider_segment_one(self, f1):
        context = MagicMock()
        network = {'id': '99f771b4-af69-45cc-942f-a76be4e8cd1d'}
        f1.return_value = [{'segmentation_id': 1000,
                            'network_type': 'vlan',
                            'physical_network': 'OpenStack/DC1/APP'}]

        result = self.core_plugin._extend_network_dict_provider(context,
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

        result = self.core_plugin._extend_network_dict_provider(context,
                                                                network)
        self.assertIsNone(result)

    @patch('neutron.common.rpc.Connection.create_consumer')
    def test_start_rpc_listeners(self, f1):
        self.core_plugin.notifier = MagicMock()
        self.core_plugin.type_manager = MagicMock()
        self.core_plugin.start_rpc_listeners()

    @patch('neutron.db.db_base_plugin_common.'
           'DbBasePluginCommon._make_network_dict')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._extend_network_dict_provider')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.get_network')
    def test_get_network(self, f1, f2, f3):
        id = "99f771b4-af69-45cc-942f-a76be4e8cd1d"
        context = MagicMock()
        fields = MagicMock()
        self.core_plugin.get_network(context, id, fields)

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.get_networks')
    def test_get_networks(self, f1):
        context = MagicMock()
        filters = MagicMock()
        fields = MagicMock()
        sorts = MagicMock()
        limit = MagicMock()
        marker = MagicMock()
        page_reverse = False
        result = self.core_plugin.get_networks(context, filters, fields,
                                               sorts, limit, marker,
                                               page_reverse)
        self.assertTrue(result)


class TestNECNWAServerRpcCallbacks(base.BaseTestCase):

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._setup_rpc')  # noqa
    @patch('neutron.plugins.ml2.managers.TypeManager.initialize')
    def setUp(self, f1, f2):
        super(TestNECNWAServerRpcCallbacks, self).setUp()
        notifier = MagicMock()
        type_manager = MagicMock()

        self.rpc = NECNWAServerRpcCallbacks(notifier, type_manager)

        f1.return_value = None
        f2.return_value = None
        self.core_plugin = NECNWACorePlugin()

        class PortBinding(object):
            segment = {'segmentation_id': 1000,
                       portbindings.VIF_TYPE: 'vlan'}
            vif_type = None

        class PortContext(object):
            bound_segment = None
            current = {'network_id': 'a70fed9f-52b8-4290-a3ed-cdcc837b78d8',
                       portbindings.VIF_TYPE: 'vlan',
                       'admin_state_up': True,
                       'status': q_const.PORT_STATUS_DOWN,
                       'mac_address': '00:0c:29:1f:f5:1c',
                       'fixed_ips': '192.168.1.1',
                       'device_owner': 'compute:DC01_KVM01_ZONE01',
                       portbindings.PROFILE: 'dummy'}

        self.port_binding = PortBinding
        self.port_context = PortContext
        self.port_context.bottom_bound_segment = MagicMock()
        self.port_context.current = MagicMock()

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.get_bound_port_context')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._device_to_port_id')
    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details(self, f1, f2, f3):
        rpc_context = MagicMock()
        f1.return_value = self.core_plugin
        f2.return_value = None
        f3.return_value = None

        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertTrue(device)

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @patch('neutron.plugins.ml2.db.get_network_segments')
    @patch('neutron.db.api.get_session')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.get_bound_port_context')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._device_to_port_id')
    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_no_segment(self, f1, f2, f3, f4, f5, f6):
        rpc_context = MagicMock()
        f1.return_value = self.core_plugin
        f2.return_value = None
        f3.current = True
        f4.begin.return_value = None
        f5.return_value = None

        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertTrue(device)

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @patch('neutron.plugins.ml2.db.get_network_segments')
    @patch('neutron.db.api.get_session')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.get_bound_port_context')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._device_to_port_id')
    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_multi_segment(self, f1, f2, f3, f4, f5, f6):
        rpc_context = MagicMock()
        f1.return_value = self.core_plugin
        f2.return_value = None
        f3.current = True
        f4.begin.return_value = None
        f5.return_value = [{}, {}]

        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertTrue(device)

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @patch('neutron.plugins.ml2.db.get_network_segments')
    @patch('neutron.db.api.get_session')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.get_bound_port_context')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._device_to_port_id')
    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_segment_size_miss_match(self, f1, f2, f3, f4,
                                                        f5, f6):
        rpc_context = MagicMock()
        f1.return_value = self.core_plugin
        f2.return_value = None
        f3.current = True
        f4.begin.return_value = None
        f5.return_value = [{}, {}]

        self.rpc.get_device_details(rpc_context, kwargs={'test': "sample"})

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @patch('neutron.plugins.ml2.db.get_network_segments')
    @patch('neutron.db.api.get_session')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.get_bound_port_context')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._device_to_port_id')
    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_segment_zero(self, f1, f2, f3, f4, f5, f6):
        rpc_context = MagicMock()
        f1.return_value = self.core_plugin
        f2.return_value = None
        f3.current = True
        f3.bottom_bound_segment = MagicMock()
        f4.begin.return_value = None
        f5.return_value = [{'segmentation_id': 0}]
        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertIsInstance(device, dict)

    @patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @patch('networking_nec.plugins.necnwa.db.api.ensure_port_binding')
    @patch('neutron.plugins.ml2.db.get_network_segments')
    @patch('neutron.db.api.get_session')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.get_bound_port_context')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._device_to_port_id')
    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_segment_not_binding(self, f1, f2, f3, f4, f5,
                                                    f6, f7):
        rpc_context = MagicMock()
        f1.return_value = self.core_plugin
        f2.return_value = None
        f3.current = True
        f4.begin.return_value = None
        f5.return_value = [{'segmentation_id': 1000}]

        class PortBinding(object):
            segment = None
            vif_type = None

        f6.return_value = PortBinding()

        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertTrue(device)

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.update_port_status')
    @patch('networking_nec.plugins.necnwa.db.api.ensure_port_binding')
    @patch('neutron.plugins.ml2.db.get_network_segments')
    @patch('neutron.db.api.get_session')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.get_bound_port_context')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._device_to_port_id')
    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_bound_segment(self, f1, f2, f3, f4, f5,
                                              f6, f7):

        rpc_context = MagicMock()
        f1.return_value = self.core_plugin
        f2.return_value = None
        f3.return_value = self.port_context
        f4.begin.return_value = None
        f5.return_value = [{'segmentation_id': 1000,
                            'network_type': 'vlan',
                            'physical_network': 'OpenStack/DC1/APP'}]
        f6.return_value = self.port_binding

        device = self.rpc.get_device_details(rpc_context,
                                             kwargs={'test': "sample"})
        self.assertTrue(device)

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.update_port_status')
    @patch('networking_nec.plugins.necnwa.db.api.ensure_port_binding')
    @patch('neutron.plugins.ml2.db.get_network_segments')
    @patch('neutron.db.api.get_session')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin.get_bound_port_context')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.'
           'NECNWACorePlugin._device_to_port_id')
    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_port_state_change(self, f1, f2, f3, f4, f5,
                                                  f6, f7):

        rpc_context = MagicMock()
        f1.return_value = self.core_plugin
        f2.return_value = None

        self.port_context.bound_segment = 'dummy segment'
        f3.return_value = self.port_context
        f4.begin.return_value = None
        f5.return_value = [{'segmentation_id': 1000,
                            'network_type': 'vlan',
                            'physical_network': 'OpenStack/DC1/APP'}]
        f6.return_value = self.port_binding

        device = self.rpc.get_device_details(rpc_context,
                                             kwargs={'test': "sample"})
        self.assertTrue(device)

    @patch('neutron.manager.NeutronManager.get_plugin')
    def test_update_device_up(self, dummy1):
        rpc_context = MagicMock()
        dummy1.return_value = None
        self.rpc.update_device_up(rpc_context)
