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

from networking_nec.nwa.common import exceptions as nwa_exc
from networking_nec.tests.unit.nwa.agent import base


class TestAgentProxyTenant(base.TestNWAAgentBase):

    def test__create_tenant_succeed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'

        self.nwacli.tenant.create_tenant.return_value = 200, {}

        body = self.agent.proxy_tenant.create_tenant(
            mock.sentinel.context,
            nwa_tenant_id=nwa_tenant_id
        )
        exp_data = {
            'CreateTenant': True,
            'NWA_tenant_id': 'DC1_844eb55f21e84a289e9c22098d387e5d'
        }
        self.assertEqual(exp_data, body)

    def test__create_tenant_already_exists(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        self.nwacli.tenant.create_tenant.return_value = 500, {}
        body = self.agent.proxy_tenant.create_tenant(
            mock.sentinel.context,
            nwa_tenant_id=nwa_tenant_id
        )
        exp_data = {
            'CreateTenant': True,
            'NWA_tenant_id': 'DC1_844eb55f21e84a289e9c22098d387e5d'
        }
        self.assertEqual(exp_data, body)

    def test__create_tenant_failed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        self.nwacli.tenant.create_tenant.return_value = 400, {}
        e = self.assertRaises(
            nwa_exc.AgentProxyException,
            self.agent.proxy_tenant.create_tenant,
            mock.sentinel.context,
            nwa_tenant_id=nwa_tenant_id
        )
        self.assertEqual(400, e.value)

    def test__delete_tenant(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_data = self.agent.proxy_tenant.delete_tenant(
            mock.sentinel.context,
            nwa_tenant_id=nwa_tenant_id
        )
        self.assertIsInstance(nwa_data, dict)
        exp_data = {
            'resultdata': {'LogicalNWName': 'LNW_BusinessVLAN_4000',
                           'TenantFWName': 'T1',
                           'VlanID': '4000'},
            'status': 'SUCCEED'}
        self.assertDictEqual(exp_data, nwa_data)

    def test__delete_tenant_failed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        self.nwacli.tenant.delete_tenant.return_value = 500, {}
        nwa_data = self.agent.proxy_tenant.delete_tenant(
            mock.sentinel.context,
            nwa_tenant_id=nwa_tenant_id
        )
        self.assertDictEqual({}, nwa_data)

    def test__update_tenant_binding_true(self):
        context = mock.MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d',
        nwa_data = {}
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
        nwa_data = {}
        self.agent.proxy_tenant.update_tenant_binding(
            context,
            tenant_id,
            nwa_tenant_id,
            nwa_data,
            False
        )
