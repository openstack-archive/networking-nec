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

import re

from debtcollector import removals
import eventlet
from oslo_log import log as logging

from networking_nec._i18n import _LW, _LE
from networking_nec.nwa.nwalib import nwa_restclient
from networking_nec.nwa.nwalib import semaphore as nwa_sem
from networking_nec.nwa.nwalib import workflow


LOG = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class NwaClient(nwa_restclient.NwaRestClient):
    '''Client class of NWA. '''

    pool = eventlet.GreenPool()

    def __init__(self, *args, **kwargs):
        super(NwaClient, self).__init__(*args, **kwargs)

    # --- Tenant Network ---

    def create_tenant_nw(self, tenant_id, dc_resource_group_name):
        body = {
            "TenantID": tenant_id,
            "CreateNW_DCResourceGroupName": dc_resource_group_name,
            'CreateNW_OperationType': 'CreateTenantNW'
        }
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('CreateTenantNW'), body
        )

    def delete_tenant_nw(self, tenant_id):
        body = {
            "TenantID": tenant_id,
        }
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('DeleteTenantNW'), body
        )

    # --- VLan ---

    def create_vlan(self, tenant_id, ipaddr, mask,
                    vlan_type='BusinessVLAN', openstack_network_id=None):
        body = {
            'TenantID': tenant_id,
            'CreateNW_VlanType1': vlan_type,
            'CreateNW_IPSubnetAddress1': ipaddr,
            'CreateNW_IPSubnetMask1': mask
        }
        if openstack_network_id:
            body['CreateNW_VlanLogicalID1'] = openstack_network_id
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('CreateVLAN'), body
        )

    def delete_vlan(self, tenant_id, logical_name, vlan_type='BusinessVLAN'):
        body = {
            'TenantID': tenant_id,
            'DeleteNW_VlanLogicalName1': logical_name,
            'DeleteNW_VlanType1': vlan_type
        }
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('DeleteVLAN'), body
        )

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
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('CreateTenantFW'), body)

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

        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('UpdateTenantFW'), body)

    def delete_tenant_fw(self, tenant_id, device_name, device_type,
                         router_id=None):
        body = {
            'DeleteNW_DeviceName1': device_name,
            'DeleteNW_DeviceType1': device_type,
            'TenantID': tenant_id
        }
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('DeleteTenantFW'), body)

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
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('SettingNAT'), body)

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
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('DeleteNAT'), body)

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

    # --- FWaaS ---

    @removals.remove(
        message='It is no longer async. Use setting_fw_policy instead.')
    def setting_fw_policy_async(self, tenant_id, fw_name, props):
        return self.setting_fw_policy(tenant_id, fw_name, props)

    def setting_fw_policy(self, tenant_id, fw_name, props):
        body = {
            'TenantID': tenant_id,
            'DCResourceType': 'TFW_Policy',
            'DCResourceOperation': 'Setting',
            'DeviceInfo': {
                'Type': 'TFW',
                'DeviceName': fw_name,
            },
            'Property': props
        }
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('SettingFWPolicy'), body)

    # --- LBaaS ---

    def create_tenant_lb(self, tenant_id,
                         dc_resource_group_name,
                         vlan_logical_name, vlan_type, vif_ipaddr):
        body = {
            'CreateNW_DeviceType1': 'LB',
            'TenantID': tenant_id,
            'CreateNW_Vlan_DeviceAddress1': vif_ipaddr,
            'CreateNW_VlanLogicalName1': vlan_logical_name,
            'CreateNW_VlanType1': vlan_type,
            'CreateNW_DCResourceGroupName': dc_resource_group_name
        }
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('CreateTenantLB'), body)

    def update_tenant_lbn(self, tenant_id,
                          device_name, actions):
        body = {
            'ReconfigNW_DeviceName1': device_name,
            'ReconfigNW_DeviceType1': 'LB',
            'TenantID': tenant_id
        }
        for n, a in enumerate(actions):
            i = str(n + 1)
            if a[0] is not None:
                body['ReconfigNW_Vlan_ConnectDevice' + i] = a[0]
            lwn = a[1]
            body['ReconfigNW_VlanLogicalName' + i] = lwn
            if len(a) > 2:
                body['ReconfigNW_Vlan_DeviceAddress' + i] = a[2]
            if len(a) > 3:
                body['ReconfigNW_VlanType' + i] = a[3]
            else:
                if re.search(lwn, '_PublicVLAN_'):
                    body['ReconfigNW_VlanType' + i] = 'PublicVLAN'
                else:
                    body['ReconfigNW_VlanType' + i] = 'BusinessVLAN'

        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('UpdateTenantLB'), body)

    def delete_tenant_lb(self, tenant_id, device_name):
        body = {
            'DeleteNW_DeviceName1': device_name,
            'DeleteNW_DeviceType1': 'LB',
            'TenantID': tenant_id,
        }
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('DeleteTenantLB'), body)

    def setting_lb_policy(self, tenant_id, lb_name, props):
        body = {
            'TenantID': tenant_id,
            'DCResourceType': 'LB_Policy',
            'DCResourceOperation': 'Setting',
            'DeviceInfo': {
                'Type': 'LB',
                'DeviceName': lb_name,
            },
            'Property': props
        }
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('SettingLBPolicy'), body)

    # --- General Dev ---

    def create_general_dev(self, tenant_id, dc_resource_group_name,
                           logical_name, vlan_type='BusinessVLAN',
                           port_type=None, openstack_network_id=None):
        body = {
            'CreateNW_DeviceType1': 'GeneralDev',
            'TenantID': tenant_id,
            'CreateNW_VlanLogicalName1': logical_name,
            'CreateNW_VlanType1': vlan_type,
            'CreateNW_DCResourceGroupName': dc_resource_group_name
        }
        if logical_name and openstack_network_id:
            LOG.warning(_LW('VLAN logical name and id to be specified '
                            'in the exclusive.'))
        if openstack_network_id:
            body['CreateNW_VlanLogicalID1'] = openstack_network_id
        if port_type:
            body['CreateNW_PortType1'] = port_type
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('CreateGeneralDev'), body
        )

    def delete_general_dev(self, tenant_id, dc_resource_group_name,
                           logical_name, vlan_type='BusinessVLAN',
                           port_type=None, openstack_network_id=None):
        body = {
            'DeleteNW_DeviceType1': 'GeneralDev',
            'TenantID': tenant_id,
            'DeleteNW_VlanLogicalName1': logical_name,
            'DeleteNW_VlanType1': vlan_type,
            'DeleteNW_DCResourceGroupName': dc_resource_group_name
        }
        if logical_name and openstack_network_id:
            LOG.warning(_LW('VLAN logical name and id to be specified '
                            'in the exclusive.'))
        if openstack_network_id:
            body['DeleteNW_VlanLogicalID1'] = openstack_network_id
        if port_type:
            body['DeleteNW_PortType1'] = port_type
        return self.call_workflow(
            tenant_id,
            self.post, workflow.NwaWorkflow.path('DeleteGeneralDev'), body
        )

    # --- sync api ---

    def create_tenant(self, tenant_id):
        body = {
            'TenantName': tenant_id,
        }
        return self.post('/umf/tenant/' + tenant_id, body)

    def delete_tenant(self, tenant_id):
        status_code, data = self.delete('/umf/tenant/' + tenant_id)
        if status_code == 200:
            nwa_sem.Semaphore.delete_tenant_semaphore(tenant_id)
        return status_code, data


def send_queue_is_not_empty():
    return nwa_sem.Semaphore.any_locked()
