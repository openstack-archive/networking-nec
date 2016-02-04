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

from networking_nec.plugins.necnwa.l3 import utils as nwa_l3_utils
from networking_nec.tests.necnwa.l2 import test_utils


class TestL3Utils(test_utils.TestNwa):

    def test_add_router_interface_by_port(self):
        context = mock.MagicMock()
        router_id = mock.MagicMock()
        interface_info = {'port_id': '0a08ca7b-51fb-4d0b-8483-e93bb6d47bda'}

        plugin = mock.MagicMock()
        plugin._core_plugin = mock.MagicMock()
        proxy = mock.MagicMock()
        create_tenant_fw = mock.MagicMock()
        proxy.create_tenant_fw = create_tenant_fw
        plugin._core_plugin.get_nwa_proxy = mock.MagicMock(return_value=proxy)

        nwa_l3_utils.add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertEqual(create_tenant_fw.call_count, 1)

        create_tenant_fw.reset_mock()
        plugin._core_plugin.get_nwa_proxy.side_effect = Exception
        nwa_l3_utils.add_router_interface_by_port(
            plugin, context, router_id, interface_info
        )
        self.assertEqual(create_tenant_fw.call_count, 0)
