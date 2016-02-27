# Copyright 2016 NEC Corporation.  All rights reserved.
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

from oslo_log import log as logging

from networking_nec._i18n import _LE


LOG = logging.getLogger(__name__)


class NwaClientL3(object):

    def __init__(self, client):
        self.client = client

    # --- Tenant FW ---

    def create_tenant_fw(self, tenant_id, dc_resource_group_name,
                         vlan_devaddr, vlan_logical_name,
                         vlan_type='BusinessVLAN', router_id=None):
        body = {
            'CreateNW_DeviceType1': 'TFW',
            'TenantID': tenant_id,
            'CreateNW_Vlan_DeviceAddress1': vlan_devaddr,
            'CreateNW_VlanLogicalName1': vlan_logical_name,
            'CreateNW_VlanType1': vlan_type,
            'CreateNW_DCResourceGroupName': dc_resource_group_name
        }
        return self.client.call_workflow(
            tenant_id, self.client.post, 'CreateTenantFW', body)

    def update_tenant_fw(self, tenant_id, device_name, vlan_devaddr,
                         vlan_logical_name, vlan_type,
                         connect=None, router_id=None):
        body = {
            'ReconfigNW_DeviceName1': device_name,
            'ReconfigNW_DeviceType1': 'TFW',
            'ReconfigNW_Vlan_DeviceAddress1': vlan_devaddr,
            'ReconfigNW_VlanLogicalName1': vlan_logical_name,
            'ReconfigNW_VlanType1': vlan_type,
            'TenantID': tenant_id
        }
        if connect:
            body['ReconfigNW_Vlan_ConnectDevice1'] = connect

        return self.client.call_workflow(
            tenant_id, self.client.post, 'UpdateTenantFW', body)

    def delete_tenant_fw(self, tenant_id, device_name, device_type,
                         router_id=None):
        body = {
            'DeleteNW_DeviceName1': device_name,
            'DeleteNW_DeviceType1': device_type,
            'TenantID': tenant_id
        }
        return self.client.call_workflow(
            tenant_id, self.client.post, 'DeleteTenantFW', body)

    # --- Nat ---

    def setting_nat(self, tenant_id, vlan_logical_name, vlan_type,
                    local_ip, global_ip, dev_name, data=None, router_id=None):
        body = {
            'ReconfigNW_DeviceName1': dev_name,
            'ReconfigNW_DeviceType1': 'TFW',
            'ReconfigNW_VlanLogicalName1': vlan_logical_name,
            'ReconfigNW_VlanType1': vlan_type,
            'LocalIP': local_ip,
            'GlobalIP': global_ip,
            'TenantID': tenant_id,
        }
        return self.client.call_workflow(
            tenant_id, self.client.post, 'SettingNAT', body)

    def delete_nat(self, tenant_id, vlan_logical_name, vlan_type,
                   local_ip, global_ip, dev_name, data=None, router_id=None):
        body = {
            'DeleteNW_DeviceName1': dev_name,
            'DeleteNW_DeviceType1': 'TFW',
            'DeleteNW_VlanLogicalName1': vlan_logical_name,
            'DeleteNW_VlanType1': vlan_type,
            'LocalIP': local_ip,
            'GlobalIP': global_ip,
            'TenantID': tenant_id,
        }
        return self.client.call_workflow(
            tenant_id, self.client.post, 'DeleteNAT', body)

    def update_nat(self, tenant_id, vlan_logical_name, vlan_type,
                   local_ip, global_ip, dev_name, data=None, router_id=None):
        try:
            http_status, rj = self.delete_nat(tenant_id,
                                              vlan_logical_name, vlan_type,
                                              local_ip, global_ip, dev_name,
                                              data=data)
        except Exception as e:
            LOG.exception(_LE('%s'), e)
            http_status = -1
            rj = None

        self.setting_nat(tenant_id, vlan_logical_name, vlan_type,
                         local_ip, global_ip, dev_name,
                         data=data, router_id=router_id)

        return http_status, rj
