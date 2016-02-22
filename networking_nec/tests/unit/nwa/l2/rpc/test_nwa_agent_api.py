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
from neutron.tests import base

from networking_nec.plugins.necnwa.l2.rpc import nwa_agent_api


class TestNECNWAAgentApi(base.BaseTestCase):

    @mock.patch('neutron.common.rpc.get_client')
    def setUp(self, f1):
        super(TestNECNWAAgentApi, self).setUp()
        self.proxy = nwa_agent_api.NECNWAAgentApi("dummy-topic")
        self.context = mock.MagicMock()

    def test_create_server(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.proxy.create_server(self.context, tenant_id)

    def test_delete_server(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.proxy.delete_server(self.context, tenant_id)

    def test_get_nwa_rpc_servers(self):
        self.proxy.get_nwa_rpc_servers(self.context)
