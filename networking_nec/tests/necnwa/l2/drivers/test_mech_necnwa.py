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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from neutron.common import constants
from neutron.extensions import providernet as prov_net
from neutron.tests import base
from oslo_log import log as logging
from oslo_serialization import jsonutils

import networking_nec
NECNWA_INI = (networking_nec.__path__[0] +
              '/../etc/neutron/plugins/nec/necnwa.ini')
from networking_nec.plugins.necnwa.common import config
from networking_nec.plugins.necnwa.common import constants as nwa_const
from networking_nec.plugins.necnwa.l2.drivers import mech_necnwa as mech

LOG = logging.getLogger(__name__)

CONTEXT = None
NETWORK_SEGMENTS = None
HOST_AGENTS = None
RESOURCE_GROUP_STR = None


def setUpModule():
    global CONTEXT, NETWORK_SEGMENTS, HOST_AGENTS
    global RESOURCE_GROUP_STR

    class network_context(object):
        network = MagicMock()
        current = MagicMock()
        _plugin = MagicMock()
        _plugin_context = MagicMock()
        _binding = MagicMock()

        engine = create_engine(
            "mysql+pymysql://root:hatake4js@localhost/neutron",
            encoding="utf-8")
        Session = sessionmaker(bind=engine, autocommit=True)
        Session = sessionmaker(autocommit=True)
        _plugin_context.session = Session()

        def set_binding(self, segment_id, vif_type, vif_details, status=None):
            # TODO(rkukura) Verify binding allowed, segment in network
            self._binding.segment = segment_id
            self._binding.vif_type = vif_type
            self._binding.vif_details = vif_details
            self._new_port_status = status

    CONTEXT = network_context()
    CONTEXT.network.current = {
        'tenant_id': 'tenant201',
        'name': 'tenant 201',
        'id': '61',
        'network_type': 'vlan',
        'physical_network': 'Common/App/Pod3',
        'segments': []
    }
    CONTEXT._port = {
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
    CONTEXT._binding.segment = ''
    CONTEXT._binding.vif_type = ''

    HOST_AGENTS = [
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
                    "Common/App/Pod3": "br-eth1"
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
    CONTEXT.host_agents = MagicMock(return_value=HOST_AGENTS)

    NETWORK_SEGMENTS = [
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
    CONTEXT.network.network_segments = NETWORK_SEGMENTS
    CONTEXT.original = MagicMock()

    resource_group = [
        {
            "physical_network": "Common/KVM/Pod1-1",
            "device_owner": "compute:AZ1",
            "ResourceGroupName": "Common/KVM/Pod1"
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
    RESOURCE_GROUP_STR = jsonutils.dumps(resource_group)


class TestNECNWAMechanismDriver(base.BaseTestCase):
    def setUp(self):
        super(TestNECNWAMechanismDriver, self).setUp()
        self.driver = mech.NECNWAMechanismDriver()
        config.CONF.set_override('resource_group', RESOURCE_GROUP_STR,
                                 group='NWA')

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
        CONTEXT._port['device_owner'] = 'compute:DC01_KVM01_ZONE01'
        self.driver.create_port_precommit(CONTEXT)

    @patch('networking_nec.plugins.necnwa.l2.db_api.add_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test_create_port_precommit_return_none(self, gntb, antb):
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = None
        self.driver.create_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        gntb.return_value = None
        self.driver.create_port_precommit(CONTEXT)

    @patch('networking_nec.plugins.necnwa.l2.db_api.add_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test_create_port_precommit_owner_router_intf(self, gntb, antb):
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self.rcode
        self.driver.create_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_62': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_62_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_62_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.create_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.side_effect = Exception
        self.driver.create_port_precommit(CONTEXT)

    @patch('networking_nec.plugins.necnwa.l2.db_api.add_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test_create_port_precommit_owner_router_gw(self, gntb, antb):
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        gntb.return_value = self.rcode
        self.driver.create_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_62': constants.DEVICE_OWNER_ROUTER_GW,
            'DEV_uuid-device_id_100_62_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_62_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.create_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        gntb.side_effect = Exception
        self.driver.create_port_precommit(CONTEXT)

    def test_update_port_precommit(self):
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        self.driver.update_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        self.driver.update_port_precommit(CONTEXT)

    @patch('networking_nec.plugins.necnwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test_delete_port_precommit(self, gntb, sntb):
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = None
        self.driver.delete_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self.rcode
        self.driver.delete_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc',
            'DEV_uuid-device_id_100_62_ip_address': '192.168.120.2'}
        )
        self.driver.delete_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_TFW,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc',
            'DEV_uuid-device_id_100_62_ip_address': '192.168.120.2'}
        )
        self.driver.delete_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = 'network:floatingip'
        gntb.return_value = self.rcode
        router_intf = constants.DEVICE_OWNER_ROUTER_INTF
        CONTEXT._port['device_owner'] = router_intf
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
        self.driver.delete_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = router_intf
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
        self.driver.delete_port_precommit(CONTEXT)

        CONTEXT._port['device_owner'] = router_intf
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': router_intf,
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(CONTEXT)

        router_gw = constants.DEVICE_OWNER_ROUTER_GW
        CONTEXT._port['device_owner'] = router_gw
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
        self.driver.delete_port_precommit(CONTEXT)

        # 1 net 1 port(compute:BM)
        CONTEXT._port['device_owner'] = 'compute:BM_1'
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_device_owner': 'compute:BM_1',
            'DEV_uuid-device_id_100_61_TYPE': nwa_const.NWA_DEVICE_GDV,
            'DEV_uuid-device_id_100_61': 'net001',
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver.delete_port_precommit(CONTEXT)

        # 1 net 1 port(compute:AZ1)
        CONTEXT._port['device_owner'] = 'compute:AZ1'
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
        self.driver.delete_port_precommit(CONTEXT)

        # 1 net 2 port(compute:AZ1)
        CONTEXT._port['device_owner'] = 'compute:AZ1'
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
        self.driver.delete_port_precommit(CONTEXT)

        # Exception
        CONTEXT._port['device_owner'] = 'compute:AZ1'
        gntb.side_effect = Exception
        self.driver.delete_port_precommit(CONTEXT)

    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test_try_to_bind_segment_for_agent(self, gntb):
        # in segment
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        CONTEXT._port['fixed_ips'] = []
        gntb.return_value = None
        rc = self.driver.try_to_bind_segment_for_agent(
            CONTEXT, NETWORK_SEGMENTS, HOST_AGENTS[0])
        self.assertEqual(rc, 1)

        # not in segment
        rc = self.driver.try_to_bind_segment_for_agent(
            CONTEXT, NETWORK_SEGMENTS[1], HOST_AGENTS[1])
        self.assertEqual(rc, 0)

    def test_bind_port(self):
        self.driver.bind_port(CONTEXT)

    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test__bind_port_nwa(self, gntb):
        # if prov_net.PHYSICAL_NETWORK in CONTEXT.network.current:
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        CONTEXT.network.current[
            'provider:physical_network'] = 'Common/App/Pod3'
        CONTEXT.network.current['provider:segmentation_id'] = 199
        gntb.return_value = None
        self.driver._bind_port_nwa(CONTEXT)

        # else:
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        CONTEXT.network.current['segments'] = NETWORK_SEGMENTS
        gntb.return_value = None
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = None
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_GW
        gntb.return_value = None
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self._get_nwa_tenant_binding({
            'CreateTenant': True,
            'NWA_tenant_id': 'RegionOnetenant201',
            'DEV_uuid-device_id_100': 'device_id',
            'DEV_uuid-device_id_100_61': constants.DEVICE_OWNER_ROUTER_INTF,
            'DEV_uuid-device_id_100_61_ip_address': '192.168.120.1',
            'DEV_uuid-device_id_100_61_mac_address': '12:34:56:78:9a:bc'}
        )
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = 'network:floatingip'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = 'ironic:isolation'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = 'ironic:isolation'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = 'compute:BM_001'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = 'compute:BM_001'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = 'compute:az_001'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = 'compute:az_001'
        gntb.return_value = self.rcode
        self.driver._bind_port_nwa(CONTEXT)

        CONTEXT._port['device_owner'] = 'compute:AZ1'
        gntb.return_value = self.rcode
        CONTEXT.network.current.pop(prov_net.PHYSICAL_NETWORK)
        self.driver._bind_port_nwa(CONTEXT)

        # Exception
        CONTEXT._port['device_owner'] = constants.DEVICE_OWNER_ROUTER_INTF
        gntb.side_effect = Exception
        self.driver._bind_port_nwa(CONTEXT)
