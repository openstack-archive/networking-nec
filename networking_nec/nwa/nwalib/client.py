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

from networking_nec.nwa.nwalib import client_l2
from networking_nec.nwa.nwalib import client_l3
from networking_nec.nwa.nwalib import client_tenant
from networking_nec.nwa.nwalib import nwa_restclient
from networking_nec.nwa.nwalib import semaphore as nwa_sem


LOG = logging.getLogger(__name__)


class NwaClient(nwa_restclient.NwaRestClient):
    '''Client class of NWA. '''

    pool = eventlet.GreenPool()

    def __init__(self, *args, **kwargs):
        super(NwaClient, self).__init__(*args, **kwargs)

        self.tenant = client_tenant.NwaClientTenant(self)
        self.l2 = client_l2.NwaClientL2(self)
        self.l3 = client_l3.NwaClientL3(self)

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
            tenant_id, self.post, 'SettingFWPolicy', body)

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
            tenant_id, self.post, 'CreateTenantLB', body)

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
            tenant_id, self.post, 'UpdateTenantLB', body)

    def delete_tenant_lb(self, tenant_id, device_name):
        body = {
            'DeleteNW_DeviceName1': device_name,
            'DeleteNW_DeviceType1': 'LB',
            'TenantID': tenant_id,
        }
        return self.call_workflow(
            tenant_id, self.post, 'DeleteTenantLB', body)

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
            tenant_id, self.post, 'SettingLBPolicy', body)


def send_queue_is_not_empty():
    return nwa_sem.Semaphore.any_locked()
