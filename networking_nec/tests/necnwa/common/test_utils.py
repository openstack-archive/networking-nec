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

from networking_nec.plugins.necnwa.common import utils as nwa_com_utils


class TestCommonUtils(base.BaseTestCase):

    def test_get_tenant_info(self):

        class network_context(object):
            network = mock.MagicMock()
            current = mock.MagicMock()
            _plugin = mock.MagicMock()
            _plugin_context = mock.MagicMock()

        context = network_context()
        context.network.current = {}
        context.network.current['tenant_id'] = 'T1'
        context.network.current['name'] = 'PublicVLAN_100'
        context.network.current['id'] = 'Uuid-PublicVLAN_100'

        tid, nid = nwa_com_utils.get_tenant_info(context)
        self.assertEqual(tid, 'T1')
        self.assertEqual(nid, 'RegionOneT1')
