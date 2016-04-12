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

from networking_nec.nwa.l2.rpc import nwa_l2_server_callback


class TestNwaL2ServerRpcCallback(base.BaseTestCase):

    def setUp(self):
        super(TestNwaL2ServerRpcCallback, self).setUp()
        self.callback = nwa_l2_server_callback.NwaL2ServerRpcCallback()
        self.context = mock.MagicMock()

    @mock.patch('neutron.db.api.get_session')
    @mock.patch('neutron.plugins.ml2.db.get_dynamic_segment')
    @mock.patch('neutron.plugins.ml2.db.delete_network_segment')
    def test_release_dynamic_segment_from_agent(self, dns, gds, gs):
        del_segment = {'segmentation_id': 0, 'id': 'ID-0'}
        gds.return_value = del_segment
        self.callback.release_dynamic_segment_from_agent(
            self.context,
            network_id='network-id',
            physical_network='physical-network')
        self.assertEqual(0, dns.call_count)

        dns.reset_mock()
        del_segment = {'segmentation_id': 4000, 'id': 'ID-4000'}
        gds.return_value = del_segment
        self.callback.release_dynamic_segment_from_agent(
            self.context,
            network_id='network-id',
            physical_network='physical-network')
        self.assertEqual(1, dns.call_count)
