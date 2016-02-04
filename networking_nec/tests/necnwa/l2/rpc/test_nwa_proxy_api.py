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

from networking_nec.plugins.necnwa.l2.rpc import nwa_proxy_api


class TestNECNWAProxyApi(base.BaseTestCase):

    @mock.patch('neutron.common.rpc.get_client')
    def setUp(self, f1):
        super(TestNECNWAProxyApi, self).setUp()
        self.proxy = nwa_proxy_api.NECNWAProxyApi("dummy-topic",
                                                  "dummy-tenant-id")
        self.context = mock.MagicMock()

    def test__send_msg_true(self):
        msg = mock.MagicMock()
        blocking = True
        self.proxy._send_msg(self.context, msg, blocking)

    def test__send_msg_false(self):
        msg = mock.MagicMock()
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
