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

import json
import copy
from nose.tools import assert_equal, eq_, ok_, raises
from mock import MagicMock, patch
from sqlalchemy.orm import exc
from neutron.plugins.necnwa.common import config
from neutron.common import exceptions as n_exc
from neutron.plugins.necnwa.necnwa_utils import (
    _allocate_dynamic_segment,
    _create_general_dev_error,
    _create_general_dev_success,
    _create_tenant_fw_error,
    _create_tenant_fw_success,
    _create_tenant_nw_error,
    _create_tenant_nw_success,
    _create_vlan_error,
    _create_vlan_success,
    _delete_general_dev_error,
    _delete_general_dev_success,
    _delete_nat_error,
    _delete_nat_success,
    _delete_tenant_fw_error,
    _delete_tenant_fw_success,
    _delete_tenant_nw_error,
    _delete_tenant_nw_success,
    _delete_vlan_error,
    _delete_vlan_success,
    _get_resource_group_name,
    _notifier_port_update,
    _release_dynamic_segment,
    _set_general_dev_to_tenant_binding,
    _set_segment_to_tenant_binding,
    _setting_nat_error,
    _setting_nat_success,
    _update_tenant_fw_error,
    _update_tenant_fw_success,
    baremetal_resource_group_name,
    get_network_info,
    get_physical_network,
    get_tenant_info,
    is_baremetal,
    nwa_create_general_dev,
    nwa_create_tenant,
    nwa_create_tenant_fw,
    nwa_create_tenant_nw,
    nwa_create_vlan,
    nwa_delete_general_dev,
    nwa_delete_nat,
    nwa_delete_tenant,
    nwa_delete_tenant_fw,
    nwa_delete_tenant_nw,
    nwa_delete_vlan,
    nwa_setting_fw_policy,
    nwa_setting_fw_policy_mech,
    nwa_setting_nat,
    nwa_update_tenant_fw,
    overwrite_segments_in_context,
    update_port_status,
    _create_tenant,
    _create_tenant_nw,
    nwa_update_router,
    add_router_interface_by_port,
)

import logging
log_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s,%(msecs).03d - %(filename)s:%(lineno)d - %(message)s',
    '%H:%M:%S'
)
log_handler.setFormatter(formatter)
log_handler.propagate = False
LOG = logging.getLogger('neutron.plugins.necnwa.necnwa_utils')
LOG.addHandler(log_handler)
LOG.setLevel(logging.INFO)


def setup():
    global context, network_segments
    global nwa_data, jbody, nwacli, rcode
    global args, kargs

    class network_context:
        network = MagicMock()
        current = MagicMock()
        _plugin = MagicMock()
        _plugin_context = MagicMock()

    class db_session:
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

    config.CONF.NWA.ResourceGroup = json.dumps(ResourceGroup)

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


class TestGetTenantInfo:
    def test_get_tenant_info(self):
        tid, nid = get_tenant_info(context)
        eq_(tid, 'T1')
        eq_(nid, 'RegionOneT1')


class TestGetNetworkInfo:
    def test_get_network_info(self):
        net, nid = get_network_info(context)
        eq_(net, 'PublicVLAN_100')
        eq_(nid, 'Uuid-PublicVLAN_100')


class TestGetPhysicalNetwork:
    def test_get_physical_network(self):
        pnet = get_physical_network('compute:AZ1')
        eq_(pnet, 'Common/KVM/Pod1-1')
        pnet = get_physical_network('network:router_interface1')
        ok_(pnet is None)


class TestUpdatePortStatus:
    def test_update_port_status(self):
        port_id = 'uuid-port-1'
        status = 'ACTIVE'
        port = {'status': None}
        ctx = MagicMock()
        ctx.session.query().filter_by().one = MagicMock(return_value=port)
        update_port_status(ctx, port_id, status)
        eq_(port['status'], status)

    def test_update_port_status_2(self):
        port_id = 'uuid-port-2'
        status = 'ACTIVE'
        port = {'status': None}
        ctx = context
        ctx.network._plugin_context.session.query().filter_by().one = \
            MagicMock(return_value=port)
        update_port_status(ctx, port_id, status)
        eq_(port['status'], status)

    @raises(n_exc.PortNotFound)
    def test_update_port_status_3(self):
        port_id = 'uuid-port-3'
        status = 'ACTIVE'
        ctx = context
        ctx.network._plugin_context.session.query().filter_by().one = \
            MagicMock(side_effect=exc.NoResultFound)
        update_port_status(ctx, port_id, status)


class TestOverwriteSegmentsInContext:
    def test_overwrite_segments_in_context(self):
        context.network.network_segments = network_segments
        dbnetsegs = {
            'physical_network': 'Common/KVM/Pod1-2',
            'id': 'uuid-200',
            'segmentation_id': 200
        }
        overwrite_segments_in_context(context, dbnetsegs)
        eq_(context.network.network_segments[1]['id'], 'uuid-200')
        eq_(context.network.network_segments[1]['segmentation_id'], 200)


class TestIsBaremetal:
    def setUp(self):
        self.ironic_az_prefix = config.CONF.NWA.IronicAZPrefix

    def tearDown(self):
        config.CONF.NWA.IronicAZPrefix = self.ironic_az_prefix

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


class TestBaremetalResourceGroupName:
    def setUp(self):
        self.portmap = config.CONF.NWA.PortMap

    def tearDown(self):
        config.CONF.NWA.PortMap = self.portmap

    def check_baremetal_resource_group_name(self, param):
        config.CONF.NWA.PortMap = param['portmap']
        rc = None
        try:
            rc = baremetal_resource_group_name(param['mac_address'])
        except KeyError:
            rc = 'KeyError'
        finally:
            eq_(rc, param['return'])

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
                'portmap': json.dumps(portmaps1),
                'mac_address': maca3,
                'return': 'KeyError',
            },
            {
                'portmap': json.dumps(portmaps1),
                'mac_address': maca1,
                'return': resgrp1,
            },
            {
                'portmap': json.dumps(portmaps1),
                'mac_address': maca2,
                'return': resgrp2,
            },
        ]
        for param in test_params:
            yield self.check_baremetal_resource_group_name, param


