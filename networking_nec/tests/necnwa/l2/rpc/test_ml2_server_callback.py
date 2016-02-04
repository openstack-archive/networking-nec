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

import mock
from neutron.common import constants as q_const
from neutron.extensions import portbindings
from neutron.tests import base

from networking_nec.plugins.necnwa.l2 import plugin
from networking_nec.plugins.necnwa.l2.rpc import ml2_server_callback


class TestNECNWAServerRpcCallbacks(base.BaseTestCase):

    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._setup_rpc')
    @mock.patch('neutron.plugins.ml2.managers.TypeManager.initialize')
    def setUp(self, f1, f2):
        super(TestNECNWAServerRpcCallbacks, self).setUp()
        notifier = mock.MagicMock()
        type_manager = mock.MagicMock()

        self.rpc = ml2_server_callback.NwaML2ServerRpcCallbacks(
            notifier, type_manager)

        f1.return_value = None
        f2.return_value = None
        self.l2_plugin = plugin.NECNWAL2Plugin()

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
        self.port_context.bottom_bound_segment = mock.MagicMock()
        self.port_context.current = mock.MagicMock()

    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.get_bound_port_context')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._device_to_port_id')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details(self, f1, f2, f3):
        rpc_context = mock.MagicMock()
        f1.return_value = self.l2_plugin
        f2.return_value = None
        f3.return_value = None

        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertTrue(device)

    @mock.patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @mock.patch('neutron.plugins.ml2.db.get_network_segments')
    @mock.patch('neutron.db.api.get_session')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.get_bound_port_context')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._device_to_port_id')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_no_segment(self, f1, f2, f3, f4, f5, f6):
        rpc_context = mock.MagicMock()
        f1.return_value = self.l2_plugin
        f2.return_value = None
        f3.current = True
        f4.begin.return_value = None
        f5.return_value = None

        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertTrue(device)

    @mock.patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @mock.patch('neutron.plugins.ml2.db.get_network_segments')
    @mock.patch('neutron.db.api.get_session')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.get_bound_port_context')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._device_to_port_id')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_multi_segment(self, f1, f2, f3, f4, f5, f6):
        rpc_context = mock.MagicMock()
        f1.return_value = self.l2_plugin
        f2.return_value = None
        f3.current = True
        f4.begin.return_value = None
        f5.return_value = [{}, {}]

        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertTrue(device)

    @mock.patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @mock.patch('neutron.plugins.ml2.db.get_network_segments')
    @mock.patch('neutron.db.api.get_session')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.get_bound_port_context')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._device_to_port_id')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_segment_size_miss_match(self, f1, f2, f3, f4,
                                                        f5, f6):
        rpc_context = mock.MagicMock()
        f1.return_value = self.l2_plugin
        f2.return_value = None
        f3.current = True
        f4.begin.return_value = None
        f5.return_value = [{}, {}]

        self.rpc.get_device_details(rpc_context, kwargs={'test': "sample"})

    @mock.patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @mock.patch('neutron.plugins.ml2.db.get_network_segments')
    @mock.patch('neutron.db.api.get_session')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.get_bound_port_context')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._device_to_port_id')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_segment_zero(self, f1, f2, f3, f4, f5, f6):
        rpc_context = mock.MagicMock()
        f1.return_value = self.l2_plugin
        f2.return_value = None
        f3.current = True
        f3.bottom_bound_segment = mock.MagicMock()
        f4.begin.return_value = None
        f5.return_value = [{'segmentation_id': 0}]
        device = self.rpc.get_device_details(rpc_context, kwargs={'test':
                                                                  "sample"})
        self.assertIsInstance(device, dict)

    @mock.patch('neutron.plugins.ml2.plugin.Ml2Plugin.update_port_status')
    @mock.patch('networking_nec.plugins.necnwa.l2.db_api.ensure_port_binding')
    @mock.patch('neutron.plugins.ml2.db.get_network_segments')
    @mock.patch('neutron.db.api.get_session')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.get_bound_port_context')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._device_to_port_id')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_segment_not_binding(self, f1, f2, f3, f4, f5,
                                                    f6, f7):
        rpc_context = mock.MagicMock()
        f1.return_value = self.l2_plugin
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

    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.update_port_status')
    @mock.patch('networking_nec.plugins.necnwa.l2.db_api.ensure_port_binding')
    @mock.patch('neutron.plugins.ml2.db.get_network_segments')
    @mock.patch('neutron.db.api.get_session')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.get_bound_port_context')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._device_to_port_id')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_bound_segment(self, f1, f2, f3, f4, f5,
                                              f6, f7):

        rpc_context = mock.MagicMock()
        f1.return_value = self.l2_plugin
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

    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.update_port_status')
    @mock.patch('networking_nec.plugins.necnwa.l2.db_api.ensure_port_binding')
    @mock.patch('neutron.plugins.ml2.db.get_network_segments')
    @mock.patch('neutron.db.api.get_session')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin.get_bound_port_context')
    @mock.patch('networking_nec.plugins.necnwa.l2.plugin.'
                'NECNWAL2Plugin._device_to_port_id')
    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_get_device_details_port_state_change(self, f1, f2, f3, f4, f5,
                                                  f6, f7):

        rpc_context = mock.MagicMock()
        f1.return_value = self.l2_plugin
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

    @mock.patch('neutron.manager.NeutronManager.get_plugin')
    def test_update_device_up(self, dummy1):
        rpc_context = mock.MagicMock()
        dummy1.return_value = None
        self.rpc.update_device_up(rpc_context)
