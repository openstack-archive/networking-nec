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
from sqlalchemy.orm import exc as sa_exc

from neutron.tests import base
from oslo_config import cfg
from oslo_serialization import jsonutils

from networking_nec.nwa.l2 import utils as nwa_l2_utils


class TestNwa(base.BaseTestCase):
    def setUp(self):
        super(TestNwa, self).setUp()

        class network_context(object):
            network = MagicMock()
            current = MagicMock()
            _plugin = MagicMock()
            _plugin_context = MagicMock()

        class db_session(object):
            def query(self):
                return
            pass

        self.context = network_context()
        self.context.network.current = {}
        self.context.network.current['tenant_id'] = 'T1'
        self.context.network.current['name'] = 'PublicVLAN_100'
        self.context.network.current['id'] = 'Uuid-PublicVLAN_100'
        self.context._port = {
            'id': 'uuid-port-100',
            'device_owner': 'network:router_interface',
            'device_id': 'uuid-device_id_100',
            'fixed_ips': [
                {'ip_address': '192.168.120.1',
                 'subnet_id': 'Uuid-Subnet-Id-1'}
            ],
            'mac_address': '12:34:56:78:9a:bc'
        }
        self.host_agent = [
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
                }
            },
            {
                "alive": False
            }
        ]

        self.context.host_agents = MagicMock(return_value=self.host_agent)
        self.context.current = {}

        self.network_segments = [
            {
                "physical_network": "Common/KVM/Pod1-1",
                "id": "uuid-1-1",
                "segmentation_id": 100
            },
            {
                "physical_network": "Common/KVM/Pod1-2",
                "id": "uuid-1-2",
                "segmentation_id": 101
            },
            {
                "physical_network": "Common/App/Pod3",
                "id": "uuid-1-3",
                "segmentation_id": 102
            }
        ]

        self.resource_group = [
            {
                "physical_network": "Common/BM/Pod1-1",
                "device_owner": "compute:BM_AZ1",
                "ResourceGroupName": "Common/BM/Pod1"
            },
            {
                "physical_network": "Common/KVM/Pod1-1",
                "device_owner": "compute:AZ1",
                "ResourceGroupName": "Common/KVM/Pod1"
            },
            {
                "physical_network": "Common/KVM/Pod1-2",
                "device_owner": "compute:AZ2",
                "ResourceGroupName": "Common/KVM/Pod2"
            },
            {
                "physical_network": "Common/App/Pod3",
                "device_owner": "compute:DC01_BMT01_ZONE01",
                "ResourceGroupName": "Common/App/Pod3"
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
                "physical_network": "Common/App/Pod4",
                "device_owner": "network:router_gateway",
                "ResourceGroupName": "Common/App/Pod4"
            },
            {
                "physical_network": "Common/App/Pod4",
                "device_owner": "network:router_interface",
                "ResourceGroupName": "Common/App/Pod4"
            }
        ]

        fn_resource_group = self.get_temp_file_path('resource_group.json')
        with open(fn_resource_group, 'w') as f:
            f.write(jsonutils.dumps(self.resource_group))
        cfg.CONF.set_override('resource_group_file', fn_resource_group,
                              group='NWA')

        self.nwa_data = {}
        self.jbody = {
            'resultdata': {
                'ResourceGroupName': 'Common/App/Pod3',
                'VlanID': '2015',
                'TenantID': 'TenantID-2015',
                'TenantFWName': 'TFW2015',
                'LogicalNWName': 'PublicVLAN_2015'
            }
        }
        self.rcode = MagicMock()


class TestGetNetworkInfo(TestNwa):
    def test_get_network_info(self):
        net, nid = nwa_l2_utils.get_network_info(self.context)
        self.assertEqual(net, 'PublicVLAN_100')
        self.assertEqual(nid, 'Uuid-PublicVLAN_100')


class TestGetPhysicalNetwork(TestNwa):
    def test_get_physical_network(self):
        pnet = nwa_l2_utils.get_physical_network('compute:AZ1',
                                                 self.resource_group)
        self.assertEqual(pnet, 'Common/KVM/Pod1-1')

        pnet = nwa_l2_utils.get_physical_network('compute:AZ1',
                                                 self.resource_group,
                                                 'Common/KVM/Pod1')
        self.assertEqual(pnet, 'Common/KVM/Pod1-1')

    def test_get_physical_network_not_found(self):
        pnet = nwa_l2_utils.get_physical_network('network:router_interface1',
                                                 self.resource_group)
        self.assertIsNone(pnet)

        pnet = nwa_l2_utils.get_physical_network('compute:AZ1',
                                                 self.resource_group,
                                                 'Common/KVM/Pod2')
        self.assertIsNone(pnet)