class test__getResourceGroupName:
    def test__get_resource_group_name(self):
        context._port['device_owner'] = 'network:dhcp'
        rc = _get_resource_group_name(context)
        eq_(rc, 'Common/App/Pod3')

        context._port['device_owner'] = 'network:router_interface'
        rc = _get_resource_group_name(context)
        eq_(rc, 'Common/App/Pod4')

        context._port['device_owner'] = 'network:router_gateway'
        rc = _get_resource_group_name(context)
        eq_(rc, 'Common/App/Pod4')

        context._port['device_owner'] = 'compute:AZ1'
        rc = _get_resource_group_name(context)
        ok_(rc is None)


class test__notifierPortUpdate:
    @patch('neutron.plugins.ml2.db.get_network_segments')
    def test__notifier_port_update(self, gns):
        gns.return_value = network_segments
        plugin = MagicMock()
        context._plugin = plugin
        context._plugin_context = MagicMock()
        _notifier_port_update(context)
        eq_(gns.call_count, 1)
        eq_(plugin.notifier.port_update.call_count, 1)


class test__releaseDynamicSegment:
    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment(self, gds, dns):
        gds.return_value = network_segments[0]
        rc = _release_dynamic_segment(context, None, None, None, 1)
        ok_(rc is True)
        eq_(gds.call_count, 1)
        eq_(dns.call_count, 1)

    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment_not_found(self, gds, dns):
        gds.return_value = None
        rc = _release_dynamic_segment(context, None, None, None, 1)
        ok_(rc is False)
        eq_(gds.call_count, 1)
        eq_(dns.call_count, 0)

    @patch('neutron.plugins.ml2.db.delete_network_segment')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__release_dynamic_segment_exception(self, gds, dns):
        gds.side_effect = Exception
        rc = _release_dynamic_segment(context, None, None, None, 1)
        ok_(rc is False)


class test__setSegmentToTenantBinding:
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__set_segment_to_tenant_binding(self, gntb, sntb):
        rcode.value_json = {}
        gntb.return_value = rcode
        sntb.return_value = True
        _set_segment_to_tenant_binding(context, jbody)
        eq_(gntb.call_count, 1)
        eq_(sntb.call_count, 1)

    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__set_segment_to_tenant_binding_set_false(self, gntb, sntb):
        rcode.value_json = {}
        gntb.return_value = rcode
        sntb.return_value = False
        _set_segment_to_tenant_binding(context, jbody)
        eq_(gntb.call_count, 1)
        eq_(sntb.call_count, 1)

class test__setGeneralDevToTenantBinding:
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__set_general_dev_to_tenant_binding(self, gntb, sntb):
        gntb.return_value = rcode
        sntb.return_value = True
        _set_general_dev_to_tenant_binding(context)
        eq_(gntb.call_count, 1)
        eq_(sntb.call_count, 1)

        sntb.return_value = False
        _set_general_dev_to_tenant_binding(context)
        eq_(gntb.call_count, 2)
        eq_(sntb.call_count, 2)

        sntb.return_value = None
        sntb.side_effect = Exception
        _set_general_dev_to_tenant_binding(context)
        eq_(gntb.call_count, 3)
        eq_(sntb.call_count, 3)

"""
class test__getSegmentationId:
    def test__get_segmentation_id(self):
        rc = _get_segmentation_id(context)
        eq_(rc, 0)
        context._port['device_owner'] = 'network:router_interface1'
        rc = _get_segmentation_id(context)
        eq_(rc, 0)
"""

class TestNwaCreateTenant:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test_nwa_create_tenant(self, cli):
        cli.return_value = (200, jbody)
        hst, rj = nwa_create_tenant(context, None)
        eq_(cli.call_count, 1)
        eq_(hst, 200)
        eq_(rj, jbody)

        nwacli.create_tenant.return_value = (300, jbody)
        hst, rj = nwa_create_tenant(context, nwacli)
        eq_(hst, 300)
        eq_(rj, jbody)

        nwacli.create_tenant.return_value = None
        nwacli.create_tenant.side_effect = Exception
        hst, rj = nwa_create_tenant(context, nwacli)
        eq_(hst, 0)
        ok_(rj is None)


class TestNwaDeleteTenant:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_nwa_delete_tenant(self, cli):
        cli.return_value = (200, jbody)
        rb = nwa_delete_tenant(context, nwa_data, None)
        eq_(cli.call_count, 1)
        ok_(rb is True)

        cli.return_value = (500, jbody)
        rb = nwa_delete_tenant(context, nwa_data, None)
        ok_(rb is True)

        nwacli.delete_tenant.return_value = None
        nwacli.delete_tenant.side_effect = Exception
        rb = nwa_delete_tenant(context, nwa_data, nwacli)
        ok_(rb is False)


class TestNwaCreateTenantNw:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    def test_nwa_create_tenant_nw(self, cli):
        if 'CreateTenantNW' in nwa_data:
            del nwa_data['CreateTenantNW']
        cli.return_value = (200, jbody)
        rb = nwa_create_tenant_nw(context, nwa_data, None)
        eq_(cli.call_count, 1)
        ok_(rb is True)

        cli.return_value = None
        cli.side_effect = Exception
        rb = nwa_create_tenant_nw(context, nwa_data, None)
        ok_(rb is True)

        rb = nwa_create_tenant_nw(context, nwa_data, nwacli)
        ok_(rb is True)

        nwa_data['CreateTenantNW'] = True
        rb = nwa_create_tenant_nw(context, nwa_data, nwacli)
        ok_(rb is False)


class TestNwaDeleteTenantNw:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    def test_nwa_delete_tenant_nw(self, cli):
        nwa_data['CreateTenantNW'] = True
        rb = nwa_delete_tenant_nw(context, nwa_data, None)
        eq_(cli.call_count, 1)
        ok_(rb is True)

        cli.return_value = None
        cli.side_effect = Exception
        rb = nwa_delete_tenant_nw(context, nwa_data, None)
        ok_(rb is True)

        rb = nwa_delete_tenant_nw(context, nwa_data, nwacli)
        ok_(rb is True)

        del nwa_data['CreateTenantNW']
        rb = nwa_delete_tenant_nw(context, nwa_data, nwacli)
        ok_(rb is False)


