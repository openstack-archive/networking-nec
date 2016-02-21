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

from networking_nec.plugins.necnwa.agent import proxy_l2
from networking_nec.plugins.necnwa.common import exceptions as nwa_exc
from networking_nec.tests.necnwa.agent import test_nwa_agent


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

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_create_general_dev_succeed1(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('create_general_dev_nwa_info.json')

        self.nwacli.create_tenant.   return_value = (200, {})
        self.nwacli.create_tenant_nw.return_value = (
            200, load_data_file('create_tenant_nw_result.json'))
        self.nwacli.create_vlan.     return_value = (
            200, load_data_file('create_vlan_result.json'))
        gtb.return_value = {}

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_create_general_dev_succeed2(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('create_general_dev_nwa_info_2.json')

        self.nwacli.create_tenant.return_value = (200, {})
        self.nwacli.create_tenant_nw.return_value = (
            200, load_data_file('create_tenant_nw_result.json'))
        self.nwacli.create_vlan.return_value = (
            200, load_data_file('create_vlan_result.json'))
        gtb.return_value = load_data_file('nwa_data_one_general_dev.json')

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_create_general_dev_fail1(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('create_general_dev_nwa_info.json')

        self.nwacli.create_tenant.   return_value = (200, {})
        self.nwacli.create_tenant_nw.return_value = (200, load_data_file('create_tenant_nw_result.json'))  # noqa
        self.nwacli.create_vlan.     return_value = (200, load_data_file('create_vlan_result.json'))  # noqa
        gtb.return_value = {}

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_create_general_dev_fail2(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('create_general_dev_nwa_info.json')

        self.nwacli.create_tenant.   return_value = (200, {})
        self.nwacli.create_tenant_nw.return_value = (200, load_data_file('create_tenant_nw_result.json'))  # noqa
        self.nwacli.create_vlan.     return_value = (500, load_data_file('create_vlan_result.json'))  # noqa
        gtb.return_value = {}

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.get_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.'
                'TenantBindingServerRpcApi.set_nwa_tenant_binding')
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.'
                'AgentProxyTenant.update_tenant_binding')
    def test_create_general_dev_fail3(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('create_general_dev_nwa_info.json')

        self.nwacli.create_tenant.   return_value = (200, {})
        self.nwacli.create_tenant_nw.return_value = (500, load_data_file('create_tenant_nw_result.json'))  # noqa
        self.nwacli.create_vlan.     return_value = (200, load_data_file('create_vlan_result.json'))  # noqa
        gtb.return_value = {}

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_create_general_dev_fail4(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('create_general_dev_nwa_info.json')

        self.nwacli.create_tenant.   return_value = (501, {})
        self.nwacli.create_tenant_nw.return_value = (200, load_data_file('create_tenant_nw_result.json'))  # noqa
        self.nwacli.create_vlan.     return_value = (200, load_data_file('create_vlan_result.json'))  # noqa
        gtb.return_value = {}

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_succeed1(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')
        nwa_data = load_data_file('nwa_data_one_general_dev.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = nwa_data

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_succeed2(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = load_data_file('nwa_data_two_general_dev.json')

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_succeed3(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = load_data_file('nwa_data_two_port_general_dev.json')

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_fail1(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = load_data_file('nwa_data_one_general_dev.json')

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_fail2(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')
        nwa_data = load_data_file('nwa_data_one_general_dev.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = nwa_data

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_fail3(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')

        self.nwacli.delete_tenant.return_value = (500, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = load_data_file('nwa_data_one_general_dev.json')

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_fail4(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (500, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = load_data_file('nwa_data_one_general_dev.json')

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_fail5(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (500, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = load_data_file('nwa_data_one_general_dev.json')

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_fail6(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = load_data_file('nwa_data_two_port_general_dev_fail.json')  # noqa

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_delete_general_dev_fail7(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('delete_general_dev_nwa_info.json')

        self.nwacli.delete_tenant.return_value = (200, {})
        self.nwacli.delete_tenant_nw.return_value = (200, load_data_file('delete_tenant_nw_result.json'))  # noqa
        self.nwacli.delete_vlan.return_value = (200, load_data_file('delete_vlan_result.json'))  # noqa
        gtb.return_value = {}

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    #####
    # appendix.
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_create_general_dev_ex1(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = "844eb55f21e84a289e9c22098d387e5d"
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = load_data_file('nwa_info_create_general_dev_ex1.json')

        self.nwacli.create_tenant.   return_value = (200, {})
        self.nwacli.create_tenant_nw.return_value = (200, load_data_file('create_tenant_nw_result.json'))  # noqa
        self.nwacli.create_vlan.     return_value = (200, load_data_file('create_vlan_result.json'))  # noqa
        gtb.return_value = load_data_file('nwa_data_create_general_dev_ex1.json')  # noqa

        self.agent.proxy_l2.create_general_dev(
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

    # ### GeneralDev: None
    # ### add Openstack/DC/HA1
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_create_general_dev_succeed1(self, stb, utb, gtb):
        context = mock.MagicMock()
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        stb.return_value = {}
        utb.return_value = {'status': 'SUCCESS'}
        gtb.return_value = None
        nwa_info = load_data_file('nwa_info_create_general_dev_succeed1.json')
        rc = self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1
    # ### add Openstack/DC/HA1
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_l2.'
                'WAIT_AGENT_NOTIFIER', new=0)
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_create_general_dev_succeed2(self, stb, utb, gtb):

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = mock.MagicMock()

        stb.return_value = {}
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = load_data_file('nwa_data_create_general_dev_succeed2.json')  # noqa
        nwa_info = load_data_file('nwa_info_create_general_dev_succeed2.json')
        rc = self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1
    # ### add Openstack/DC/HA2
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_create_general_dev_succeed3(self, stb, utb, gtb):

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = mock.MagicMock()

        stb.return_value = {}
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = load_data_file('nwa_data_create_general_dev_succeed3.json')  # noqa
        nwa_info = load_data_file('nwa_info_create_general_dev_succeed3.json')

        rc = self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1 x1
    # ### del Openstack/DC/HA1
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_delete_general_dev_succeed1(self, stb, utb, gtb):

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = mock.MagicMock()

        stb.return_value = {}
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = load_data_file('nwa_data_delete_general_dev_succeed1.json')  # noqa
        nwa_info = load_data_file('nwa_info_delete_general_dev_succeed1.json')

        rc = self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1 x2
    # ### del Openstack/DC/HA1
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_delete_general_dev_succeed2(self, stb, utb, gtb):

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = mock.MagicMock()

        stb.return_value = {}
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = load_data_file('nwa_data_delete_general_dev_succeed2.json')  # noqa
        nwa_info = load_data_file('nwa_info_delete_general_dev_succeed2.json')

        rc = self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1 x1, Openstack/DC/HA2 x1
    # ### del Openstack/DC/HA1
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_delete_general_dev_succeed3(self, stb, utb, gtb):

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = mock.MagicMock()

        stb.return_value = {}
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = load_data_file('nwa_data_delete_general_dev_succeed3.json')  # noqa
        nwa_info = load_data_file('nwa_info_delete_general_dev_succeed3.json')
        rc = self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info)
        self.assertTrue(rc)
