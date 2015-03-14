# Copyright 2014 NEC Corporation.  All rights reserved.
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
from sqlalchemy.orm import exc as sa_exc

from neutron.common import constants
from neutron import manager
from neutron.tests import base

from networking_nec.plugins.openflow import utils
from networking_nec.tests.unit.openflow import test_plugin


class NecUtilsTest(base.BaseTestCase):

    def test_cmp_dpid(self):
        self.assertTrue(utils.cmp_dpid('0xabcd', '0xabcd'))
        self.assertTrue(utils.cmp_dpid('abcd', '0xabcd'))
        self.assertTrue(utils.cmp_dpid('0x000000000000abcd', '0xabcd'))
        self.assertTrue(utils.cmp_dpid('0x000000000000abcd', '0x00abcd'))
        self.assertFalse(utils.cmp_dpid('0x000000000000abcd', '0xabc0'))
        self.assertFalse(utils.cmp_dpid('0x000000000000abcd', '0x00abc0'))

    def test_cmp_dpid_with_exception(self):
        self.assertFalse(utils.cmp_dpid('0xabcx', '0xabcx'))
        self.assertFalse(utils.cmp_dpid(None, None))


class TestUtilsDbTest(test_plugin.NecPluginV2TestCase):

    def test_update_resource(self):
        with self.network() as network:
            self.assertEqual("ACTIVE", network['network']['status'])
            net_id = network['network']['id']
            for status in ["DOWN", "BUILD", "ERROR", "ACTIVE"]:
                utils.update_resource_status(
                    self.context, 'network', net_id,
                    getattr(constants, 'NET_STATUS_%s' % status))
                n = self.plugin._get_network(self.context, net_id)
                self.assertEqual(status, n.status)

    def _test_update_resource_with_exception(self, exc=None,
                                             ignore_error=False,
                                             exc_expexted=True):
        def _call_method():
            utils.update_resource_status(
                self.context, 'network', net_id, "DOWN", ignore_error)

        with self.network() as network:
            self.assertEqual("ACTIVE", network['network']['status'])
            net_id = network['network']['id']
            plugin = manager.NeutronManager.get_plugin()
            exc = exc or Exception
            with mock.patch.object(plugin, '_get_network', side_effect=exc):
                if exc_expexted:
                    self.assertRaises(exc, _call_method)
                else:
                    _call_method()
            n = self.plugin._get_network(self.context, net_id)
            # Check the status is unchanged.
            self.assertEqual("ACTIVE", n.status)

    def test_update_resource_with_staledata_error_ignore_error(self):
        self._test_update_resource_with_exception(sa_exc.StaleDataError,
                                                  ignore_error=True,
                                                  exc_expexted=False)

    def test_update_resource_with_staledata_error(self):
        self._test_update_resource_with_exception(sa_exc.StaleDataError,
                                                  ignore_error=False)

    def test_update_resource_with_general_exception_with_ignore_error(self):
        self._test_update_resource_with_exception(ignore_error=True)

    def test_update_resource_with_general_exception(self):
        self._test_update_resource_with_exception(ignore_error=False)