class TestNwaDeleteVlan:
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    def test_nwa_delete_vlan(self, cli, gntb):
        rcode.value_json = {
            'NWA_tenant_id': 'NWA-T101',
            'NW_Uuid-PublicVLAN_100_nwa_network_name': 'uuid-network-101'
        }
        gntb.return_value = rcode
        context._port['device_owner'] = 'network:router_gateway'
        rb = nwa_delete_vlan(context, nwa_data, None)
        eq_(cli.call_count, 1)
        ok_(rb is True)

        context._port['device_owner'] = 'network:router_interface'
        rb = nwa_delete_vlan(context, nwa_data, None)
        eq_(cli.call_count, 2)
        ok_(rb is True)

        nwacli.delete_vlan.return_value = None
        nwacli.delete_vlan.side_effect = Exception
        rb = nwa_delete_vlan(context, nwa_data, nwacli)
        ok_(rb is True)

        rcode.value_json['DEV_Uuid-PublicVLAN_100'] = 'uuid-dev-102'
        rb = nwa_delete_vlan(context, nwa_data, None)
        ok_(rb is False)


class TestNwaCreateTenantFw:
    def setUp(self):
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

    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    def test_nwa_create_tenant_fw(self, ups, gres):
        gres.return_value = self.dc_resg_name
        rc = nwa_create_tenant_fw(
            self.context, self.nwa_data, self.nwacli
        )
        ok_(rc is True)
        eq_(gres.call_count, 1)
        eq_(ups.call_count, 1)
        eq_(self.nwacli.create_tenant_fw.call_count, 1)
        args = self.nwacli.create_tenant_fw.call_args_list[0][0]
        eq_(args[2], self.context)
        eq_(args[3], self.nwa_tenant_id)
        eq_(args[4], self.dc_resg_name)
        eq_(args[5], self.vlan_devaddr)
        eq_(args[6], self.vlan_logical_name)

    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    def test_nwa_create_tenant_fw_dcres_is_none(self, ups, gres):
        gres.return_value = None
        ups.return_value = None
        rc = nwa_create_tenant_fw(
            self.context, self.nwa_data, self.nwacli
        )
        # ok_(rc) XXX: is False
        ok_(rc is None)

    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    def test_nwa_create_tenant_fw_business_vlan(self, ups, gres):
        self.context._port['device_owner'] = 'network:router_interface'
        gres.return_value = self.dc_resg_name
        ups.return_value = None
        rc = nwa_create_tenant_fw(
            self.context, self.nwa_data, self.nwacli
        )
        ok_(rc is True)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient')
    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    def test_nwa_create_tenant_fw_new_nwaclient(self, ups, gres, cli):
        gres.return_value = self.dc_resg_name
        ups.return_value = None
        cli.create_tenant_fw = MagicMock(name='create_tenant_fw')
        rc = nwa_create_tenant_fw(self.context, self.nwa_data)
        ok_(rc is True)

    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    def test_nwa_create_tenant_fw_other_owner(self, ups, gres):
        self.context._port['device_owner'] = 'network:router_interface1'
        gres.return_value = self.dc_resg_name
        ups.return_value = None
        rc = nwa_create_tenant_fw(
            self.context, self.nwa_data, self.nwacli
        )
        ok_(rc is False)

    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    def test_nwa_create_tenant_fw_error(self, ups, gres):
        gres.return_value = self.dc_resg_name
        ups.side_effect = Exception('Failed')
        rc = nwa_create_tenant_fw(
            self.context, self.nwa_data, self.nwacli
        )
        ok_(rc is True)


class TestNwaUpdateTenantFw:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.update_tenant_fw')
    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    def test_nwa_update_tenant_fw(self, gres, cli):
        context._port['device_owner'] = 'network:router_gateway'
        gres.return_value = None
        rb = nwa_update_tenant_fw(context, nwa_data, 'connect', nwacli)
        eq_(gres.call_count, 1)
        ok_(rb is False)

        gres.return_value = 'Common/App/Pod3'
        nd = copy.deepcopy(nwa_data)
        netkey = 'NW_Uuid-PublicVLAN_100'
        devkey = 'DEV_uuid-device_id_100'
        nd[netkey + '_nwa_network_name'] = '1'
        nd[devkey + '_TenantFWName'] = 'TFW8'
        rb = nwa_update_tenant_fw(context, nd, 'connect', None)
        ok_(rb is True)

        nd = copy.deepcopy(nwa_data)
        netkey = 'NW_Uuid-PublicVLAN_100'
        devkey = 'DEV_uuid-device_id_100'
        nd[netkey + '_nwa_network_name'] = '1'
        nd[devkey + '_TenantFWName'] = None
        rb = nwa_update_tenant_fw(context, nd, 'connect', None)
        #ok_(rb is False)
        ok_(rb is True)

        nd[devkey + '_TenantFWName'] = 'TFW8'
        nd[devkey + '_' + netkey + '_TenantFWName'] = 'TFW8'
        rb = nwa_update_tenant_fw(context, nd, 'connect', None)
        ok_(rb is True)

        context._port['device_owner'] = 'network:dhcp'
        rb = nwa_update_tenant_fw(context, nd, 'connect', None)
        ok_(rb is False)

        context._port['device_owner'] = 'network:router_interface'
        rb = nwa_update_tenant_fw(context, nd, 'connect', None)
        ok_(rb is True)
        eq_(cli.call_count, 4)


class TestNwaDeleteTenantFw:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    def test_nwa_delete_tenant_fw(self, cli):
        nd = copy.deepcopy(nwa_data)
        devkey = 'DEV_uuid-device_id_100'
        nd[devkey + '_TenantFWName'] = 'TFW8'
        nd[devkey + '_' + 'Uuid-PublicVLAN_100' + '_TenantFWName'] = 'TFW8'
        rb = nwa_delete_tenant_fw(context, nd, nwacli)
        ok_(rb is True)

        rb = nwa_delete_tenant_fw(context, nd, None, tfw_name='TFW8')
        ok_(rb is True)
        eq_(cli.call_count, 1)

        rb = nwa_delete_tenant_fw(context, nd, None)
        ok_(rb is True)
        eq_(cli.call_count, 2)

        cli.side_effect = Exception
        rb = nwa_delete_tenant_fw(context, nd, None)
        ok_(rb is True)


