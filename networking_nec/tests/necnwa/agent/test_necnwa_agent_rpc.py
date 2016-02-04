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

from mock import MagicMock
from mock import patch
import os

from neutron.tests import base
from oslo_log import log as logging

from networking_nec.plugins.necnwa.agent.necnwa_agent_rpc import NECNWAAgentApi
from networking_nec.plugins.necnwa.agent.necnwa_agent_rpc import NECNWAProxyApi

LOG = logging.getLogger(__name__)
ROOTDIR = '/'
ETCDIR = os.path.join(ROOTDIR, 'etc/neutron')


class TestNECNWAAgentApi(base.BaseTestCase):

    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1):
        super(TestNECNWAAgentApi, self).setUp()
        self.proxy = NECNWAAgentApi("dummy-topic")
        self.context = MagicMock()

    def test_create_server(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.proxy.create_server(self.context, tenant_id)

    def test_delete_server(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.proxy.delete_server(self.context, tenant_id)

    def test_get_nwa_rpc_servers(self):
        self.proxy.get_nwa_rpc_servers(self.context)


class TestNECNWAProxyApi(base.BaseTestCase):

    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1):
        super(TestNECNWAProxyApi, self).setUp()
        self.proxy = NECNWAProxyApi("dummy-topic", "dummy-tenant-id")
        self.context = MagicMock()

    def test__send_msg_true(self):
        msg = MagicMock()
        blocking = True
        self.proxy._send_msg(self.context, msg, blocking)

    def test__send_msg_false(self):
        msg = MagicMock()
        blocking = False
        self.proxy._send_msg(self.context, msg, blocking)

    def test_create_general_dev(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        nwa_info = dict()
        self.proxy.create_general_dev(self.context, tenant_id, nwa_tenant_id,
                                      nwa_info)

    def test_delete_general_dev(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        nwa_info = dict()
        self.proxy.delete_general_dev(self.context, tenant_id, nwa_tenant_id,
                                      nwa_info)