class TestPortcontextToNwaInfo(TestNwa):
    def test_portcontext_to_nwa_info(self):
        self.context.current = self.context._port
        rd = nwa_l2_utils.portcontext_to_nwa_info(self.context,
                                                  self.resource_group)
        self.assertIsInstance(rd, dict)
        p = self.context._port
        self.assertEqual(rd['device']['owner'], p['device_owner'])
        self.assertEqual(rd['device']['id'], p['device_id'])
        self.assertEqual(rd['subnet']['id'], p['fixed_ips'][0]['subnet_id'])
        self.assertEqual(rd['port']['id'], p['id'])
        self.assertEqual(rd['port']['ip'], p['fixed_ips'][0]['ip_address'])
        self.assertEqual(rd['port']['mac'], p['mac_address'])

    def test_portcontext_to_nwa_info_business_vlan(self):
        # session in context
        self.context.session = MagicMock()
        # external network is not found
        self.context.session.query().filter_by().\
            one.side_effect = sa_exc.NoResultFound
        self.context.network.current['name'] = 'BusinessVLAN_200'
        self.context.network.current['id'] = 'Uuid-BusinessVLAN_200'
        self.context.current = self.context._port
        rd = nwa_l2_utils.portcontext_to_nwa_info(self.context,
                                                  self.resource_group)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['network']['vlan_type'], 'BusinessVLAN')

    def test_portcontext_to_nwa_info_original_port(self):
        device_owner = 'do-1'
        device_id = 'di-1'
        id_ = 'id-1'
        subnet_id = 'sid-1'
        ip_address = '192.168.120.1'
        mac = 'mac-1'
        self.context.original = {
            'device_owner': device_owner,
            'device_id': device_id,
            'id': id_,
            'fixed_ips': [
                {'ip_address': ip_address,
                 'subnet_id': subnet_id},
            ],
            'mac_address': mac,
        }
        rd = nwa_l2_utils.portcontext_to_nwa_info(self.context,
                                                  self.resource_group,
                                                  True)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['device']['owner'], device_owner)
        self.assertEqual(rd['device']['id'], device_id)
        self.assertEqual(rd['subnet']['id'], subnet_id)
        self.assertEqual(rd['port']['id'], id_)
        self.assertEqual(rd['port']['ip'], ip_address)
        self.assertEqual(rd['port']['mac'], mac)

    def test_portcontext_to_nwa_info_original_port_no_fixedip(self):
        device_owner = 'do-2'
        device_id = 'di-2'
        id_ = 'id-2'
        subnet_id = ''
        ip_address = ''
        mac = ''
        self.context.original = {
            'device_owner': device_owner,
            'device_id': device_id,
            'id': id_,
            'fixed_ips': [],
            'mac_address': mac,
        }
        rd = nwa_l2_utils.portcontext_to_nwa_info(self.context,
                                                  self.resource_group,
                                                  True)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['device']['owner'], device_owner)
        self.assertEqual(rd['device']['id'], device_id)
        self.assertEqual(rd['subnet']['id'], subnet_id)
        self.assertEqual(rd['port']['id'], id_)
        self.assertEqual(rd['port']['ip'], ip_address)
        self.assertEqual(rd['port']['mac'], mac)


class test__getResourceGroupName(TestNwa):
    def test__get_resource_group_name(self):
        self.context.current['device_owner'] = 'network:dhcp'
        rc = nwa_l2_utils._get_resource_group_name(self.context,
                                                   self.resource_group)
        self.assertEqual(rc, 'Common/App/Pod3')

        self.context.current['device_owner'] = 'network:router_interface'
        rc = nwa_l2_utils._get_resource_group_name(self.context,
                                                   self.resource_group)
        self.assertEqual(rc, 'Common/App/Pod4')

        self.context.current['device_owner'] = 'network:router_gateway'
        rc = nwa_l2_utils._get_resource_group_name(self.context,
                                                   self.resource_group)
        self.assertEqual(rc, 'Common/App/Pod4')

        self.context.current['device_owner'] = 'compute:AZ1'
        rc = nwa_l2_utils._get_resource_group_name(self.context,
                                                   self.resource_group)
        self.assertIsNone(rc)

        self.context.current['device_owner'] = 'network:router_interface'
        self.host_agent[0]['alive'] = False
        self.resource_group = []
        rc = nwa_l2_utils._get_resource_group_name(self.context,
                                                   self.resource_group)
        self.assertIsNone(rc)