class TestNwaCreateGeneralDev:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    def test_nwa_create_general_dev(self, gres, cli):
        nwa_data = {
            'Tenant': 'T1',
            'CreateTenantNW': True,
            'NW_': 'dummy'
        }

        gres.return_value = None
        nwa_create_general_dev(context, nwa_data, nwacli)

        gres.return_value = 'Common/KVM/Pod3'
        context._port['device_owner'] = 'network:dhcp'
        nid = 'Uuid-PublicVLAN_100'
        vid = nid + '_Common/App/Pod3'
        nwkey = 'NW_' + nid
        nwa_data[nwkey] = 1
        nwa_data[nwkey + '_network_id'] = 2
        nwa_data[nwkey + '_subnet_id'] = 3
        nwa_data[nwkey + '_subnet'] = 4
        nwa_data[nwkey + '_nwa_network_name'] = 5
        gres.return_value = True
        rb = nwa_create_general_dev(context, nwa_data, None)
        ok_(rb is None)                   # XXX is True

        cli.side_effect = Exception
        rb = nwa_create_general_dev(context, nwa_data, None)
        ok_(rb is True)

        nwa_data['VLAN_' + vid] = 'uuid-VLAN-200'
        nwa_data['VLAN_' + vid + '_segmentation_id'] = 200
        nwa_data['VLAN_' + vid + '_GD'] = 201
        rb = nwa_create_general_dev(context, nwa_data, None)
        ok_(rb is False)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    def check_nwa_create_general_dev_bm(self, param, cli):
        context._port['device_owner'] = param['device_owner']
        context._port['mac_address'] = param['mac_address']
        config.CONF.NWA.IronicAZPrefix = param['ironic_az_prefix']
        config.CONF.NWA.PortMap = json.dumps(param['portmaps'])
        rb = nwa_create_general_dev(context, param['nwa_data'], None)
        if param['return'] is not None:
            eq_(rb, param['return'])
        eq_(cli.call_count, param['call_count_create_general_dev'])

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


class TestNwaDeleteGeneralDev:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.necnwa_utils._get_resource_group_name')
    def test_nwa_delete_general_dev(self, gres, cli):
        nwa_data = {
            'Tenant': 'T1',
            'CreateTenantNW': True,
            'NW_Uuid-PublicVLAN_100_nwa_network_name': '5'
        }
        rb = nwa_delete_general_dev(context, nwa_data, nwacli)
        ok_(rb is None)                   # XXX

        rb = nwa_delete_general_dev(context, nwa_data, None)
        ok_(rb is None)                   # XXX is True

        cli.side_effect = Exception
        rb = nwa_delete_general_dev(context, nwa_data, None)
        ok_(rb is True)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    def check_nwa_delete_general_dev_bm(self, param, cli):
        context._port['device_owner'] = param['device_owner']
        context._port['mac_address'] = param['mac_address']
        config.CONF.NWA.IronicAZPrefix = param['ironic_az_prefix']
        config.CONF.NWA.PortMap = json.dumps(param['portmaps'])
        rb = nwa_delete_general_dev(context, param['nwa_data'], None)
        if param['return'] is not None:
            eq_(rb, param['return'])
        eq_(cli.call_count, param['call_count_delete_general_dev'])

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


class TestNwaCreateVlan:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    def test_nwa_create_vlan(self, cli):
        rb = nwa_create_vlan(context, None, None)
        ok_(rb is True)

        nwa_data = {
            'Tenant': 'T1',
            'CreateTenantNW': True,
            'NW_Uuid-PublicVLAN_100_nwa_network_name': '5'
        }
        context._port['device_owner'] = 'network:router_gateway'
        rb = nwa_create_vlan(context, nwa_data, nwacli)
        ok_(rb is True)

        context._port['device_owner'] = 'network:router_interface'
        context._port['fixed_ips'] = [
            {
                'subnet_id': 'uuid-subnet_201',
                'ip_address': '192.168.120.201'
            }
        ]
        context._plugin.get_subnet.return_value = {
            'cidr': '192.168.120.0/24'
        }
        rb = nwa_create_vlan(context, nwa_data, None)
        ok_(rb is True)

        nwa_data['NW_Uuid-PublicVLAN_100'] = '2'
        rb = nwa_create_vlan(context, nwa_data, None)
        ok_(rb is False)

        cli.side_effect = Exception
        rb = nwa_create_vlan(context, nwa_data, None)
        ok_(rb is False)


class test__createTenantNwSuccess:
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__create_tenant_nw_success(self, gntb, sntb):
        rcode.value_json = {}
        gntb.return_value = rcode
        _create_tenant_nw_success(context, 200, jbody, *args, **kargs)

        gntb.side_effect = Exception
        _create_tenant_nw_success(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__createTenantNwError:
    @patch('neutron.plugins.necnwa.necnwa_utils.get_tenant_info')
    def test__create_tenant_nw_error(self, gti):
        gti.return_value = 'a', 'b'
        _create_tenant_nw_error(context, 200, jbody, *args, **kargs)
        gti.side_effect = Exception
        _create_tenant_nw_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__deleteTenantNwSuccess:
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_delete_tenant')
    @patch('neutron.plugins.necnwa.db.api.del_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__delete_tenant_nw_success(self, gntb, sntb, dntb, ndt):
        gntb.return_value = None
        _delete_tenant_nw_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 1)

        rcode.value_json = {'CreateTenantNW': True}
        gntb.return_value = rcode
        sntb.return_value = False
        ndt.return_value = True
        _delete_tenant_nw_success(context, 200, jbody, *args, **kargs)
        eq_(sntb.call_count, 1)
        eq_(dntb.call_count, 1)

        gntb.side_effect = Exception
        _delete_tenant_nw_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 3)


