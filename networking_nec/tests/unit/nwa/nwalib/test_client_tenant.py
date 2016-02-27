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

import mock

from networking_nec.tests.unit.nwa.nwalib import test_client

TENANT_ID = 'OpenT9004'
DC_RESOURCE_GROUP_POD1 = 'OpenStack/DC1/Common/Pod1Grp/Pod1'
DC_RESOURCE_GROUP_APP1 = 'OpenStack/DC1/Common/App1Grp/App1'


class TestNwaClientTenant(test_client.TestNwaClientBase):

    def test_create_tenant(self):
        rd, rj = self.nwa.tenant.create_tenant(TENANT_ID)
        self.post.assert_called_once_with(
            '/umf/tenant/%s' % TENANT_ID,
            {'TenantName': TENANT_ID})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def _test_delete_tenant(self, status_code, sem_delete_tenant_called):
        with mock.patch('networking_nec.nwa.nwalib.restclient.'
                        'RestClient.delete') as mock_delete, \
            mock.patch('networking_nec.nwa.nwalib.semaphore.'
                       'Semaphore.delete_tenant_semaphore') as mock_sem_del:
            mock_delete.return_value = (status_code, mock.sentinel.data)
            rd, rj = self.nwa.tenant.delete_tenant(TENANT_ID)

        mock_delete.assert_called_once_with('/umf/tenant/%s' % TENANT_ID)
        if sem_delete_tenant_called:
            mock_sem_del.assert_called_once_with(TENANT_ID)
        else:
            self.assertEqual(0, mock_sem_del.call_count)
        self.assertEqual(rd, status_code)
        self.assertEqual(mock.sentinel.data, rj)
        self.assertEqual(0, self.post.call_count)
        self.assertEqual(1, mock_delete.call_count)

    def test_delete_tenant(self):
        self._test_delete_tenant(200, sem_delete_tenant_called=True)

    def test_delete_tenant_non_200(self):
        self._test_delete_tenant(500, sem_delete_tenant_called=False)
