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

from networking_nec.tests.necnwa.agent import test_nwa_agent


class TestAgentProxyTenant(test_nwa_agent.TestNECNWANeutronAgentBase):

    def test__create_tenant_succeed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'

        self.nwacli.create_tenant.return_value = 200, {}

        rcode, body = self.agent.proxy_tenant.create_tenant(
            self.context,
            nwa_tenant_id=nwa_tenant_id
        )

        self.assertTrue(rcode)
        self.assertIsInstance(body, dict)

    def test__create_tenant_failed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        self.nwacli.create_tenant.return_value = 400, {}
        rcode, body = self.agent.proxy_tenant.create_tenant(
            self.context,
            nwa_tenant_id=nwa_tenant_id
        )
        self.assertTrue(rcode)
        self.assertIsInstance(body, dict)

    def test__delete_tenant(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        result, nwa_data = self.agent.proxy_tenant.delete_tenant(
            self.context,
            nwa_tenant_id=nwa_tenant_id
        )

        self.assertTrue(result)
        self.assertIsInstance(nwa_data, dict)

    def test__delete_tenant_failed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        self.nwacli.delete_tenant.return_value = 500, dict()
        result, nwa_data = self.agent.proxy_tenant.delete_tenant(
            self.context,
            nwa_tenant_id=nwa_tenant_id
        )
        self.assertIsInstance(nwa_data, dict)
        self.assertTrue(result)

    def test__update_tenant_binding_true(self):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d',
        nwa_data = dict()
        self.agent.proxy_tenant.update_tenant_binding(
            context,
            tenant_id,
            nwa_tenant_id,
            nwa_data,
            True
        )

    def test__update_tenant_binding_false(self):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d',
        nwa_data = dict()
        self.agent.proxy_tenant.update_tenant_binding(
            context,
            tenant_id,
            nwa_tenant_id,
            nwa_data,
            False
        )
