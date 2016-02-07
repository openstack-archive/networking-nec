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
from sqlalchemy.orm import exc
import testscenarios

from neutron.common import exceptions as n_exc
from neutron.tests import base
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec.plugins.necnwa.common import config
from networking_nec.plugins.necnwa.l2 import utils as nwa_l2_utils

# the below code is required to load test scenarios.
# If a test class has 'scenarios' attribute,
# tests are multiplied depending on their 'scenarios' attribute.
# This can be assigned to 'load_tests' in any test module to make this
# automatically work across tests in the module.
# For more details, see testscenarios document.
load_tests = testscenarios.load_tests_apply_scenarios

LOG = logging.getLogger(__name__)


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
                {'ip_address': '192.168.120.1'}
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

        config.CONF.set_override('resource_group',
                                 jsonutils.dumps(self.resource_group),
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
        pnet = nwa_l2_utils.get_physical_network('compute:AZ1')
        self.assertEqual(pnet, 'Common/KVM/Pod1-1')

        pnet = nwa_l2_utils.get_physical_network('compute:AZ1',
                                                 'Common/KVM/Pod1')
        self.assertEqual(pnet, 'Common/KVM/Pod1-1')

    def test_get_physical_network_not_found(self):
        pnet = nwa_l2_utils.get_physical_network('network:router_interface1')
        self.assertIsNone(pnet)

        pnet = nwa_l2_utils.get_physical_network('compute:AZ1',
                                                 'Common/KVM/Pod2')
        self.assertIsNone(pnet)


class TestUpdatePortStatus(TestNwa):
    def test_update_port_status(self):
        port_id = 'uuid-port-1'
        status = 'ACTIVE'
        port = {'status': None}
        ctx = MagicMock()
        ctx.session.query().filter_by().one = MagicMock(return_value=port)
        nwa_l2_utils.update_port_status(ctx, port_id, status)
        self.assertEqual(port['status'], status)

    def test_update_port_status_2(self):
        port_id = 'uuid-port-2'
        status = 'ACTIVE'
        port = {'status': None}
        ctx = self.context
        ctx.network._plugin_context.session.query().filter_by().one = \
            MagicMock(return_value=port)
        nwa_l2_utils.update_port_status(ctx, port_id, status)
        self.assertEqual(port['status'], status)

    def test_update_port_status_3(self):
        port_id = 'uuid-port-3'
        status = 'ACTIVE'
        ctx = self.context
        ctx.network._plugin_context.session.query().filter_by().one = \
            MagicMock(side_effect=exc.NoResultFound)
        self.assertRaises(
            n_exc.PortNotFound,
            nwa_l2_utils.update_port_status, ctx, port_id, status
        )


class TestIsBaremetal(base.BaseTestCase):

    scenarios = [
        ('ironic_az_prefix is empty',
         {
             'ironic_az_prefix': '',
             'device_owner': 'compute:',
             'expected_return_value': False
         }),
        ('ironic_az_prefix is a space',
         {
             'ironic_az_prefix': ' ',
             'device_owner': 'compute:',
             'expected_return_value': False
         }),
        ('ironic_az_prefix and device_owner AZ match',
         {
             'ironic_az_prefix': 'BM1',
             'device_owner': 'compute:BM1',
             'expected_return_value': True
         }),
        ('ironic_az_prefix and device_owner AZ are different cases',
         {
             'ironic_az_prefix': 'BM2',
             'device_owner': 'compute:bm2',
             'expected_return_value': False
         }),
        ('ironic_az_prefix is specified but device_owner AZ is empty',
         {
             'ironic_az_prefix': 'BM3',
             'device_owner': 'compute:',
             'expected_return_value': False
         }),
        ('ironic_az_prefix is specified but device_owner prefix is unexpected',
         {
             'ironic_az_prefix': 'BM4',
             'device_owner': 'COMPUTE:BM4',
             'expected_return_value': False
         })
    ]

    def test_is_baremetal(self):
        config.CONF.set_override('ironic_az_prefix', self.ironic_az_prefix,
                                 group='NWA')
        rc = nwa_l2_utils.is_baremetal(self.device_owner)
        self.assertEqual(self.expected_return_value, rc)


class TestBaremetalResourceGroupName(base.BaseTestCase):

    maca1 = '00:10:18:ca:1f:a1'
    maca2 = '00:10:18:ca:1f:a2'
    maca3 = '00:10:18:ca:1f:a3'
    resgrp1 = "Common/BM/Pod2-BM1"
    resgrp2 = "Common/BM/Pod2-BM2"
    portmaps1 = [
        {'mac_address': maca1, "ResourceGroupName": resgrp1},
        {"mac_address": maca2, "ResourceGroupName": resgrp2},
    ]

    scenarios = [
        ('test 1',
         {
             'portmap': None,
             'mac_address': '',
             'expected_return_value': None
         }),
        ('test 2',
         {
             'portmap': [],
             'mac_address': '',
             'expected_return_value': None
         }),
        ('test 3',
         {
             'portmap': {},
             'mac_address': '',
             'expected_return_value': None
         }),
        ('test 4',
         {
             'portmap': {'a': 1},
             'mac_address': '',
             'expected_return_value': None
         }),
        ('test 5',
         {
             'portmap': jsonutils.dumps(portmaps1),
             'mac_address': maca3,
             'expected_return_value': None,
         }),
        ('test 6',
         {
             'portmap': jsonutils.dumps(portmaps1),
             'mac_address': maca1,
             'expected_return_value': resgrp1,
         }),
        ('test 7',
         {
             'portmap': jsonutils.dumps(portmaps1),
             'mac_address': maca2,
             'expected_return_value': resgrp2,
         }),
    ]

    def test_baremetal_resource_group_name(self):
        config.CONF.set_override('port_map', self.portmap, group='NWA')
        rc = nwa_l2_utils.baremetal_resource_group_name(self.mac_address)
        self.assertEqual(self.expected_return_value, rc)


class test__getResourceGroupName(TestNwa):
    def test__get_resource_group_name(self):
        self.context.current['device_owner'] = 'network:dhcp'
        rc = nwa_l2_utils._get_resource_group_name(self.context)
        self.assertEqual(rc, 'Common/App/Pod3')

        self.context.current['device_owner'] = 'network:router_interface'
        rc = nwa_l2_utils._get_resource_group_name(self.context)
        self.assertEqual(rc, 'Common/App/Pod4')

        self.context.current['device_owner'] = 'network:router_gateway'
        rc = nwa_l2_utils._get_resource_group_name(self.context)
        self.assertEqual(rc, 'Common/App/Pod4')

        self.context.current['device_owner'] = 'compute:AZ1'
        rc = nwa_l2_utils._get_resource_group_name(self.context)
        self.assertIsNone(rc)


class test__releaseDynamicSegment(TestNwa):
    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment(self, gds, dns):
        gds.return_value = self.network_segments[0]
        rc = nwa_l2_utils._release_dynamic_segment(self.context,
                                                   None, None, None, 1)
        self.assertTrue(rc)
        self.assertEqual(gds.call_count, 1)
        self.assertEqual(dns.call_count, 1)

    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment_not_found(self, gds, dns):
        gds.return_value = None
        rc = nwa_l2_utils._release_dynamic_segment(self.context,
                                                   None, None, None, 1)
        self.assertFalse(rc)
        self.assertEqual(gds.call_count, 1)
        self.assertEqual(dns.call_count, 0)

    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment_exception(self, gds, dns):
        gds.side_effect = Exception
        rc = nwa_l2_utils._release_dynamic_segment(self.context,
                                                   None, None, None, 1)
        self.assertFalse(rc)


class test__setSegmentToTenantBinding(TestNwa):
    @patch('networking_nec.plugins.necnwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test__set_segment_to_tenant_binding(self, gntb, sntb):
        self.rcode.value_json = {}
        gntb.return_value = self.rcode
        sntb.return_value = True
        nwa_l2_utils._set_segment_to_tenant_binding(self.context, self.jbody)
        self.assertEqual(gntb.call_count, 1)
        self.assertEqual(sntb.call_count, 1)

    @patch('networking_nec.plugins.necnwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test__set_segment_to_tenant_binding_set_false(self, gntb, sntb):
        self.rcode.value_json = {}
        gntb.return_value = self.rcode
        sntb.return_value = False
        nwa_l2_utils._set_segment_to_tenant_binding(self.context, self.jbody)
        self.assertEqual(gntb.call_count, 1)
        self.assertEqual(sntb.call_count, 1)


class test__setGeneralDevToTenantBinding(TestNwa):
    @patch('networking_nec.plugins.necnwa.l2.db_api.set_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test__set_general_dev_to_tenant_binding(self, gntb, sntb):
        gntb.return_value = self.rcode
        sntb.return_value = True
        nwa_l2_utils._set_general_dev_to_tenant_binding(self.context)
        self.assertEqual(gntb.call_count, 1)
        self.assertEqual(sntb.call_count, 1)

        sntb.return_value = False
        nwa_l2_utils._set_general_dev_to_tenant_binding(self.context)
        self.assertEqual(gntb.call_count, 2)
        self.assertEqual(sntb.call_count, 2)

        sntb.return_value = None
        sntb.side_effect = Exception
        nwa_l2_utils._set_general_dev_to_tenant_binding(self.context)
        self.assertEqual(gntb.call_count, 3)
        self.assertEqual(sntb.call_count, 3)


class TestNwaCreateTenantFw(base.BaseTestCase):
    def setUp(self):
        super(TestNwaCreateTenantFw, self).setUp()
        self.context = MagicMock()
        self.device_id = 'uuid-device_id'
        self.vlan_devaddr = '192.168.123.1'
        self.context._port = {
            'id': 'uuid-1',
            'device_id': self.device_id,
            'device_owner': 'network:router_gateway',
            'fixed_ips': [
                {
                    'ip_address': self.vlan_devaddr
                }
            ]
        }
        self.tenant_id = 'uuid-tenant_id'
        self.network_id = 'uuid-network'
        self.context.network.current = {
            'id': self.network_id,
            'tenant_id': self.tenant_id
        }
        self.nwa_tenant_id = 'RegionOne' + self.tenant_id
        self.dc_resg_name = 'DC1'
        self.vlan_logical_name = 'PublicVLAN_100'
        self.nwa_data = {}
        self.nwa_data['NW_' + self.network_id + '_nwa_network_name'] = \
            self.vlan_logical_name
        self.nwacli = MagicMock()
        self.nwacli.create_tenant_fw = MagicMock(name='create_tenant_fw')

    def test_nwa_create_general_dev_bm(self):
        maca1 = '00:10:18:ca:1f:a1'
        maca2 = '00:10:18:ca:1f:a2'
        maca3 = '00:10:18:ca:1f:a3'
        portmaps1 = [
            {
                'mac_address': maca1,
                "ResourceGroupName": "Common/BM/Pod2-BM1"
            },
            {
                "mac_address": maca2,
                "ResourceGroupName": "Common/BM/Pod1-BM2"
            }
        ]
        test_params = [
            {
                # pmap not found
                'return': True,
                'device_owner': 'compute:',
                'ironic_az_prefix': '',
                'nwa_data': None,
                'mac_address': maca3,
                'portmaps': portmaps1,
                'call_count_create_general_dev': 0
            },
            {
                'return': True,
                'device_owner': 'compute:BM_AZ1',
                'ironic_az_prefix': 'BM_',
                'nwa_data': None,
                'mac_address': maca1,
                'portmaps': portmaps1,
                'call_count_create_general_dev': 0
            },
            {
                'return': None,
                'device_owner': 'compute:BM_AZ1',
                'ironic_az_prefix': 'BM_',
                'nwa_data': {
                    'NW_Uuid-PublicVLAN_100_nwa_network_name': 'PublicVLAN_100'
                },
                'mac_address': maca2,
                'portmaps': portmaps1,
                'call_count_create_general_dev': 1
            }
        ]
        # NOTE(amotoki): check_nwa_create_general_dev_bm not found
        for param in test_params:
            yield self.check_nwa_create_general_dev_bm, param


class TestNwaDeleteGeneralDev(TestNwa):

    def test_nwa_delete_general_dev_bm(self):
        maca1 = '00:10:18:ca:1f:a1'
        maca2 = '00:10:18:ca:1f:a2'
        maca3 = '00:10:18:ca:1f:a3'
        portmaps1 = [
            {
                'mac_address': maca1,
                "ResourceGroupName": "Common/BM/Pod2-BM1"
            },
            {
                "mac_address": maca2,
                "ResourceGroupName": "Common/BM/Pod1-BM2"
            }
        ]
        test_params = [
            {
                # pmap not found
                'return': None,
                'device_owner': 'compute:',
                'ironic_az_prefix': '',
                'nwa_data': {
                    'NW_Uuid-PublicVLAN_100_nwa_network_name': 'PublicVLAN_100'
                },
                'mac_address': maca3,
                'portmaps': portmaps1,
                'call_count_delete_general_dev': 1
            },
            {
                'return': None,
                'device_owner': 'compute:BM_AZ1',
                'ironic_az_prefix': 'BM_',
                'nwa_data': {
                    'NW_Uuid-PublicVLAN_100_nwa_network_name': 'PublicVLAN_100'
                },
                'mac_address': maca1,
                'portmaps': portmaps1,
                'call_count_delete_general_dev': 1
            },
            {
                'return': None,
                'device_owner': 'compute:BM_AZ1',
                'ironic_az_prefix': 'BM_',
                'nwa_data': {
                    'NW_Uuid-PublicVLAN_100_nwa_network_name': 'PublicVLAN_100'
                },
                'mac_address': maca2,
                'portmaps': portmaps1,
                'call_count_delete_general_dev': 1
            },
            {
                'return': None,
                'device_owner': 'compute:BM_AZ1',
                'ironic_az_prefix': 'BM_',
                'nwa_data': {
                    'NW_Uuid-PublicVLAN_100_nwa_network_name': 'PublicVLAN_100'
                },
                'mac_address': maca1,
                'portmaps': [],
                'call_count_delete_general_dev': 0
            }
        ]
        # NOTE(amotoki): check_nwa_delete_general_dev_bm not found
        for param in test_params:
            yield self.check_nwa_delete_general_dev_bm, param
