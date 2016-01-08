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

from mock import patch, MagicMock  # noqa
from neutron.tests import base

import logging
import os


from networking_nec.plugins.necnwa.agent.necnwa_agent_rpc import (  # noqa
    NECNWAAgentApi,
    NECNWAProxyApi
)
# from networking_nec.plugins.necnwa.nwalib import client as nwa_cli

log_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s,%(msecs).03d - %(levelname)s - '
    '%(filename)s:%(lineno)d - %(message)s',
    '%H:%M:%S'
)

log_handler.setFormatter(formatter)
log_handler.setLevel(logging.INFO)

LOG = logging.getLogger()
LOG.addHandler(log_handler)
LOG.setLevel(logging.INFO)

context = MagicMock()

ROOTDIR = '/'
ETCDIR = os.path.join(ROOTDIR, 'etc/neutron')


class TestNECNWAAgentApi(base.BaseTestCase):

    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1):
        super(TestNECNWAAgentApi, self).setUp()
        self.proxy = NECNWAAgentApi("dummy-topic")

    def test_create_server(self):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.proxy.create_server(context, tenant_id)

    def test_delete_server(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.proxy.delete_server(context, tenant_id)

    def test_get_nwa_rpc_servers(self):
        self.proxy.get_nwa_rpc_servers(context)


class TestNECNWAProxyApi(base.BaseTestCase):

    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1):
        super(TestNECNWAProxyApi, self).setUp()
        self.proxy = NECNWAProxyApi("dummy-topic", "dummy-tenant-id")

    def test__send_msg_true(self):
        context = MagicMock()
        msg = MagicMock()
        blocking = True
        self.proxy._send_msg(context, msg, blocking)

    def test__send_msg_false(self):
        context = MagicMock()
        msg = MagicMock()
        blocking = False
        self.proxy._send_msg(context, msg, blocking)

    # def test_get_tenant_queue(self):
    #     context = MagicMock()
    #     self.proxy.get_tenant_queue(context)

    def test_create_tenant_fw(self):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        nwa_info = dict()
        self.proxy.create_tenant_fw(context, tenant_id, nwa_tenant_id,
                                    nwa_info)

    def test_delete_tenant_fw(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        nwa_info = dict()
        self.proxy.delete_tenant_fw(context, tenant_id, nwa_tenant_id,
                                    nwa_info)

    def test_create_general_dev(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        nwa_info = dict()
        self.proxy.create_general_dev(context, tenant_id, nwa_tenant_id,
                                      nwa_info)

    def test_delete_general_dev(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        nwa_info = dict()
        self.proxy.delete_general_dev(context, tenant_id, nwa_tenant_id,
                                      nwa_info)

    def test_setting_nat(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        floating = dict()
        self.proxy.setting_nat(context, tenant_id, nwa_tenant_id, floating)

    def test_delete_nat(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        floating = dict()
        self.proxy.delete_nat(context, tenant_id, nwa_tenant_id, floating)
