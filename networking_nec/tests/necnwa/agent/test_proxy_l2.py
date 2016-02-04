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

from copy import deepcopy

import mock

from networking_nec.plugins.necnwa.agent import proxy_l2
from networking_nec.tests.necnwa.agent import test_data
from networking_nec.tests.necnwa.agent import test_nwa_agent

# TODO(amotoki): Clean up this
proxy_l2.WAIT_AGENT_NOTIFIER = 0


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
        self.nwacli.create_tenant_nw.return_value = 500, dict()
        result, nwa_data2 = self.agent.proxy_l2._create_tenant_nw(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            resource_group_name=resource_group_name,
            nwa_data=nwa_data1,
            nwa_info=nwa_info,
        )
        self.assertEqual(nwa_data1, nwa_data2)
        self.assertFalse(result)

    def test__create_vlan_succeed1(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {}
        nwa_info = deepcopy(test_data.nwa_info_add_intf)
        ret_vln = deepcopy(test_data.result_vln)
        ret_vln['resultdata']['VlanID'] = '300'
        self.nwacli.create_vlan.return_value = (200, ret_vln)
        result, nwa_data = self.agent.proxy_l2._create_vlan(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    def test__create_vlan_fail1(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {'NW_546a8551-5c2b-4050-a769-cc3c962fc5cf': 'net100'}
        nwa_info = deepcopy(test_data.nwa_info_add_intf)
        self.nwacli.create_vlan.return_value = 500, dict()
        result, nwa_data = self.agent.proxy_l2._create_vlan(
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
        nwa_data = {
            "CreateTenantNW": True,
            "CreateTenant": "1",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "device_id",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TenantFWName": "TFW27",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_ip_address": "192.168.100.1",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_mac_address": "fa:16:3e:04:d3:28",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_device_owner": "network:router_interface",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_physical_network": "OpenStack/DC1/APP",  # noqa
            "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_network_id": "546a8551-5c2b-4050-a769-cc3c962fc5cf",  # noqa
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_nwa_network_name": "LNW_BusinessVLAN_120",  # noqa
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet": "192.168.100.0",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet_id": "7dabadaa-06fc-45fb-af0b-33384cf291c4",  # noqa
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf": "physical_network",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_VlanID": "4000",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_CreateVlan": "",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_CreateVlan": "CreateVlan",  # noqa
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP": "physical_network",  # noqa
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",  # noqa
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_VlanID": "62"  # noqa
        }

        nwa_info = deepcopy(test_data.nwa_info_add_intf)
        self.nwacli.create_vlan.return_value = (200,
                                                deepcopy(test_data.result_dvl))
        result, nwa_data = self.agent.proxy_l2._delete_vlan(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_create_general_dev_succeed1(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(test_data.nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(test_data.result_tnw))  # noqa
        self.nwacli.create_vlan.     return_value = (200, deepcopy(test_data.result_vln))  # noqa
        gtb.return_value = dict()

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_create_general_dev_succeed2(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(test_data.nwa_info_create_gdv2)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(test_data.result_tnw))  # noqa
        self.nwacli.create_vlan.     return_value = (200, deepcopy(test_data.result_vln))  # noqa
        gtb.return_value = deepcopy(test_data.nwa_data_one_gdev)

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_create_general_dev_fail1(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(test_data.nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(test_data.result_tnw))  # noqa
        self.nwacli.create_vlan.     return_value = (200, deepcopy(test_data.result_vln))  # noqa
        gtb.return_value = dict()

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_create_general_dev_fail2(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(test_data.nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(test_data.result_tnw))  # noqa
        self.nwacli.create_vlan.     return_value = (500, deepcopy(test_data.result_vln))  # noqa
        gtb.return_value = dict()

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_create_general_dev_fail3(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(test_data.nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (500, deepcopy(test_data.result_tnw))  # noqa
        self.nwacli.create_vlan.     return_value = (200, deepcopy(test_data.result_vln))  # noqa
        gtb.return_value = dict()

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

        nwa_info = deepcopy(test_data.nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (501, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(test_data.result_tnw))  # noqa
        self.nwacli.create_vlan.     return_value = (200, deepcopy(test_data.result_vln))  # noqa
        gtb.return_value = dict()

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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)
        nwa_data = deepcopy(test_data.nwa_data_one_gdev)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
        gtb.return_value = deepcopy(test_data.nwa_data_two_gdev)

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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
        gtb.return_value = deepcopy(test_data.nwa_data_two_port_gdev)

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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
        gtb.return_value = deepcopy(test_data.nwa_data_one_gdev)

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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)
        nwa_data = deepcopy(test_data.nwa_data_one_gdev)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (500, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
        gtb.return_value = deepcopy(test_data.nwa_data_one_gdev)

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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (500, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
        gtb.return_value = deepcopy(test_data.nwa_data_one_gdev)

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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (500, deepcopy(test_data.result_dvl))  # noqa
        gtb.return_value = deepcopy(test_data.nwa_data_one_gdev)

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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
        gtb.return_value = deepcopy(test_data.nwa_data_gdev_fail6)

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

        nwa_info = deepcopy(test_data.nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(test_data.result_dnw))  # noqa
        self.nwacli.delete_vlan.return_value = (200, deepcopy(test_data.result_dvl))  # noqa
        gtb.return_value = dict()

        self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    def test__dummy_ok(self):
        context = mock.MagicMock()
        rcode = mock.MagicMock()
        jbody = mock.MagicMock()
        args = mock.MagicMock()
        kwargs = mock.MagicMock()

        self.agent.proxy_l2._dummy_ok(context, rcode, jbody, args, kwargs)

    def test__dummy_ng(self):
        context = mock.MagicMock()
        rcode = mock.MagicMock()
        jbody = mock.MagicMock()
        args = mock.MagicMock()
        kwargs = mock.MagicMock()

        self.agent.proxy_l2._dummy_ng(context, rcode, jbody, args, kwargs)

    #####
    # appendix.
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    def test_create_general_dev_ex1(self, utb, stb, gtb):
        context = mock.MagicMock()
        tenant_id = "844eb55f21e84a289e9c22098d387e5d"
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = {
            "device": {
                "id": "171fff51-ac4c-444e-99a2-8957ca0fad6e",
                "owner": "compute:DC1_KVM"
            },
            "network": {
                "id": "0ed65870-9acb-48ce-8c0b-e803d527a9d2",
                "name": "net100",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC02_844eb55f21e84a289e9c22098d387e5d",
            "physical_network": "OpenStack/DC1/APP",
            "port": {
                "id": "81f78799-fd82-48ce-98c3-3df91fb4768c",
                "ip": "192.168.100.102",
                "mac": "fa:16:3e:1b:27:f9"
            },
            "resource_group": "OpenStack/DC1/APP",
            "resource_group_name": "OpenStack/DC1/APP",
            "resource_group_name_nw": "OpenStack/DC1/APP",
            "subnet": {
                "id": "df2a7b8a-e027-49ab-bf84-ade82a3c096c",
                "mask": "24",
                "netaddr": "192.168.100.0"
            },
            "tenant_id": "844eb55f21e84a289e9c22098d387e5d"
        }

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(test_data.result_tnw))  # noqa
        self.nwacli.create_vlan.     return_value = (200, deepcopy(test_data.result_vln))  # noqa
        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99": "device_id",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2": "net100",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_TYPE": "TenantFW",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_TenantFWName": "TFW8",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_ip_address": "192.168.100.1",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_mac_address": "fa:16:3e:97:4f:d4",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_TenantFWName": "TFW8",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_device_owner": "network:router_interface",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_physical_network": "OpenStack/DC1/APP",  # noqa
            "NWA_tenant_id": "DC02_844eb55f21e84a289e9c22098d387e5d",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2": "net100",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_network_id": "0ed65870-9acb-48ce-8c0b-e803d527a9d2",  # noqa
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_nwa_network_name": "LNW_BusinessVLAN_108",  # noqa
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_subnet": "192.168.100.0",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_subnet_id": "df2a7b8a-e027-49ab-bf84-ade82a3c096c",  # noqa
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP": "physical_network",  # noqa
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_CreateVlan": "CreateVlan",  # noqa
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_FW_TFW4b18c7ba-1370-410e-af4c-8578fbb3ab99": "connected",  # noqa
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_VlanID": "53"  # noqa
        }

        self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


def test_check_segment():
    network_id = 'a94fd0fc-2282-4092-9485-b0f438b0f6c4'
    nwa_data = {
        "CreateTenantNW": "1",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1": "device_id",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_TenantFWName": "TFW3",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "TenantFW",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TenantFWName": "TFW3",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.1",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:17:41:b4",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_device_owner": "network:router_interface",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_physical_network": "OpenStack/DC1/APP",  # noqa
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",  # noqa
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_103",  # noqa
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",  # noqa
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_CreateVlan": "",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_VlanID": "4000",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",  # noqa
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "CreateVlan",  # noqa
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_FW_TFW843bc108-2f17-4be4-b9cb-44e00abe78d1": "connected",  # noqa
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "37"  # noqa
    }
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
        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}
        gtb.return_value = None
        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
                "owner": "network:dhcp"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "519c51b8-9328-455a-8ae7-b204754eacea",
                "ip": "192.168.0.1",
                "mac": "fa:16:3e:76:ab:0e"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }
        rc = self.agent.proxy_l2.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1
    # ### add Openstack/DC/HA1
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.agent.proxy_tenant.AgentProxyTenant.update_tenant_binding')  # noqa
    @mock.patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_create_general_dev_succeed21(self, stb, utb, gtb):

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = mock.MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "18972752-f0f4-4cf7-b185-971ff6539d21",
                "owner": "compute:DC01_KVM02_ZONE02"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "faa923cc-3bfc-44d1-a66a-31b75b5aad7a",
                "ip": "192.168.0.3",
                "mac": "fa:16:3e:5c:3f:c2"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }
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

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "18972752-f0f4-4cf7-b185-971ff6539d21",
                "owner": "compute:DC01_KVM02_ZONE02"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA2",
            "port": {
                "id": "faa923cc-3bfc-44d1-a66a-31b75b5aad7a",
                "ip": "192.168.0.3",
                "mac": "fa:16:3e:5c:3f:c2"
            },
            "resource_group_name": "OpenStack/DC/HA2",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

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

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "52",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
                "owner": "network:dhcp"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "519c51b8-9328-455a-8ae7-b204754eacea",
                "ip": "192.168.0.1",
                "mac": "fa:16:3e:76:ab:0e"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

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

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21": "device_id",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.3",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:5c:3f:c2",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_device_owner": "compute:DC01_KVM02_ZONE02",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
                "owner": "network:dhcp"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "519c51b8-9328-455a-8ae7-b204754eacea",
                "ip": "192.168.0.1",
                "mac": "fa:16:3e:76:ab:0e"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

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

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21": "device_id",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2": "GeneralDev",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.3",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:5c:3f:c2",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_device_owner": "compute:DC01_KVM02_ZONE02",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2_GD_VlanID": "53",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
                "owner": "network:dhcp"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "519c51b8-9328-455a-8ae7-b204754eacea",
                "ip": "192.168.0.1",
                "mac": "fa:16:3e:76:ab:0e"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }
        rc = self.agent.proxy_l2.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info)
        self.assertTrue(rc)
