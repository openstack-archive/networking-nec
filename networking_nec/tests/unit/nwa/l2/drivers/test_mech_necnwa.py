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

from neutron.common import constants as neutron_const
from neutron import context
from neutron.extensions import providernet as prov_net
from neutron.tests.unit import testlib_api
from neutron_lib import constants
from oslo_config import cfg
from oslo_serialization import jsonutils

from networking_nec.nwa.common import constants as nwa_const
from networking_nec.nwa.common import exceptions as nwa_exc
from networking_nec.nwa.l2.drivers import mech_necnwa as mech


class TestMechNwa(testlib_api.SqlTestCase):
    def setUp(self):
        super(TestMechNwa, self).setUp()

        class network_context(object):
            network = MagicMock()
            current = MagicMock()
            _plugin = MagicMock()
            _plugin_context = MagicMock()
            _binding = MagicMock()

            _plugin_context.session = context.get_admin_context().session

            def set_binding(self, segment_id, vif_type, vif_details,
                            status=None):
                self._binding.segment = segment_id
                self._binding.vif_type = vif_type
                self._binding.vif_details = vif_details
                self._new_port_status = status

        self.context = network_context()
        self.context.network.current = {
            'tenant_id': 'tenant201',
            'name': 'tenant 201',
            'id': '61',
            'network_type': 'vlan',
            'physical_network': 'Common/App/Pod3',
            'segments': []
        }
        self.context._port = {
            'binding:vif_details': {},
            'binding:vif_type': 'ovs',
            'binding:vnic_type': 'normal',
            'id': 'uuid-port-100',
            'device_owner': constants.DEVICE_OWNER_ROUTER_INTF,
            'device_id': 'uuid-device_id_100',
            'fixed_ips': [
                {'ip_address': '192.168.120.1',
                 'subnet_id': '65e6bc06-09b5-4a16-b093-cbc177818b9e'}
            ],
            'mac_address': '12:34:56:78:9a:bc'
        }
        self.context._binding.segment = ''
        self.context._binding.vif_type = ''

        self.host_agents = [
            {
                "binary": "neutron-openvswitch-agent",
                "description": None,
                "admin_state_up": True,
                "alive": True,
                "topic": "N/A",
                "host": "harry",
                "agent_type": "Open vSwitch agent",
                "id": "a01dc42f-0d15-43ff-8f80-22e15cfe715d",
                "configurations": {
                    "tunnel_types": [],
                    "tunneling_ip": "",
                    "bridge_mappings": {
                        "Common/App/Pod3": "br-eth1",
                        "Common/KVM/Pod1-1": "br-eth2"
                    },
                    "l2_population": False,
                    "devices": 0
                },
                "alive": True
            },
            {
                "binary": "neutron-openvswitch-agent",
                "description": None,
                "admin_state_up": True,
                "alive": True,
                "topic": "N/A",
                "host": "harry",
                "agent_type": "Open vSwitch agent",
                "id": "a01dc42f-0d15-43ff-8f80-22e15cfe715d",
                "configurations": {
                    "tunnel_types": [],
                    "tunneling_ip": "",
                    "bridge_mappings": {
                        "Common/App/Pod4": "br-eth1"
                    },
                    "l2_population": False,
                    "devices": 0
                },
                "alive": False
            }
        ]
        self.context.host_agents = MagicMock(return_value=self.host_agents)

        self.network_segments = [
            {
                "provider:network_type": "vlan",
                "provider:physical_network": "Common/KVM/Pod1-1",
                "id": "uuid-1-1",
                "provider:segmentation_id": 100
            },
            {
                "network_type": "vlan",
                "physical_network": "Common/KVM/Pod1-2",
                "id": "uuid-1-2",
                "provider:segmentation_id": 101
            },
            {
                "provider:network_type": "vlan",
                "provider:physical_network": "Common/App/Pod3",
                "id": "61",
                "provider:segmentation_id": 102
            }
        ]
        self.context.network.network_segments = self.network_segments
        self.context.original = MagicMock()

        resource_group = [
            {
                "physical_network": "Common/KVM/Pod1-1",
                "device_owner": "compute:AZ1",
                "ResourceGroupName": "Common/KVM/Pod1-1"
            },
            {
                "physical_network": "Common/App/Pod3",
                "device_owner": "ironic:isolation",
                "ResourceGroupName": "Common/App/Pod3"
            },
            {
                "physical_network": "Common/App/Pod3",
                "device_owner": "network:dhcp",
                "ResourceGroupName": "Common/App/Pod3"
            },
            {
                "physical_network": "Common/App/Pod3",
                "device_owner": constants.DEVICE_OWNER_ROUTER_GW,
                "ResourceGroupName": "Common/App/Pod3"
            },
            {
                "physical_network": "Common/App/Pod3",
                "device_owner": constants.DEVICE_OWNER_ROUTER_INTF,
                "ResourceGroupName": "Common/App/Pod3"
            }
        ]

        fn_resource_group = self.get_temp_file_path('resource_group.json')
        with open(fn_resource_group, 'w') as f:
            f.write(jsonutils.dumps(resource_group))
        cfg.CONF.set_override('resource_group_file', fn_resource_group,
                              group='NWA')


