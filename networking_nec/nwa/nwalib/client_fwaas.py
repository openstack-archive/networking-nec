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

from debtcollector import removals


class NwaClientFWaaS(object):

    def __init__(self, client):
        self.client = client

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
        return self.client.call_workflow(
            tenant_id, self.client.post, 'SettingFWPolicy', body)
