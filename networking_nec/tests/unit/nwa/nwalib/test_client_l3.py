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

import mock

from networking_nec.nwa.nwalib import workflow
from networking_nec.tests.unit.nwa.nwalib import test_client

TENANT_ID = 'OpenT9004'

# create tenant nw
DC_RESOURCE_GROUP_APP1 = 'OpenStack/DC1/Common/App1Grp/App1'


class TestNwaClientL3(test_client.TestNwaClientBase):

    def test_create_tenant_fw(self):
        vlan_devaddr = '10.0.0.254'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        rd, rj = self.nwa.l3.create_tenant_fw(
            TENANT_ID, DC_RESOURCE_GROUP_APP1,
            vlan_devaddr, vlan_name, vlan_type
        )
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('CreateTenantFW'),
            {'TenantID': TENANT_ID,
             'CreateNW_DeviceType1': 'TFW',
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_APP1,
             'CreateNW_Vlan_DeviceAddress1': vlan_devaddr,
             'CreateNW_VlanLogicalName1': vlan_name,
             'CreateNW_VlanType1': vlan_type})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_update_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        rd, rj = self.nwa.l3.update_tenant_fw(
            TENANT_ID,
            device_name, mock.sentinel.vlan_devaddr,
            vlan_name, vlan_type, 'connect'
        )
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('UpdateTenantFW'),
            {'TenantID': TENANT_ID,
             'ReconfigNW_DeviceName1': device_name,
             'ReconfigNW_DeviceType1': device_type,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_Vlan_DeviceAddress1': mock.sentinel.vlan_devaddr,
             'ReconfigNW_VlanType1': vlan_type,
             'ReconfigNW_Vlan_ConnectDevice1': 'connect'})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_update_tenant_fw_without_connect(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        rd, rj = self.nwa.l3.update_tenant_fw(
            TENANT_ID,
            device_name, mock.sentinel.vlan_devaddr,
            vlan_name, vlan_type
        )
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('UpdateTenantFW'),
            {'TenantID': TENANT_ID,
             'ReconfigNW_DeviceName1': device_name,
             'ReconfigNW_DeviceType1': device_type,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_Vlan_DeviceAddress1': mock.sentinel.vlan_devaddr,
             'ReconfigNW_VlanType1': vlan_type})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_delete_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        rd, rj = self.nwa.l3.delete_tenant_fw(
            TENANT_ID,
            device_name, device_type,
        )
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('DeleteTenantFW'),
            {'TenantID': TENANT_ID,
             'DeleteNW_DeviceName1': device_name,
             'DeleteNW_DeviceType1': device_type})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_setting_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        rd, rj = self.nwa.l3.setting_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('SettingNAT'),
            {'TenantID': TENANT_ID,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_VlanType1': vlan_type,
             'ReconfigNW_DeviceType1': 'TFW',
             'ReconfigNW_DeviceName1': fw_name,
             'LocalIP': local_ip,
             'GlobalIP': global_ip})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_delete_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'

        rd, rj = self.nwa.l3.delete_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )

        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('DeleteNAT'),
            {'TenantID': TENANT_ID,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type,
             'DeleteNW_DeviceType1': 'TFW',
             'DeleteNW_DeviceName1': fw_name,
             'LocalIP': local_ip,
             'GlobalIP': global_ip})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_update_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        rd, rj = self.nwa.l3.update_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )

        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 2)
