# Copyright (c) 2013 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
from oslo_config import cfg

from neutron import manager
from neutron.tests.unit import test_extension_extraroute as test_ext_route

from networking_nec.tests import base
from networking_nec.tests.unit.openflow import test_plugin


class NecRouterL3AgentTestCase(test_ext_route.ExtraRouteDBIntTestCase):

    _plugin_name = test_plugin.PLUGIN_NAME

    def setUp(self):
        base.override_nvalues()
        mock.patch(test_plugin.OFC_MANAGER).start()
        super(NecRouterL3AgentTestCase, self).setUp(self._plugin_name)

        plugin = manager.NeutronManager.get_plugin()
        plugin.network_scheduler = None
        plugin.router_scheduler = None

    def test_floatingip_with_invalid_create_port(self):
        self._test_floatingip_with_invalid_create_port(self._plugin_name)


class NecRouterOpenFlowTestCase(NecRouterL3AgentTestCase):

    def setUp(self):
        cfg.CONF.set_override('default_router_provider',
                              'openflow', 'PROVIDER')
        super(NecRouterOpenFlowTestCase, self).setUp()

    def test_router_add_gateway_no_subnet(self):
        self.skipTest('Need investigation to support IPv6 router. '
                      'See blueprint ipv6-router in Neutorn.')
