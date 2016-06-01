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

import os.path

import mock
from oslo_serialization import jsonutils
import six
import testscenarios

from networking_nec.nwa.agent import proxy_l2
from networking_nec.nwa.common import exceptions as nwa_exc
from networking_nec.tests.unit.nwa.agent import base


def load_data_file(name):
    base_dir = os.path.dirname(__file__)
    fn = os.path.join(base_dir, 'test_data', name)
    with open(fn) as f:
        return jsonutils.loads(f.read())


class TestAgentProxyL2(base.TestNWAAgentBase):

    def test__create_tenant_nw_fail(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        resource_group_name = 'OpenStack/DC1/APP'
        nwa_data1 = {}
        nwa_info = {
            'resource_group_name': resource_group_name,
            'resource_group_name_nw': resource_group_name,
        }
        self.nwacli.l2.create_tenant_nw.return_value = 500, {}
        e = self.assertRaises(
            nwa_exc.AgentProxyException,
            self.agent.proxy_l2._create_tenant_nw,
            mock.sentinel.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            resource_group_name=resource_group_name,
            nwa_data=nwa_data1,
            nwa_info=nwa_info,
        )
        ret_val = e.value
        self.assertEqual(ret_val, nwa_data1)

    def test__create_tenant_nw_with_key(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        resource_group_name = 'OpenStack/DC1/APP'
        nwa_data1 = {proxy_l2.KEY_CREATE_TENANT_NW: True}
        nwa_info = {
            'resource_group_name': resource_group_name,
            'resource_group_name_nw': resource_group_name,
        }
        result = self.agent.proxy_l2._create_tenant_nw(
            mock.sentinel.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            resource_group_name=resource_group_name,
            nwa_data=nwa_data1,
            nwa_info=nwa_info,
        )
        self.assertIsNone(result)

    def test__create_vlan_succeed1(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {}
        nwa_info = load_data_file('add_router_interface_nwa_info.json')
        ret_vln = load_data_file('create_vlan_result.json')
        ret_vln['resultdata']['VlanID'] = '300'
        self.nwacli.l2.create_vlan.return_value = (200, ret_vln)
        result = self.agent.proxy_l2._create_vlan(
            mock.sentinel.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )
        exp_data = load_data_file('expected_proxy_create_vlan_succeed1.json')
        self.assertDictEqual(exp_data, result)

    def test__create_vlan_succeed2(self):
        net_id = '546a8551-5c2b-4050-a769-cc3c962fc5cf'
        vlan_id_key = 'VLAN_' + net_id
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {vlan_id_key: 'net-uuid-1'}
        nwa_info = load_data_file('add_router_interface_nwa_info.json')
        ret_vln = load_data_file('create_vlan_result.json')
        ret_vln['resultdata']['VlanID'] = '300'
        ret_vln['resultdata'][net_id] = 'net-uuid-1'
        self.nwacli.l2.create_vlan.return_value = (200, ret_vln)
        result = self.agent.proxy_l2._create_vlan(
            mock.sentinel.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )
        self.assertDictEqual(nwa_data, result)

    def test__create_vlan_fail1(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {'NW_546a8551-5c2b-4050-a769-cc3c962fc5cf': 'net100'}
        nwa_info = load_data_file('add_router_interface_nwa_info.json')
        self.nwacli.l2.create_vlan.return_value = 500, {}
        self.assertRaises(
            nwa_exc.AgentProxyException,
            self.agent.proxy_l2._create_vlan,
            mock.sentinel.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    def test__delete_vlan_succeed1(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = load_data_file('nwa_data_delete_vlan_succeed1.json')
        nwa_info = load_data_file('add_router_interface_nwa_info.json')
        dvl_result = load_data_file('delete_vlan_result.json')
        self.nwacli.l2.create_vlan.return_value = (200, dvl_result)
        result = self.agent.proxy_l2._delete_vlan(
            mock.sentinel.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )
        self.assertDictEqual(nwa_data, result)

    def test_check_vlan_for_tenant_fw(self):
        network_id = '546a8551-5c2b-4050-a769-cc3c962fc5cf'
        segment = 'OpenStack/DC1/APP'
        nwa_data = {'VLAN_%s_%s_VlanID' % (network_id, segment): '4000'}
        self.assertEqual(1, proxy_l2.check_vlan(network_id, nwa_data))

    def test_check_vlan_for_tenant_lb(self):
        network_id = '546a8551-5c2b-4050-a769-cc3c962fc5cf'
        segment = 'OpenStack/DC1/APP'
        nwa_data = {'VLAN_LB_%s_%s_VlanID' % (network_id, segment): '4000'}
        self.assertEqual(1, proxy_l2.check_vlan(network_id, nwa_data))


class TestAgentProxyL2CreateGeneralDev(testscenarios.WithScenarios,
                                       base.TestNWAAgentBase):

    scenarios = [
        ('succeed1',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info': 'create_general_dev_nwa_info.json',
          'gtb_data': {}},
         ),
        ('succeed2',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info': 'create_general_dev_nwa_info_2.json',
          'gtb_data': 'nwa_data_one_general_dev.json'},
         ),
        ('fail1',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info': 'create_general_dev_nwa_info.json',
          'gtb_data': {}},
         ),
        ('fail2',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (500, 'create_vlan_result.json'),
          'nwa_info': 'create_general_dev_nwa_info.json',
          'gtb_data': {}},
         ),
        ('fail3',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (500, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info': 'create_general_dev_nwa_info.json',
          'gtb_data': {}},
         ),
        ('fail4',
         {'retval_create_tenant': (501, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info': 'create_general_dev_nwa_info.json',
          'gtb_data': {}},
         ),
        ('ex1',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info': 'nwa_info_create_general_dev_ex1.json',
          'gtb_data': 'nwa_data_create_general_dev_ex1.json'},
         ),
    ]

    @mock.patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.nwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_create_general_dev(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = "844eb55f21e84a289e9c22098d387e5d"
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file(self.nwa_info)

        self.nwacli.tenant.create_tenant.return_value = \
            self.retval_create_tenant
        self.nwacli.l2.create_tenant_nw.return_value = (
            self.retval_create_tenant_nw[0],
            load_data_file(self.retval_create_tenant_nw[1])
        )
        self.nwacli.l2.create_vlan.return_value = (
            self.retval_create_vlan[0],
            load_data_file(self.retval_create_vlan[1])
        )

        if isinstance(self.gtb_data, six.string_types):
            gtb.return_value = load_data_file(self.gtb_data)
        else:
            gtb.return_value = self.gtb_data

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


class TestAgentProxyL2DeleteGeneralDev(testscenarios.WithScenarios,
                                       base.TestNWAAgentBase):

    scenarios = [
        ('succeed1',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_one_general_dev.json',
          },
         ),
        ('succeed2',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_two_general_dev.json',
          },
         ),
        ('succeed3',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_two_port_general_dev.json',
          },
         ),
        ('fail1',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_one_general_dev.json',
          },
         ),
        ('fail2',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_one_general_dev.json',
          },
         ),
        ('fail3',
         {'retval_delete_tenant': (500, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_one_general_dev.json',
          },
         ),
        ('fail4',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (500, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_one_general_dev.json',
          },
         ),
        ('fail5',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (500, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_one_general_dev.json',
          },
         ),
        ('fail6',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': 'nwa_data_two_port_general_dev_fail.json',
          },
         ),
        ('fail7',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info': 'delete_general_dev_nwa_info.json',
          'gtb_data': {},
          },
         ),
    ]

    @mock.patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.nwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_delete_general_dev(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = "844eb55f21e84a289e9c22098d387e5d"
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file(self.nwa_info)

        self.nwacli.tenant.delete_tenant.return_value = \
            self.retval_delete_tenant
        self.nwacli.l2.delete_tenant_nw.return_value = (
            self.retval_delete_tenant_nw[0],
            load_data_file(self.retval_delete_tenant_nw[1])
        )
        self.nwacli.l2.delete_vlan.return_value = (
            self.retval_delete_vlan[0],
            load_data_file(self.retval_delete_vlan[1])
        )

        if isinstance(self.gtb_data, six.string_types):
            gtb.return_value = load_data_file(self.gtb_data)
        else:
            gtb.return_value = self.gtb_data

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


def test_check_segment():
    network_id = 'a94fd0fc-2282-4092-9485-b0f438b0f6c4'
    nwa_data = load_data_file('nwa_data_check_segment.json')
    proxy_l2.check_segment(network_id, nwa_data)


class TestGetResourceGroupName(base.TestNWAAgentBase):

    def setUp(self):
        super(TestGetResourceGroupName, self).setUp()
        self.nwa_info = load_data_file('nwa_info_get_resource_group_name.json')
        self.nwa_data = load_data_file('nwa_data_get_resource_group_name.json')
        self.dev_type = 'GeneralDev'
        self.resource_group_name = 'OpenStack/DC/HA1'

    def test_resource_group_name_found(self):
        self.assertEqual(
            proxy_l2.get_resource_group_name(self.nwa_info, self.nwa_data,
                                             self.dev_type),
            self.resource_group_name
        )

    def test_mac_not_found(self):
        self.nwa_info['port']['mac'] = 'X'
        self.assertIsNone(
            proxy_l2.get_resource_group_name(self.nwa_info, self.nwa_data,
                                             self.dev_type))

    def test_network_id_not_found(self):
        self.nwa_info['network']['id'] = 'X'
        self.assertIsNone(
            proxy_l2.get_resource_group_name(self.nwa_info, self.nwa_data,
                                             self.dev_type))

    def test_device_id_not_found(self):
        self.nwa_info['device']['id'] = 'X'
        self.assertIsNone(
            proxy_l2.get_resource_group_name(self.nwa_info, self.nwa_data,
                                             self.dev_type))

    def test_dev_type_not_found(self):
        dev_type = 'X'
        self.assertIsNone(
            proxy_l2.get_resource_group_name(self.nwa_info, self.nwa_data,
                                             dev_type))


class TestNECNWANeutronAgentRpc(testscenarios.WithScenarios,
                                base.TestNWAAgentBase):

    scenarios = [
        # ### GeneralDev: None
        # ### add Openstack/DC/HA1
        ('create_general_dev_succeed1',
         {'mode': 'create_general_dev',
          'gtb_data': None,
          'nwa_info': 'nwa_info_create_general_dev_succeed1.json'}),
        # ### GeneralDev: Openstack/DC/HA1
        # ### add Openstack/DC/HA1
        ('create_general_dev_succeed2',
         {'mode': 'create_general_dev',
          'gtb_data': 'nwa_data_create_general_dev_succeed2.json',
          'nwa_info': 'nwa_info_create_general_dev_succeed2.json',
          'mock_wait_agent_notifier': True}),
        # ### GeneralDev: Openstack/DC/HA1
        # ### add Openstack/DC/HA2
        ('create_general_dev_succeed3',
         {'mode': 'create_general_dev',
          'gtb_data': 'nwa_data_create_general_dev_succeed3.json',
          'nwa_info': 'nwa_info_create_general_dev_succeed3.json'}),
        # ### GeneralDev: Openstack/DC/HA1 x1
        # ### del Openstack/DC/HA1
        ('delete_general_dev_succeed1',
         {'mode': 'delete_general_dev',
          'gtb_data': 'nwa_data_delete_general_dev_succeed1.json',
          'nwa_info': 'nwa_info_delete_general_dev_succeed1.json'}),
        # ### GeneralDev: Openstack/DC/HA1 x2
        # ### del Openstack/DC/HA1
        ('delete_general_dev_succeed2',
         {'mode': 'delete_general_dev',
          'gtb_data': 'nwa_data_delete_general_dev_succeed2.json',
          'nwa_info': 'nwa_info_delete_general_dev_succeed2.json'}),
        # ### GeneralDev: Openstack/DC/HA1 x1, Openstack/DC/HA2 x1
        # ### del Openstack/DC/HA1
        ('delete_general_dev_succeed3',
         {'mode': 'delete_general_dev',
          'gtb_data': 'nwa_data_delete_general_dev_succeed3.json',
          'nwa_info': 'nwa_info_delete_general_dev_succeed3.json'}),
    ]

    @mock.patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.nwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    @mock.patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    def test_general_dev(self, stb, utb, gtb):
        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = mock.MagicMock()
        stb.return_value = {}
        utb.return_value = {'status': 'SUCCEED'}
        if self.gtb_data:
            gtb.return_value = load_data_file(self.gtb_data)
        else:
            gtb.return_value = None
        nwa_info = load_data_file(self.nwa_info)

        if getattr(self, 'mock_wait_agent_notifier', False):
            mock.patch('networking_nec.nwa.agent.proxy_l2.WAIT_AGENT_NOTIFIER',
                       new=0).start()

        if self.mode == 'create_general_dev':
            rc = self.agent.proxy_l2.create_general_dev(
                context,
                tenant_id=tenant_id,
                nwa_tenant_id=nwa_tenant_id,
                nwa_info=nwa_info)
            self.assertTrue(rc)
        elif self.mode == 'delete_general_dev':
            rc = self.agent.proxy_l2.delete_general_dev(
                context,
                tenant_id=tenant_id,
                nwa_tenant_id=nwa_tenant_id,
                nwa_info=nwa_info)
            self.assertTrue(rc)
        else:
            self.fail('mode %s is invalide' % self.mode)
