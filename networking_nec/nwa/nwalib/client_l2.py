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

from networking_nec._i18n import _LW


LOG = logging.getLogger(__name__)


class NwaClientL2(object):

    def __init__(self, client):
        self.client = client

    # --- Tenant Network ---

    def create_tenant_nw(self, tenant_id, dc_resource_group_name):
        body = {
            "TenantID": tenant_id,
            "CreateNW_DCResourceGroupName": dc_resource_group_name,
            'CreateNW_OperationType': 'CreateTenantNW'
        }
        return self.client.call_workflow(
            tenant_id, self.client.post, 'CreateTenantNW', body
        )

    def delete_tenant_nw(self, tenant_id):
        body = {
            "TenantID": tenant_id,
        }
        return self.client.call_workflow(
            tenant_id, self.client.post, 'DeleteTenantNW', body
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
        return self.client.call_workflow(
            tenant_id, self.client.post, 'CreateVLAN', body
        )

    def delete_vlan(self, tenant_id, logical_name, vlan_type='BusinessVLAN'):
        body = {
            'TenantID': tenant_id,
            'DeleteNW_VlanLogicalName1': logical_name,
            'DeleteNW_VlanType1': vlan_type
        }
        return self.client.call_workflow(
            tenant_id, self.client.post, 'DeleteVLAN', body
        )

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
        return self.client.call_workflow(
            tenant_id, self.client.post, 'CreateGeneralDev', body
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
        return self.client.call_workflow(
            tenant_id, self.client.post, 'DeleteGeneralDev', body
        )
