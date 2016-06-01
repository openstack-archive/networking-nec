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

from networking_nec.nwa.nwalib import semaphore as nwa_sem


class NwaClientTenant(object):

    def __init__(self, client):
        self.client = client

    def create_tenant(self, tenant_id):
        body = {
            'TenantName': tenant_id,
        }
        return self.client.post('/umf/tenant/' + tenant_id, body)

    def delete_tenant(self, tenant_id):
        status_code, data = self.client.delete('/umf/tenant/' + tenant_id)
        if status_code == 200:
            nwa_sem.Semaphore.delete_tenant_semaphore(tenant_id)
        return status_code, data
