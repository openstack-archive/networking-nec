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
from neutron.tests import base

from networking_nec.nwa.l2.rpc import nwa_l2_server_api


class TestNwaL2ServerApi(base.BaseTestCase):

    @mock.patch('neutron.common.rpc.get_client')
    def setUp(self, f1):
        super(TestNwaL2ServerApi, self).setUp()
        self.proxy = nwa_l2_server_api.NwaL2ServerRpcApi("dummy-topic")
        self.context = mock.MagicMock()

    def test_release_dynamic_segment_from_agent(self):
        cctxt = mock.MagicMock()
        self.proxy.client.prepare.return_value = cctxt
        self.proxy.release_dynamic_segment_from_agent(
            self.context, 'physical_network', 'network_id')
        self.assertEqual(1, cctxt.call.call_count)
