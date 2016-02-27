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

from networking_nec.tests.unit.nwa.nwalib import test_client

TENANT_ID = 'OpenT9004'

# create tenant nw
DC_RESOURCE_GROUP_APP1 = 'OpenStack/DC1/Common/App1Grp/App1'


class TestNwaClient(test_client.TestNwaClientBase):

    def test_delete_nat(self):
        vlan_name = 'LNW_BusinessVLAN_100'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.5'
        global_ip = '10.0.1.5'
        fw_name = 'TFW77'
        rd, rj = self.nwa.l3.delete_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_setting_nat(self):
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.6'
        global_ip = '10.0.1.6'
        fw_name = 'TFW78'
        rd, rj = self.nwa.l3.setting_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_update_tenant_fw(self):
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        vlan_devaddr = '192.168.6.254'
        fw_name = 'TFW79'
        rd, rj = self.nwa.l3.update_tenant_fw(
            TENANT_ID,
            fw_name, vlan_devaddr,
            vlan_name, vlan_type
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)


class TestUtNwaClient(test_client.TestUtNwaClientBase):
    '''Unit test for NwaClient '''

    def test_create_tenant_fw(self):
        vlan_devaddr = '10.0.0.254'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        self.nwa.l3.create_tenant_fw(
            self.tenant_id, DC_RESOURCE_GROUP_APP1,
            vlan_devaddr, vlan_name, vlan_type
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'CreateTenantFW',
            {'TenantID': self.tenant_id,
             'CreateNW_DeviceType1': 'TFW',
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_APP1,
             'CreateNW_Vlan_DeviceAddress1': vlan_devaddr,
             'CreateNW_VlanLogicalName1': vlan_name,
             'CreateNW_VlanType1': vlan_type})

    def test_update_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        self.nwa.l3.update_tenant_fw(
            self.tenant_id,
            device_name, mock.sentinel.vlan_devaddr,
            vlan_name, vlan_type, 'connect'
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'UpdateTenantFW',
            {'TenantID': self.tenant_id,
             'ReconfigNW_DeviceName1': device_name,
             'ReconfigNW_DeviceType1': device_type,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_Vlan_DeviceAddress1': mock.sentinel.vlan_devaddr,
             'ReconfigNW_VlanType1': vlan_type,
             'ReconfigNW_Vlan_ConnectDevice1': 'connect'})

    def test_delete_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        self.nwa.l3.delete_tenant_fw(
            self.tenant_id,
            device_name, device_type,
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'DeleteTenantFW',
            {'TenantID': self.tenant_id,
             'DeleteNW_DeviceName1': device_name,
             'DeleteNW_DeviceType1': device_type})

    def test_setting_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        self.nwa.l3.setting_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'SettingNAT',
            {'TenantID': self.tenant_id,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_VlanType1': vlan_type,
             'ReconfigNW_DeviceType1': 'TFW',
             'ReconfigNW_DeviceName1': fw_name,
             'LocalIP': local_ip,
             'GlobalIP': global_ip})

    def test_delete_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'

        self.nwa.l3.delete_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )

        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'DeleteNAT',
            {'TenantID': self.tenant_id,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type,
             'DeleteNW_DeviceType1': 'TFW',
             'DeleteNW_DeviceName1': fw_name,
             'LocalIP': local_ip,
             'GlobalIP': global_ip})
