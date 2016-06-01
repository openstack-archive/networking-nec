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

from networking_nec.nwa.nwalib import workflow
from networking_nec.tests.unit.nwa.nwalib import test_client

TENANT_ID = 'OpenT9004'


class TestNwaClientFWaaS(test_client.TestNwaClientBase):

    def test_setting_fw_policy(self):
        fw_name = 'TFW8'
        props = {'properties': [1]}
        rd, rj = self.nwa.fwaas.setting_fw_policy_async(
            TENANT_ID, fw_name, props
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('SettingFWPolicy'),
            {'TenantID': TENANT_ID,
             'DCResourceType': 'TFW_Policy',
             'DCResourceOperation': 'Setting',
             'DeviceInfo': {'Type': 'TFW', 'DeviceName': fw_name},
             'Property': props})