class test__deleteTenantNwError:
    @patch('neutron.plugins.necnwa.necnwa_utils.get_tenant_info')
    def test__delete_tenant_nw_error(self, gti):
        gti.return_value = 'a', 'b'
        _delete_tenant_nw_error(context, 200, jbody, *args, **kargs)
        gti.side_effect = Exception
        _delete_tenant_nw_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__createVlanSuccess:
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_create_general_dev')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__create_vlan_success(self, gntb, sntb, ncgd):
        context._port['fixed_ips'] = [
            {
                'subnet_id': 'uuid-subnet_201',
                'ip_address': '192.168.120.201'
            }
        ]
        context._plugin.get_subnet.side_effect = Exception
        _create_vlan_success(context, 200, jbody, *args, **kargs)
        context._plugin.get_subnet.side_effect = None

        context._plugin.get_subnet.return_value = {
            'cidr': '192.168.120.0/24'
        }
        context._port['device_owner'] = 'network:dhcp'
        nwa_data = {
            'Tenant': 'T1',
            'CreateTenantNW': True,
        }
        rcode.value_json = nwa_data
        gntb.return_value = rcode
        sntb.return_value = False
        _create_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(sntb.call_count, 1)

        context._port['device_owner'] = 'network:router_interface'
        _create_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(sntb.call_count, 2)

        rcode.value_json['DEV_uuid-device_id_100'] = 1
        _create_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(sntb.call_count, 3)

        context._port['device_owner'] = 'network:dhcp'
        ncgd.return_value = True
        _create_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(sntb.call_count, 4)


class test__createVlanError:
    @patch('neutron.plugins.necnwa.necnwa_utils.get_tenant_info')
    def test__create_vlan_error(self, gti):
        gti.return_value = 'a', 'b'
        _create_vlan_error(context, 200, jbody, *args, **kargs)

        gti.side_effect = Exception
        _create_vlan_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__deleteVlanSuccess:
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.send_queue_is_not_empty')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__delete_vlan_success(self, gntb, sntb, sqine, ndtn):
        gntb.return_value = None
        _delete_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 1)

        context._port['device_owner'] = 'network:dhcp'
        nid = 'Uuid-PublicVLAN_100'
        vid = nid + '_Common/App/Pod3'
        nwkey = 'NW_' + nid
        nwa_data = {
            'Tenant': 'T1',
            'CreateTenantNW': True,
            'NW_': 'dummy'
        }
        nwa_data[nwkey] = 1
        nwa_data[nwkey + '_network_id'] = 2
        nwa_data[nwkey + '_subnet_id'] = 3
        nwa_data[nwkey + '_subnet'] = 4
        nwa_data[nwkey + '_nwa_network_name'] = 5
        nwa_data['VLAN_' + vid] = 'uuid-VLAN-200'
        nwa_data['VLAN_' + vid + '_segmentation_id'] = 200
        nwa_data['VLAN_' + vid + '_VlanID'] = 201

        rcode.value_json = copy.deepcopy(nwa_data)
        gntb.return_value = rcode
        _delete_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(sntb.call_count, 1)

        del nwa_data['NW_']
        rcode.value_json = copy.deepcopy(nwa_data)
        sqine.return_value = True
        _delete_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(sntb.call_count, 2)

        rcode.value_json = copy.deepcopy(nwa_data)
        sqine.return_value = False
        ndtn.return_value = True
        _delete_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(sntb.call_count, 3)

        gntb.side_effect = Exception
        _delete_vlan_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 5)


class test__deleteVlanError:
    def test__delete_vlan_error(self):
        _delete_vlan_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__allocateDynamicSegment:
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    def test__allocate_dynamic_segment(self, gds):
        gds.return_value = None
        _allocate_dynamic_segment(context, None, None, None, None)

        gds.return_value = True
        _allocate_dynamic_segment(context, None, None, None, None)
        eq_(gds.call_count, 2)

        gds.side_effect = Exception
        _allocate_dynamic_segment(context, None, None, None, None)
        eq_(gds.call_count, 3)


class test__createTenantFwSuccess:
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    @patch('neutron.plugins.ml2.db.add_network_segment')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_delete_tenant_fw')
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_delete_vlan')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__create_tenant_fw_success(self, gntb, sntb, ndv, ndtf, ups, ans, gds):
        context._port['device_owner'] = 'none'
        _create_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(gds.call_count, 0)

        context._port['device_owner'] = 'network:router_interface'
        rcode.value_json = {}
        gds.return_value = None
        _create_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ans.call_count, 1)

        gds.return_value = True
        _create_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ans.call_count, 1)

        context.network._plugin_context.session.query.side_effect = \
            exc.NoResultFound
        _create_tenant_fw_success(context, 200, jbody, *args, **kargs)
        context.network._plugin_context.session.query.side_effect = None
        eq_(gntb.call_count, 3)

        rcode.value_json = {}
        gntb.return_value = rcode
        _create_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ups.call_count, 1)