class TestNECNWAMechanismDriver(TestMechNwa):
    def setUp(self):
        super(TestNECNWAMechanismDriver, self).setUp()
        self.driver = mech.NECNWAMechanismDriver()
        self.driver.initialize()

        self.rcode = MagicMock()
        self.rcode.value_json = {
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201'
        }

    def _get_nwa_tenant_binding(self, value_json):
        rcode = MagicMock()
        rcode.value_json = value_json
        return rcode

    def test_create_port_precommit_compute(self):
        self.context._port['device_owner'] = 'compute:DC01_KVM01_ZONE01'
        self.driver.create_port_precommit(self.context)

    def test_create_port_precommit_group_not_found(self):
        self.driver.resource_groups = [
            {
                "physical_network": "Common/App/Pod3",
                "device_owner": constants.DEVICE_OWNER_ROUTER_GW,
                "ResourceGroupName": "Common/App/Pod3"
            }
        ]
        self.assertRaises(nwa_exc.ResourceGroupNameNotFound,
                          self.driver.create_port_precommit, self.context)

    @patch('networking_nec.nwa.l2.db_api.add_nwa_tenant_binding')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_create_port_precommit_owner_router_intf(self, gntb, antb):
        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self.rcode
        self.driver.create_port_precommit(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_62': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_62_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_62_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.create_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.db_api.add_nwa_tenant_binding')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_create_port_precommit_owner_router_gw(self, gntb, antb):
        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        gntb.return_value = self.rcode
        self.driver.create_port_precommit(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_62': constants.DEVICE_OWNER_ROUTER_GW,
            'DEV_uuid-device_id_100_62_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_62_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.create_port_precommit(self.context)

    def test_update_port_precommit(self):
        for device_owner in (constants.DEVICE_OWNER_ROUTER_INTF,
                             constants.DEVICE_OWNER_ROUTER_GW):
            self.context._port['device_owner'] = device_owner
            self.driver.update_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.utils.portcontext_to_nwa_info')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_update_port_precommit_current_none(self, gntb, ptni):
        self.context.current = self.context._port
        self.context.current['device_id'] = None
        self.context.current['device_owner'] = None
        self.context.original[
            'device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        self.context.original['device_id'] = 'uuid-device_id_000'
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        ptni.return_value = {
            'tenant_id': 'Tenant1',
            'nwa_tenant_id': 'RegionOnetenant201',
            'resource_group_name': 'Common/App/Pod3',
            'physical_network': 'Common/App/Pod3'}
        self.driver.update_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_delete_port_precommit_owner_router_interface(self, gntb, sntb):
        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self.rcode
        self.driver.delete_port_precommit(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc',
            'DEV_uuid-device_id_100_62_ip_address': '192.168.120.2'}
        )
        self.driver.delete_port_precommit(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc',
            'DEV_uuid-device_id_100_62_ip_address': '192.168.120.2'}
        )
        self.driver.delete_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_delete_port_precommit_owner_network_floatingip(self, gntb, sntb):
        self.context._port['device_owner'] = 'network:floatingip'
        gntb.return_value = self.rcode
        router_intf = constants.DEVICE_OWNER_ROUTER_INTF
        self.context._port['device_owner'] = router_intf
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': router_intf,
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc',
            'DEV_uuid-device_id_101_61': '12'}
        )
        self.driver.delete_port_precommit(self.context)

        self.context._port['device_owner'] = router_intf
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': router_intf,
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

        self.context._port['device_owner'] = router_intf
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': router_intf,
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_delete_port_precommit_owner_router_gateway(self, gntb, sntb):
        router_gw = constants.DEVICE_OWNER_ROUTER_GW
        self.context._port['device_owner'] = router_gw
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': 1,
            'CreateTenantNW': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': router_gw,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61': 'public001',
            'DEV_uuid-device_id_100_61_ip_address': '172.16.1.23',
            'DEV_uuid-device_id_100_63_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_delete_port_precommit_owner_floatingip(self, gntb, sntb):
        floatingip = constants.DEVICE_OWNER_FLOATINGIP
        self.context._port['device_owner'] = floatingip
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': 1,
            'CreateTenantNW': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': floatingip,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61': 'public001',
            'DEV_uuid-device_id_100_61_ip_address': '172.16.1.23',
            'DEV_uuid-device_id_100_63_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_delete_port_precommit_owner_none(self, gntb, sntb):
        self.context._port['device_owner'] = ''
        self.context._port['device_id'] = ''
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': 1,
            'CreateTenantNW': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': '',
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61': 'public001',
            'DEV_uuid-device_id_100_61_ip_address': '172.16.1.23',
            'DEV_uuid-device_id_100_63_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.utils.portcontext_to_nwa_info')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_delete_port_precommit_owner_dhcp(self, gntb, ptni):
        self.context._port['device_owner'] = constants.DEVICE_OWNER_DHCP
        self.context._port[
            'device_id'] = neutron_const.DEVICE_ID_RESERVED_DHCP_PORT
        self.context._port['binding:host_id'] = 'myhost'

        # _revert_dhcp_agent_device
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': 1,
            'CreateTenantNW': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': constants.DEVICE_OWNER_DHCP,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61': 'public001',
            'DEV_uuid-device_id_100_61_ip_address': '172.16.1.23',
            'DEV_uuid-device_id_100_63_mac_address': '12:34:56:78:9a:bc'}
        )
        ptni.return_value = {
            'tenant_id': 'Tenant1',
            'nwa_tenant_id': 'RegionOnetenant201',
            'device': {
                'owner': constants.DEVICE_OWNER_DHCP,
                'id': 'device_id'},
            'resource_group_name': 'Common/App/Pod3',
            'physical_network': 'Common/App/Pod3'}
        self.driver.delete_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_delete_port_precommit_owner_compute_az(self, gntb, sntb):
        # 1 net 1 port(compute:AZ1)
        self.context.current = self.context._port
        self.context.current['device_owner'] = 'compute:AZ1'
        self.context._port['device_owner'] = 'compute:AZ1'
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': 'compute:AZ1',
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_GDV,
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

        # 1 net 2 port(compute:AZ1)
        self.context._port['device_owner'] = 'compute:AZ1'
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': 'compute:AZ1',
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_GDV,
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc',
            'DEV_uuid-device_id_200': 'device_id',
            'DEV_uuid-device_id_200_device_owner': 'compute:AZ1',
            'DEV_uuid-device_id_200_61_TYPE': nwa_const.NWA_DEVICE_GDV,
            'DEV_uuid-device_id_200_61': 'net001',
            'DEV_uuid-device_id_200_61_ip_address': '192.168.120.2',
            'DEV_uuid-device_id_200_61_mac_address': 'fe:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(self.context)

    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_try_to_bind_segment_for_agent(self, gntb):
        # in segment
        self.context._port['device_owner'] = 'network:dhcp'
        self.context._port['fixed_ips'] = []
        self.context.current = self.context._port
        rb = self.driver.try_to_bind_segment_for_agent(
            self.context, self.network_segments[1], self.host_agents[0])
        self.assertEqual(rb, True)

        # in physical_network
        self.context.network.current[
            'provider:physical_network'] = 'Common/App/Pod3'
        self.context.network.current['provider:segmentation_id'] = 199
        self.context.current = self.context._port
        rb = self.driver.try_to_bind_segment_for_agent(
            self.context, self.network_segments[1], self.host_agents[0])
        self.assertEqual(rb, True)

        # not in segment
        rb = self.driver.try_to_bind_segment_for_agent(
            self.context, self.network_segments[1], self.host_agents[1])
        self.assertEqual(rb, False)

        # device_owner is router_gw
        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        rb = self.driver.try_to_bind_segment_for_agent(
            self.context, self.network_segments[1], self.host_agents[0])
        self.assertEqual(rb, False)

    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_try_to_bind_segment_for_agent_in_segments(self, gntb):
        # in segment
        self.context._port['device_owner'] = 'network:dhcp'
        self.context.network.current['segments'] = self.network_segments
        self.context.current = self.context._port
        rb = self.driver.try_to_bind_segment_for_agent(
            self.context, self.network_segments[2], self.host_agents[0])
        self.assertEqual(rb, True)

    def test__bind_segment_to_vif_type(self):
        pod3_eth1 = self.host_agents[0]
        rb = self.driver._bind_segment_to_vif_type(self.context, pod3_eth1)
        self.assertEqual(rb, True)

    def test__bind_segment_to_vif_type_no_match(self):
        rb = self.driver._bind_segment_to_vif_type(self.context,
                                                   self.host_agents[1])
        self.assertEqual(rb, False)

    def test__bind_segment_to_vif_type_agent_none(self):
        rb = self.driver._bind_segment_to_vif_type(self.context)
        self.assertEqual(rb, True)

    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__bind_segment_to_vif_type_dummy_segment_none(self, gds):
        gds.return_value = None
        rb = self.driver._bind_segment_to_vif_type(self.context)
        self.assertEqual(rb, True)

    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def _test__bind_port_nwa(self, gntb):
        # if prov_net.PHYSICAL_NETWORK in self.context.network.current:
        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        self.context.network.current[
            'provider:physical_network'] = 'Common/App/Pod3'
        self.context.network.current['provider:segmentation_id'] = 199
        gntb.return_value = None
        self.driver._bind_port_nwa(self.context)

        # else:
        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        self.context.network.current['segments'] = self.network_segments
        gntb.return_value = None
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = None
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        gntb.return_value = None
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = 'network:floatingip'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = 'ironic:isolation'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = 'ironic:isolation'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = 'compute:BM_001'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = 'compute:BM_001'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = 'compute:az_001'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = 'compute:az_001'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(self.context)

        self.context._port['device_owner'] = 'compute:AZ1'
        gntb.return_value = self.rcode
        self.context.network.current.pop(prov_net.PHYSICAL_NETWORK)
        self.driver._bind_port_nwa(self.context)

        # Exception
        self.context._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.side_effect = Exception
        self.driver._bind_port_nwa(self.context)

    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    @patch('neutron.plugins.ml2.db.delete_network_segment')
    def test__l2_delete_segment(self, dns, gds):
        gds.return_value = None
        self.driver._l2_delete_segment(self.context, MagicMock())
        self.assertEqual(0, dns.call_count)

        dns.mock_reset()
        gds.return_value = {'id': 'ID-100'}
        self.driver._l2_delete_segment(self.context, MagicMock())
        self.assertEqual(1, dns.call_count)
