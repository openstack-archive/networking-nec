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

from networking_nec.plugins.necnwa.l2.rpc import nwa_agent_callback


class TestNECNWAAgentRpcCallback(base.BaseTestCase):

    def setUp(self):
        super(TestNECNWAAgentRpcCallback, self).setUp()
        self.context = mock.MagicMock()
        self.agent = mock.MagicMock()
        self.callback = nwa_agent_callback.NwaAgentRpcCallback(
            self.context, self.agent
        )

    def test_get_nwa_rpc_server(self):
        rd = self.callback.get_nwa_rpc_servers(self.context, kwargs={})
        self.assertIsInstance(rd, dict)

    def test_create_server(self):
        params = {'tenant_id': 'T1'}
        rd = self.callback.create_server(self.context, kwargs=params)
        self.assertIsNotNone(rd)

    def test_delete_server(self):
        params = {'tenant_id': 'T1'}
        rd = self.callback.delete_server(self.context, kwargs=params)
        self.assertIsNotNone(rd)