class test__createTenantFwError:
    def test__create_tenant_fw_error(self):
        _create_tenant_fw_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__updateTenantFwSuccess:
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    @patch('neutron.plugins.ml2.db.add_network_segment')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_delete_tenant_fw')
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_delete_vlan')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__update_tenant_fw_success(self, gntb, sntb, ndv, ndtf, ups, ans, gds):
        context._port['device_owner'] = 'network:router_interface'
        phyid = 'Common/App/Pod4'
        devid = 'uuid-device_id_100'
        devkey = 'DEV_' + devid
        nid = 'Uuid-PublicVLAN_100'
        nwa_data = {}
        nwa_data[devkey + '_TenantFWName'] = 0
        nwa_data[devkey + '_' + nid] = 1
        nwa_data[devkey + '_' + nid + '_TYPE'] = 2
        nwa_data[devkey + '_' + nid + '_ip_address'] = 3
        nwa_data[devkey + '_' + nid + '_mac_address'] = 4
        nwa_data['VLAN_' + nid + '_' + phyid + '_FW_TFW' + devid] = 5
        nwa_data[devkey + '_' + nid + '_TenantFWName'] = 6

        kargs['connect'] = 'disconnect'
        rcode.value_json = copy.deepcopy(nwa_data)
        gntb.return_value = rcode
        _update_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ndtf.call_count, 0)

        rcode.value_json = copy.deepcopy(nwa_data)
        rcode.value_json[devkey + '_' + '_ip_address'] = 6
        _update_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ndv.call_count, 2)

        rcode.value_json = copy.deepcopy(nwa_data)
        rcode.value_json[devkey + '_' + '_ip_address'] = 7
        rcode.value_json['DEV_' + nid] = 8
        _update_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ndv.call_count, 2)

        kargs['connect'] = 'connect'
        gds.return_value = None
        rcode.value_json = copy.deepcopy(nwa_data)
        _update_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ans.call_count, 1)
        eq_(ups.call_count, 1)

        gds.return_value = network_segments[0]
        rcode.value_json = copy.deepcopy(nwa_data)
        _update_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ans.call_count, 1)
        eq_(ups.call_count, 2)

        kargs['connect'] = 'disconnect'
        nwa_data[devkey] = 10
        nwa_data[devkey + '_physical_network'] = 10
        nwa_data[devkey + '_device_owner'] = 10
        nwa_data[devkey + '_TenantFWName'] = 10
        _update_tenant_fw_success(context, 200, jbody, *args, **kargs)

        kargs['connect'] = 'connect'
        context.network._plugin_context.session.query.side_effect = \
            exc.NoResultFound
        _update_tenant_fw_success(context, 200, jbody, *args, **kargs)
        context.network._plugin_context.session.query.side_effect = None
        eq_(ans.call_count, 1)
        eq_(ups.call_count, 3)

        gntb.side_effect = Exception
        rcode.value_json = copy.deepcopy(nwa_data)
        _update_tenant_fw_success(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__updateTenantFwError:
    @patch('neutron.plugins.necnwa.necnwa_utils.get_tenant_info')
    def test__update_tenant_fw_error(self, gti):
        gti.return_value = 'a', 'b'
        _update_tenant_fw_error(context, 200, jbody, *args, **kargs)
        gti.side_effect = Exception
        _update_tenant_fw_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__deleteTenantFwSuccess:
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__delete_tenant_fw_success(self, gntb, sntb, cli, ndv):
        gntb.return_value = None
        _delete_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 1)

        phyid = 'Common/App/Pod3'
        devid = 'uuid-device_id_100'
        devkey = 'DEV_' + devid
        nid = 'Uuid-PublicVLAN_100'
        rcode.value_json = {}
        rcode.value_json[devkey] = 1
        rcode.value_json[devkey + '_physical_network'] = 2
        rcode.value_json[devkey + '_device_owner'] = 3
        rcode.value_json[devkey + '_TenantFWName'] = 4
        rcode.value_json[devkey + '_' + nid] = 5
        rcode.value_json[devkey + '_' + nid + '_TYPE'] = 6
        rcode.value_json[devkey + '_' + nid + '_ip_address'] = 7
        rcode.value_json[devkey + '_' + nid + '_mac_address'] = 8
        rcode.value_json[devkey + '_' + nid + '_TenantFWName'] = 9
        rcode.value_json['VLAN_' + nid + '_' + phyid + '_FW_TFW' + devid] = 10
        gntb.return_value = rcode
        _delete_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(ndv.call_count, 1)

        gntb.side_effect = Exception
        _delete_tenant_fw_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 3)


class test__deleteTenantFwError:
    @patch('neutron.plugins.necnwa.necnwa_utils.get_tenant_info')
    def test__delete_tenant_fw_error(self, gti):
        gti.return_value = 'a', 'b'
        _delete_tenant_fw_error(context, 200, jbody, *args, **kargs)
        gti.side_effect = Exception
        _delete_tenant_fw_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__createGeneralDevSuccess:
    @patch('neutron.plugins.necnwa.db.api.ensure_port_binding')
    @patch('neutron.plugins.ml2.db.get_dynamic_segment')
    @patch('neutron.plugins.necnwa.necnwa_utils.update_port_status')
    def test__create_general_dev_success(self, ups, gds, epb):
        context.current.get.return_value = 'normal-1'
        _create_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(ups.call_count, 1)

        context.current.get.return_value = 'normal'
        context._port['device_owner'] = 'network:dhcp'
        gds.return_value = None
        _create_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(ups.call_count, 2)

        gds.return_value = network_segments
        context.network._plugin_context.session.query().filter_by().one = \
            MagicMock()
        _create_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(context._plugin.notifier.port_update.call_count, 1)

        epb.side_effect = Exception
        _create_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(context._plugin.notifier.port_update.call_count, 2)
        epb.side_effect = None

        context.network._plugin_context.session.query().filter_by().one = \
            MagicMock(side_effect=exc.NoResultFound)
        _create_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(context._plugin.notifier.port_update.call_count, 3)

        context.network._plugin_context.session.query().filter_by().one = \
            MagicMock(side_effect=Exception)
        _create_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(context._plugin.notifier.port_update.call_count, 4)

        ups.side_effect = Exception
        _create_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(ups.call_count, 7)


class test__createGeneralDevError:
    def test__create_general_dev_error(self):
        _create_general_dev_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__deleteGeneralDevSuccess:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__delete_general_dev_success(self, gntb, sntb, cli):
        _delete_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 2)

        vid = 'Uuid-PublicVLAN_100_Common/App/Pod3'
        rcode.value_json = {}
        rcode.value_json['VLAN_' + vid + '_GD'] = 'connected'
        gntb.return_value = rcode
        _delete_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 4)

        gntb.return_value = None
        _delete_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 5)

        gntb.side_effect = Exception
        _delete_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 6)

    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__delete_general_dev_success_dev(self, gntb, sntb):
        nid = 'Uuid-PublicVLAN_100'
        rcode.value_json = {}
        rcode.value_json['DEV_' + nid] = nid
        gntb.return_value = rcode
        sntb.return_value = True
        _delete_general_dev_success(context, 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 1)
        eq_(sntb.call_count, 1)

class test__deleteGeneralDevError:
    @patch('neutron.plugins.necnwa.necnwa_utils.get_tenant_info')
    def test__delete_general_dev_error(self, gti):
        gti.return_value = ('T1', 'NWA-T1')
        _delete_general_dev_error(context, 200, jbody, *args, **kargs)
        gti.side_effect = Exception
        _delete_general_dev_error(context, 200, jbody, *args, **kargs)
        eq_(gti.call_count, 2)


