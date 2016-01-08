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

from oslo_serialization import jsonutils
from mock import MagicMock, patch  # noqa
from sqlalchemy.orm import exc

from networking_nec.plugins.necnwa.common import config
from networking_nec.plugins.necnwa.necnwa_utils import (  # noqa
    _get_resource_group_name,
    _release_dynamic_segment,
    _set_general_dev_to_tenant_binding,
    _set_segment_to_tenant_binding,
    baremetal_resource_group_name,
    get_network_info,
    get_physical_network,
    get_tenant_info,
    is_baremetal,
    update_port_status,
    add_router_interface_by_port,
)
from neutron.common import exceptions as n_exc
from neutron.tests import base

import logging
log_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s,%(msecs).03d - %(filename)s:%(lineno)d - %(message)s',
    '%H:%M:%S'
)
log_handler.setFormatter(formatter)
log_handler.propagate = False
LOG = logging.getLogger('networking_nec.plugins.necnwa.necnwa_utils')
LOG.addHandler(log_handler)
LOG.setLevel(logging.INFO)

context = None
network_segments = None
nwa_data = None
jbody = None
nwacli = None
rcode = None
args = None
kargs = None


def setup_global():
    global context, network_segments
    global nwa_data, jbody, nwacli, rcode
    global args, kargs

    class network_context(object):
        network = MagicMock()
        current = MagicMock()
        _plugin = MagicMock()
        _plugin_context = MagicMock()

    class db_session(object):
        def query(self):
            return
        pass

    context = network_context()
    context.network.current = {}
    context.network.current['tenant_id'] = 'T1'
    context.network.current['name'] = 'PublicVLAN_100'
    context.network.current['id'] = 'Uuid-PublicVLAN_100'
    context._port = {
        'id': 'uuid-port-100',
        'device_owner': 'network:router_interface',
        'device_id': 'uuid-device_id_100',
        'fixed_ips': [
            {'ip_address': '192.168.120.1'}
        ],
        'mac_address': '12:34:56:78:9a:bc'
    }
    host_agent = [
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

    context.host_agents = MagicMock(return_value=host_agent)
    context.current = {}

    network_segments = [
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

    ResourceGroup = [
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

    config.CONF.NWA.ResourceGroup = jsonutils.dumps(ResourceGroup)

    nwa_data = {}
    jbody = {
        'resultdata': {
            'ResourceGroupName': 'Common/App/Pod3',
            'VlanID': '2015',
            'TenantID': 'TenantID-2015',
            'TenantFWName': 'TFW2015',
            'LogicalNWName': 'PublicVLAN_2015'
        }
    }
    nwacli = MagicMock()
    rcode = MagicMock()
    rcode.value_json = {}

    args = []
    kargs = {}


class TestNwa(base.BaseTestCase):
    def setUp(self):
        super(TestNwa, self).setUp()
        setup_global()


class TestGetTenantInfo(TestNwa):
    def test_get_tenant_info(self):
        tid, nid = get_tenant_info(context)
        self.assertEqual(tid, 'T1')
        self.assertEqual(nid, 'RegionOneT1')


class TestGetNetworkInfo(TestNwa):
    def test_get_network_info(self):
        net, nid = get_network_info(context)
        self.assertEqual(net, 'PublicVLAN_100')
        self.assertEqual(nid, 'Uuid-PublicVLAN_100')


class TestGetPhysicalNetwork(TestNwa):
    def test_get_physical_network(self):
        pnet = get_physical_network('compute:AZ1')
        self.assertEqual(pnet, 'Common/KVM/Pod1-1')
        pnet = get_physical_network('network:router_interface1')
        self.assertTrue(pnet is None)


class TestUpdatePortStatus(TestNwa):
    def test_update_port_status(self):
        port_id = 'uuid-port-1'
        status = 'ACTIVE'
        port = {'status': None}
        ctx = MagicMock()
        ctx.session.query().filter_by().one = MagicMock(return_value=port)
        update_port_status(ctx, port_id, status)
        self.assertEqual(port['status'], status)

    def test_update_port_status_2(self):
        port_id = 'uuid-port-2'
        status = 'ACTIVE'
        port = {'status': None}
        ctx = context
        ctx.network._plugin_context.session.query().filter_by().one = \
            MagicMock(return_value=port)
        update_port_status(ctx, port_id, status)
        self.assertEqual(port['status'], status)

    def test_update_port_status_3(self):
        port_id = 'uuid-port-3'
        status = 'ACTIVE'
        ctx = context
        ctx.network._plugin_context.session.query().filter_by().one = \
            MagicMock(side_effect=exc.NoResultFound)
        self.assertRaises(
            n_exc.PortNotFound,
            update_port_status, ctx, port_id, status
        )


class TestIsBaremetal(base.BaseTestCase):
    def setUp(self):
        super(TestIsBaremetal, self).setUp()
        setup_global()
        self.ironic_az_prefix = config.CONF.NWA.IronicAZPrefix

    def tearDown(self):
        config.CONF.NWA.IronicAZPrefix = self.ironic_az_prefix
        super(TestIsBaremetal, self).tearDown()

    def check_is_baremetal(self, param):
        config.CONF.NWA.IronicAZPrefix = param['ironic_az_prefix']
        return is_baremetal(param['device_owner'])

    def test_is_baremetal(self):
        test_params = [
            {
                'ironic_az_prefix': '',
                'device_owner': 'compute:',
                'return': False
            },
            {
                'ironic_az_prefix': ' ',
                'device_owner': 'compute:',
                'return': False
            },
            {
                'ironic_az_prefix': 'BM1',
                'device_owner': 'compute:BM1',
                'return': True
            },
            {
                'ironic_az_prefix': 'BM2',
                'device_owner': 'compute:bm2',
                'return': False
            },
            {
                'ironic_az_prefix': 'BM3',
                'device_owner': 'compute:',
                'return': False
            },
            {
                'ironic_az_prefix': 'BM4',
                'device_owner': 'COMPUTE:BM4',
                'return': False
            }
        ]
        for param in test_params:
            yield self.check_is_baremetal, param


class TestBaremetalResourceGroupName(base.BaseTestCase):
    def setUp(self):
        super(TestBaremetalResourceGroupName, self).setUp()
        setup_global()
        self.portmap = config.CONF.NWA.PortMap

    def tearDown(self):
        config.CONF.NWA.PortMap = self.portmap
        super(TestBaremetalResourceGroupName, self).tearDown()

    def check_baremetal_resource_group_name(self, param):
        config.CONF.NWA.PortMap = param['portmap']
        rc = None
        try:
            rc = baremetal_resource_group_name(param['mac_address'])
        except KeyError:
            rc = 'KeyError'
        finally:
            self.assertEqual(rc, param['return'])

    def test_baremetal_resource_group_name(self):
        maca1 = '00:10:18:ca:1f:a1'
        maca2 = '00:10:18:ca:1f:a2'
        maca3 = '00:10:18:ca:1f:a3'
        resgrp1 = "Common/BM/Pod2-BM1"
        resgrp2 = "Common/BM/Pod2-BM2"
        portmaps1 = [
            {'mac_address': maca1, "ResourceGroupName": resgrp1},
            {"mac_address": maca2, "ResourceGroupName": resgrp2},
        ]
        test_params = [
            {'portmap': None, 'mac_address': '', 'return': 'KeyError'},
            {'portmap': [], 'mac_address': '', 'return': 'KeyError'},
            {'portmap': {}, 'mac_address': '', 'return': 'KeyError'},
            {'portmap': {'a': 1}, 'mac_address': '', 'return': 'KeyError'},
            {
                'portmap': jsonutils.dumps(portmaps1),
                'mac_address': maca3,
                'return': 'KeyError',
            },
            {
                'portmap': jsonutils.dumps(portmaps1),
                'mac_address': maca1,
                'return': resgrp1,
            },
            {
                'portmap': jsonutils.dumps(portmaps1),
                'mac_address': maca2,
                'return': resgrp2,
            },
        ]
        for param in test_params:
            yield self.check_baremetal_resource_group_name, param


class test__getResourceGroupName(TestNwa):
    def test__get_resource_group_name(self):
        context.current['device_owner'] = 'network:dhcp'
        rc = _get_resource_group_name(context)
        self.assertEqual(rc, 'Common/App/Pod3')

        context.current['device_owner'] = 'network:router_interface'
        rc = _get_resource_group_name(context)
        self.assertEqual(rc, 'Common/App/Pod4')

        context.current['device_owner'] = 'network:router_gateway'
        rc = _get_resource_group_name(context)
        self.assertEqual(rc, 'Common/App/Pod4')

        context.current['device_owner'] = 'compute:AZ1'
        rc = _get_resource_group_name(context)
        self.assertTrue(rc is None)


class test__releaseDynamicSegment(TestNwa):
    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment(self, gds, dns):
        gds.return_value = network_segments[0]
        rc = _release_dynamic_segment(context, None, None, None, 1)
        self.assertTrue(rc is True)
        self.assertEqual(gds.call_count, 1)
        self.assertEqual(dns.call_count, 1)

    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment_not_found(self, gds, dns):
        gds.return_value = None
        rc = _release_dynamic_segment(context, None, None, None, 1)
        self.assertTrue(rc is False)
        self.assertEqual(gds.call_count, 1)
        self.assertEqual(dns.call_count, 0)

    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment_exception(self, gds, dns):
        gds.side_effect = Exception
        rc = _release_dynamic_segment(context, None, None, None, 1)
        self.assertTrue(rc is False)


class test__setSegmentToTenantBinding(TestNwa):
    @patch('networking_nec.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__set_segment_to_tenant_binding(self, gntb, sntb):
        rcode.value_json = {}
        gntb.return_value = rcode
        sntb.return_value = True
        _set_segment_to_tenant_binding(context, jbody)
        self.assertEqual(gntb.call_count, 1)
        self.assertEqual(sntb.call_count, 1)

    @patch('networking_nec.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__set_segment_to_tenant_binding_set_false(self, gntb, sntb):
        rcode.value_json = {}
        gntb.return_value = rcode
        sntb.return_value = False
        _set_segment_to_tenant_binding(context, jbody)
        self.assertEqual(gntb.call_count, 1)
        self.assertEqual(sntb.call_count, 1)


class test__setGeneralDevToTenantBinding(TestNwa):
    @patch('networking_nec.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__set_general_dev_to_tenant_binding(self, gntb, sntb):
        gntb.return_value = rcode
        sntb.return_value = True
        _set_general_dev_to_tenant_binding(context)
        self.assertEqual(gntb.call_count, 1)
        self.assertEqual(sntb.call_count, 1)

        sntb.return_value = False
        _set_general_dev_to_tenant_binding(context)
        self.assertEqual(gntb.call_count, 2)
        self.assertEqual(sntb.call_count, 2)

        sntb.return_value = None
        sntb.side_effect = Exception
        _set_general_dev_to_tenant_binding(context)
        self.assertEqual(gntb.call_count, 3)
        self.assertEqual(sntb.call_count, 3)

"""
class test__getSegmentationId:
    def test__get_segmentation_id(self):
        rc = _get_segmentation_id(context)
        self.assertEqual(rc, 0)
        context._port['device_owner'] = 'network:router_interface1'
        rc = _get_segmentation_id(context)
        self.assertEqual(rc, 0)
"""


class TestNwaCreateTenantFw(base.BaseTestCase):
    def setUp(self):
        super(TestNwaCreateTenantFw, self).setUp()
        setup_global()
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
        for param in test_params:
            yield self.check_nwa_delete_general_dev_bm, param

    @patch('networking_nec.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_ctnt(self, gpt, gtid):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'

        ret = add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertTrue(ret)

    @patch('networking_nec.plugins.necnwa.db.api.add_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_nbd(self, gpt, gtid, nbd):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        nbd.return_value = False

        ret = add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertTrue(ret)

    @patch('networking_nec.plugins.necnwa.db.api.get_nwa_tenant_binding')
    @patch('networking_nec.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_gbd(self, gpt, gtid, gbd):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        gbd.return_value = True

        ret = add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertTrue(ret)

    @patch('networking_nec.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_ctnw(self, gpt, gtid):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'

        ret = add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertTrue(ret)

    @patch('networking_nec.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_cvln(self, gpt, gtid):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'

        ret = add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertTrue(ret)

    @patch('networking_nec.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_urt(self, gpt, gtid):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'

        ret = add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertTrue(ret)

    @patch('networking_nec.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_urt_false(self, gpt, gtid):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'

        ret = add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertTrue(ret)
