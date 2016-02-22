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

from networking_nec.plugins.necnwa.agent import proxy_l2
from networking_nec.plugins.necnwa.common import exceptions as nwa_exc
from networking_nec.tests.necnwa.agent import test_nwa_agent

load_tests = testscenarios.load_tests_apply_scenarios


def load_data_file(name):
    base_dir = os.path.dirname(__file__)
    fn = os.path.join(base_dir, 'data', name)
    with open(fn) as f:
        return jsonutils.loads(f.read())


class TestAgentProxyL2(test_nwa_agent.TestNECNWANeutronAgentBase):

    def test__create_tenant_nw_fail(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        resource_group_name = 'OpenStack/DC1/APP'
        nwa_data1 = {}
        nwa_info = {
            'resource_group_name': resource_group_name,
            'resource_group_name_nw': resource_group_name,
        }
        self.nwacli.create_tenant_nw.return_value = 500, {}
        e = self.assertRaises(
            nwa_exc.AgentProxyException,
            self.agent.proxy_l2._create_tenant_nw,
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            resource_group_name=resource_group_name,
            nwa_data=nwa_data1,
            nwa_info=nwa_info,
        )
        ret_val = e.value
        self.assertEqual(ret_val, nwa_data1)

    def test__create_vlan_succeed1(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {}
        nwa_info = load_data_file('add_router_interface_nwa_info.json')
        ret_vln = load_data_file('create_vlan_result.json')
        ret_vln['resultdata']['VlanID'] = '300'
        self.nwacli.create_vlan.return_value = (200, ret_vln)
        result = self.agent.proxy_l2._create_vlan(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )
        exp_data = load_data_file('expected_proxy_create_vlan_succeed1.json')
        self.assertDictEqual(exp_data, result)

    def test__create_vlan_fail1(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {'NW_546a8551-5c2b-4050-a769-cc3c962fc5cf': 'net100'}
        nwa_info = load_data_file('add_router_interface_nwa_info.json')
        self.nwacli.create_vlan.return_value = 500, {}
        self.assertRaises(
            nwa_exc.AgentProxyException,
            self.agent.proxy_l2._create_vlan,
            self.context,
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
        self.nwacli.create_vlan.return_value = (200, dvl_result)
        result = self.agent.proxy_l2._delete_vlan(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )
        self.assertDictEqual(nwa_data, result)


class TestAgentProxyL2CreateGeneralDevScenarios(
        test_nwa_agent.TestNECNWANeutronAgentBase):

    scenarios = [
        ('test_create_general_dev_succeed1',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info_file': 'create_general_dev_nwa_info.json',
          'gtb_data_file': {}},
         ),
        ('test_create_general_dev_succeed2',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info_file': 'create_general_dev_nwa_info_2.json',
          'gtb_data_file': 'nwa_data_one_general_dev.json'},
         ),
        ('test_create_general_dev_fail1',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info_file': 'create_general_dev_nwa_info.json',
          'gtb_data_file': {}},
         ),
        ('test_create_general_dev_fail2',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (500, 'create_vlan_result.json'),
          'nwa_info_file': 'create_general_dev_nwa_info.json',
          'gtb_data_file': {}},
         ),
        ('test_create_general_dev_fail3',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (500, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info_file': 'create_general_dev_nwa_info.json',
          'gtb_data_file': {}},
         ),
        ('test_create_general_dev_fail4',
         {'retval_create_tenant': (501, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info_file': 'create_general_dev_nwa_info.json',
          'gtb_data_file': {}},
         ),
        ('test_create_general_dev_ex1',
         {'retval_create_tenant': (200, {}),
          'retval_create_tenant_nw': (200, 'create_tenant_nw_result.json'),
          'retval_create_vlan': (200, 'create_vlan_result.json'),
          'nwa_info_file': 'nwa_info_create_general_dev_ex1.json',
          'gtb_data_file': 'nwa_data_create_general_dev_ex1.json'},
         ),
    ]

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_general_dev(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = "844eb55f21e84a289e9c22098d387e5d"
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file(self.nwa_info_file)

        self.nwacli.create_tenant.return_value = self.retval_create_tenant
        self.nwacli.create_tenant_nw.return_value = (
            self.retval_create_tenant_nw[0],
            load_data_file(self.retval_create_tenant_nw[1])
        )
        self.nwacli.create_vlan.return_value = (
            self.retval_create_vlan[0],
            load_data_file(self.retval_create_vlan[1])
        )

        if isinstance(self.gtb_data_file, six.string_types):
            gtb.return_value = load_data_file(self.gtb_data_file)
        else:
            gtb.return_value = self.gtb_data_file

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


class TestAgentProxyL2DeleteGeneralDevScenarios(
        test_nwa_agent.TestNECNWANeutronAgentBase):

    scenarios = [
        ('test_delete_general_dev_succeed1',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_one_general_dev.json',
          },
         ),
        ('test_delete_general_dev_succeed2',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_two_general_dev.json',
          },
         ),
        ('test_delete_general_dev_succeed3',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_two_port_general_dev.json',
          },
         ),
        ('test_delete_general_dev_fail1',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_one_general_dev.json',
          },
         ),
        # TODO(amotoki): It seems fail1 and fail2 are same.
        ('test_delete_general_dev_fail2',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_one_general_dev.json',
          },
         ),
        ('test_delete_general_dev_fail3',
         {'retval_delete_tenant': (500, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_one_general_dev.json',
          },
         ),
        ('test_delete_general_dev_fail4',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (500, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_one_general_dev.json',
          },
         ),
        ('test_delete_general_dev_fail5',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (500, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_one_general_dev.json',
          },
         ),
        ('test_delete_general_dev_fail6',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': 'nwa_data_two_port_general_dev_fail.json',
          },
         ),
        ('test_delete_general_dev_fail7',
         {'retval_delete_tenant': (200, {}),
          'retval_delete_tenant_nw': (200, 'delete_tenant_nw_result.json'),
          'retval_delete_vlan': (200, 'delete_vlan_result.json'),
          'nwa_info_file': 'delete_general_dev_nwa_info.json',
          'gtb_data_file': {},
          },
         ),
    ]

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_general_dev(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = "844eb55f21e84a289e9c22098d387e5d"
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file(self.nwa_info_file)

        self.nwacli.delete_tenant.return_value = self.retval_delete_tenant
        self.nwacli.delete_tenant_nw.return_value = (
            self.retval_delete_tenant_nw[0],
            load_data_file(self.retval_delete_tenant_nw[1])
        )
        self.nwacli.delete_vlan.return_value = (
            self.retval_delete_vlan[0],
            load_data_file(self.retval_delete_vlan[1])
        )

        if isinstance(self.gtb_data_file, six.string_types):
            gtb.return_value = load_data_file(self.gtb_data_file)
        else:
            gtb.return_value = self.gtb_data_file

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


class TestNECNWANeutronAgentRpc(test_nwa_agent.TestNECNWANeutronAgentBase):

    scenarios = [
        # ### GeneralDev: None
        # ### add Openstack/DC/HA1
        ('create_general_dev_succeed1',
         {'mode': 'create_general_dev',
          'gtb_data_file': None,
          'nwa_info_file': 'nwa_info_create_general_dev_succeed1.json'}),
        # ### GeneralDev: Openstack/DC/HA1
        # ### add Openstack/DC/HA1
        ('create_general_dev_succeed2',
         {'mode': 'create_general_dev',
          'gtb_data_file': 'nwa_data_create_general_dev_succeed2.json',
          'nwa_info_file': 'nwa_info_create_general_dev_succeed2.json',
          'mock_wait_agent_notifier': True}),
        # ### GeneralDev: Openstack/DC/HA1
        # ### add Openstack/DC/HA2
        ('create_general_dev_succeed3',
         {'mode': 'create_general_dev',
          'gtb_data_file': 'nwa_data_create_general_dev_succeed3.json',
          'nwa_info_file': 'nwa_info_create_general_dev_succeed3.json'}),
        # ### GeneralDev: Openstack/DC/HA1 x1
        # ### del Openstack/DC/HA1
        ('delete_general_dev_succeed1',
         {'mode': 'delete_general_dev',
          'gtb_data_file': 'nwa_data_delete_general_dev_succeed1.json',
          'nwa_info_file': 'nwa_info_delete_general_dev_succeed1.json'}),
        # ### GeneralDev: Openstack/DC/HA1 x2
        # ### del Openstack/DC/HA1
        ('delete_general_dev_succeed2',
         {'mode': 'delete_general_dev',
          'gtb_data_file': 'nwa_data_delete_general_dev_succeed2.json',
          'nwa_info_file': 'nwa_info_delete_general_dev_succeed2.json'}),
        # ### GeneralDev: Openstack/DC/HA1 x1, Openstack/DC/HA2 x1
        # ### del Openstack/DC/HA1
        ('delete_general_dev_succeed3',
         {'mode': 'delete_general_dev',
          'gtb_data_file': 'nwa_data_delete_general_dev_succeed3.json',
          'nwa_info_file': 'nwa_info_delete_general_dev_succeed3.json'}),
    ]

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    def test_general_dev(self, stb, utb, gtb):
        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = mock.MagicMock()
        stb.return_value = {}
        utb.return_value = {'status': 'SUCCESS'}
        if self.gtb_data_file:
            gtb.return_value = load_data_file(self.gtb_data_file)
        else:
            gtb.return_value = None
        nwa_info = load_data_file(self.nwa_info_file)

        if getattr(self, 'mock_wait_agent_notifier', False):
            mock.patch('networking_nec.plugins.necnwa.agent.proxy_l2.'
                       'WAIT_AGENT_NOTIFIER', new=0).start()

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