class TestNwaSettingNat:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test_nwa_setting_nat(self, gntb, sntb, cli):
        cli.setting_nat = MagicMock()
        fid = 'uuid-103'
        nid = 'uuid-floating_network_id-103'
        did = 'uuid-device_id-103'
        rcode.value_json = {}
        rcode.value_json['NAT_' + fid] = 'T-103'
        rcode.value_json['NW_' + nid + '_nwa_network_name'] = 'PublicVLAN_103'
        rcode.value_json['DEV_' + did + '_TenantFWName'] = 'TFW8'
        gntb.return_value = rcode
        floating = {
            'floating_port_id': 'uuid-port-id-103',
            'tenant_id': 'tenantid-103',
            'device_id': did,
            'floating_network_id': nid,
            'floating_ip_address': '10.0.120.103',
            'floating_port_id': 'uuid-port-id-103',
            'fixed_ip_address': '192.168.120.103',
            'id': fid
        }
        ctx = MagicMock()
        rb = nwa_setting_nat(ctx, floating, None)
        ok_(rb is False)

        floating['id'] = 'uuid-103-1'
        rb = nwa_setting_nat(ctx, floating, None)
        # ok_(rb) XXX: is True
        eq_(cli.call_count, 1)

        nwacli.setting_nat.side_effect = Exception
        rb = nwa_setting_nat(ctx, floating, nwacli)
        ok_(rb is True)


class TestNwaDeleteNat:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient')
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test_nwa_delete_nat(self, gntb, sntb, cli):
        cli.delete_nat = MagicMock()
        fid = 'uuid-104'
        nid = 'uuid-floating_network_id-104'
        did = 'uuid-device_id-104'
        rcode.value_json = {}
        rcode.value_json['NAT_' + fid] = 'T-104'
        rcode.value_json['NW_' + nid + '_nwa_network_name'] = 'PublicVLAN_104'
        rcode.value_json['DEV_' + did + '_TenantFWName'] = 'TFW8'
        gntb.return_value = rcode
        floating = {
            'floating_port_id': 'uuid-port-id-104',
            'tenant_id': 'tenantid-104',
            'device_id': did,
            'floating_network_id': nid,
            'floating_ip_address': '10.0.120.104',
            'floating_port_id': 'uuid-port-id-104',
            'fixed_ip_address': '192.168.120.104',
            'id': fid
        }
        ctx = MagicMock()
        rb = nwa_delete_nat(ctx, floating, None)
        # ok_(rb)  XXX: is True
        eq_(cli.call_count, 1)

        floating['id'] = 'uuid-104-1'
        rb = nwa_delete_nat(ctx, floating, None)
        ok_(rb is False)

        floating['id'] = fid
        nwacli.delete_nat.side_effect = Exception
        rb = nwa_delete_nat(ctx, floating, nwacli)
        ok_(rb is True)


class TestNwaSettingFwPolicyMech:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.setting_fw_policy')
    def test_nwa_setting_fw_policy_mech(self, sfp):
        fw_name = 'TFW8'
        devparams = {}
        rv = {'status': 'SUCCEED'}
        sfp.return_value = rv
        rc = nwa_setting_fw_policy_mech(context, fw_name, devparams, None)
        eq_(rc, rv)
        eq_(sfp.call_count, 1)

    def test_nwa_setting_fw_policy_mech_raise(self):
        fw_name = 'TFW8'
        devparams = {}
        nwacli.reset_mock()
        nwacli.setting_fw_policy.side_effect = Exception
        rc = nwa_setting_fw_policy_mech(context, fw_name, devparams, nwacli)
        eq_(rc, None)
        eq_(nwacli.setting_fw_policy.call_count, 1)


class TestNwaSettingFwPolicy:
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.setting_fw_policy')
    def test_nwa_setting_fw_policy(self, sfp):
        fw_name = 'TFW8'
        devparams = {'a': 1}
        context = MagicMock()
        tid_value = 'TenantID-2015'
        context.to_dict.return_value = {'tenant_id': tid_value}

        rv = {'status': 'SUCCEED'}
        sfp.return_value = rv
        rc = nwa_setting_fw_policy(context, fw_name, devparams, None)
        eq_(rc, rv)
        eq_(sfp.call_count, 1)
        tid = str(config.CONF.NWA.RegionName) + tid_value
        sfp.assert_called_once_with(tid, fw_name, devparams)

    def test_nwa_setting_fw_policy_raise(self):
        fw_name = 'TFW8'
        devparams = {}
        context = MagicMock()
        context.to_dict.return_value = {'tenant_id': 'TenantID-2015'}
        nwacli.reset_mock()
        nwacli.setting_fw_policy.side_effect = Exception
        rc = nwa_setting_fw_policy(context, fw_name, devparams, nwacli)
        eq_(rc, None)
        eq_(nwacli.setting_fw_policy.call_count, 1)


class test__settingNatSuccess:
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__setting_nat_success(self, gntb, sntb):
        if kargs.get('data', None):
            del kargs['data']
        _setting_nat_success(context, 200, jbody, *args, **kargs)

        kargs['data'] = {
            'floating_port_id': 'uuid-port-id-105',
            'tenant_id': 'tenantid-105',
            'device_id': 'uuid-device_id-105',
            'floating_network_id': 'uuid-floating_network_id-105',
            'floating_ip_address': '10.0.120.105',
            'floating_port_id': 'uuid-port-id-105',
            'fixed_ip_address': '192.168.120.105',
            'id': 'uuid-105'
        }
        rcode.value_json = {}
        gntb.return_value = rcode
        _setting_nat_success(MagicMock(), 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 2)
        eq_(sntb.call_count, 1)


class test__settingNatError:
    def test__setting_nat_error(self):
        if kargs.get('data', None):
            del kargs['data']
        _setting_nat_error(context, 200, jbody, *args, **kargs)
        kargs['data'] = {
            'floating_port_id': 'uuid-port-id-106'
        }
        _setting_nat_error(context, 200, jbody, *args, **kargs)
        ok_(True)


