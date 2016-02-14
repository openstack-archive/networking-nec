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

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class NwaL3ProxyApi(object):

    def __init__(self, client):
        self.client = client

    def create_tenant_fw(self, context, tenant_id, nwa_tenant_id, nwa_info):
        cctxt = self.client.prepare()
        return cctxt.cast(
            context,
            'create_tenant_fw',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    def delete_tenant_fw(self, context, tenant_id, nwa_tenant_id, nwa_info):
        cctxt = self.client.prepare()
        return cctxt.cast(
            context,
            'delete_tenant_fw',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    def setting_nat(self, context, tenant_id, nwa_tenant_id, floating):
        cctxt = self.client.prepare()
        return cctxt.cast(
            context,
            'setting_nat',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            floating=floating
        )

    def delete_nat(self, context, tenant_id, nwa_tenant_id, floating):
        cctxt = self.client.prepare()
        return cctxt.cast(
            context,
            'delete_nat',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            floating=floating
        )