class test__deleteNatSuccess:
    @patch('neutron.plugins.necnwa.db.api.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test__delete_nat_success(self, gntb, sntb):
        nid = 'uuid-nat-103'
        rcode.value_json = {}
        rcode.value_json['NAT_' + nid] = 1
        kargs['data'] = {
            'id': nid,
            'tenant_id': 'T-103'
        }
        _delete_nat_success(MagicMock(), 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 1)
        eq_(sntb.call_count, 1)

        gntb.reset_mock()
        gntb.side_effect = Exception
        _delete_nat_success(MagicMock(), 200, jbody, *args, **kargs)
        eq_(gntb.call_count, 1)


class test__deleteNatError:
    def test__delete_nat_error(self):
        _delete_nat_error(context, 200, jbody, *args, **kargs)
        lvl = LOG.getEffectiveLevel()
        LOG.setLevel(logging.DEBUG)
        _delete_nat_error(context, '200', jbody, *args, **kargs)
        LOG.setLevel(lvl)
        ok_(True)

class test_add_interface_by_port:

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test__create_tenant_true(self, ct):
        tid = '007ed0e1c1de424e82be53ce213e87c2'
        ct.return_value = 200, None
        ret = _create_tenant(tid)
        ok_(ret is True)

        ct.return_value = 500, None
        ret = _create_tenant(tid)
        ok_(ret is True)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test__create_tenant_false(self, ct):
        tid = '007ed0e1c1de424e82be53ce213e87c2'
        ct.return_value = 300, None
        ret = _create_tenant(tid)
        ok_(ret is False)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient')
    def test__create_tenant_except(self, cli):
        tid = '007ed0e1c1de424e82be53ce213e87c2'
        cli.return_value = None
        ret = _create_tenant(tid)
        ok_(ret is False)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    def test__create_tenant_nw_true(self, ctn):
        ctn.return_value = 200, None
        nwa_data = {'CreateTenant': True,
                    'NWA_tenant_id': 'DC01_007ed0e1c1de424e82be53ce213e87c2'}

        ret = _create_tenant_nw(context, nwa_data)
        ok_(ret is True)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    def test__create_tenant_nw_false(self, ctn):
        ctn.return_value = 200, None
        nwa_data = {'CreateTenant': True,
                    'NWA_tenant_id': 'DC01_007ed0e1c1de424e82be53ce213e87c2',
                    'CreateTenantNW': True}

        ret = _create_tenant_nw(context, nwa_data)
        ok_(ret is False)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient')
    def test__create_tenant_nw_except(self, cli):
        cli.return_value = None
        nwa_data = {'CreateTenant': True,
                    'NWA_tenant_id': 'DC01_007ed0e1c1de424e82be53ce213e87c2'}

        ret = _create_tenant_nw(context, nwa_data)
        ok_(ret is True)

    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_create_tenant_fw')
    def test_nwa_update_router_with_create(self, utn):
        utn.return_value = True

        devkey = 'DEV_DummyId_' + context.network.current['id']
        nwa_data = {'CreateTenant': True,
                    'NWA_tenant_id': 'DC01_007ed0e1c1de424e82be53ce213e87c2',
                    'CreateTenantNW': True}

        ret = nwa_update_router(context, nwa_data)
        ok_(ret is True)

    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_update_tenant_fw')
    def test_nwa_update_router_with_update(self, utn):
        utn.return_value = True

        devkey = 'DEV_DummyId_' + context.network.current['id']
        nwa_data = {'CreateTenant': True,
                    'NWA_tenant_id': 'DC01_007ed0e1c1de424e82be53ce213e87c2',
                    'CreateTenantNW': True,
                    devkey: 'DummyNetworkName'}

        ret = nwa_update_router(context, nwa_data)
        ok_(ret is True)

    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_ctnt(self, gpt, gtid, ctnt):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        ctnt.return_value = False
        
        ret = add_router_interface_by_port(plugin, context, router_id, interface_info)

        ok_(ret is False)

    @patch('neutron.plugins.necnwa.db.api.add_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_nbd(self, gpt, gtid, ctnt, nbd):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        ctnt.return_value = True
        nbd.return_value = False
        
        ret = add_router_interface_by_port(plugin, context, router_id, interface_info)

        ok_(ret is False)

    @patch('neutron.plugins.necnwa.db.api.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_gbd(self, gpt, gtid, ctnt, gbd):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        ctnt.return_value = True
        gbd.return_value = True
        
        ret = add_router_interface_by_port(plugin, context, router_id, interface_info)

        ok_(ret is False)

    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant_nw')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_ctnw(self, gpt, gtid, ctnt, ctnw):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        ctnt.return_value = True
        ctnw.return_value = True
        
        ret = add_router_interface_by_port(plugin, context, router_id, interface_info)

        ok_(ret is True)

    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_create_vlan')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant_nw')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_cvln(self, gpt, gtid, ctnt, ctnw, cvln):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        ctnt.return_value = True
        ctnw.return_value = False
        cvln.return_value = True
        
        ret = add_router_interface_by_port(plugin, context, router_id, interface_info)

        ok_(ret is True)

    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_update_router')
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_create_vlan')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant_nw')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_urt(self, gpt, gtid, ctnt, ctnw, cvln, urt):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        ctnt.return_value = True
        ctnw.return_value = False
        cvln.return_value = False
        urt.return_value = True
        
        ret = add_router_interface_by_port(plugin, context, router_id, interface_info)

        ok_(ret is True)

    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_update_router')
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_create_vlan')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant_nw')
    @patch('neutron.plugins.necnwa.necnwa_utils._create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_utils.get_nwa_tenant_id')
    @patch('neutron.plugins.ml2.plugin.Ml2Plugin._get_port')
    def test_add_router_interface_by_port_urt_false(self, gpt, gtid, ctnt, ctnw, cvln, urt):
        # case: _create_tenant is False.
        plugin = MagicMock()
        context = MagicMock()
        router_id = MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}
        gtid.return_value = 'DC01_007ed0e1c1de424e82be53ce213e87c2'
        ctnt.return_value = True
        ctnw.return_value = False
        cvln.return_value = False
        urt.return_value = False
        
        ret = add_router_interface_by_port(plugin, context, router_id, interface_info)

        ok_(ret is True)
