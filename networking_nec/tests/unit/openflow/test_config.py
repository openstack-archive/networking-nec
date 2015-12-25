# Copyright 2012 NEC Corporation.  All rights reserved.
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

from neutron.tests import base
from oslo_config import cfg

from neutron.agent.common import config as agent_config

from networking_nec.plugins.openflow import config


class ConfigurationTest(base.BaseTestCase):

    def setUp(self):
        super(ConfigurationTest, self).setUp()
        # NOTE: I am not sure why register_agent_opts is already called
        # with a different *Opt object, but it causes register_*_opts to fail.
        # Resetting cfg.CONF to a fresh ConfigOpts helps us.
        # This test class tests the default value loaded by register_*_opts,
        # so I believe it is good to reset loaded options before the tests.
        self.patch(cfg, 'CONF', cfg.ConfigOpts())

    def test_defaults_plugin_opts(self):
        config.register_plugin_opts()

        self.assertEqual('127.0.0.1', cfg.CONF.OFC.host)
        self.assertEqual('8888', cfg.CONF.OFC.port)
        # Check path_prefix is an empty string explicitly.
        self.assertEqual('', cfg.CONF.OFC.path_prefix)
        self.assertEqual('trema', cfg.CONF.OFC.driver)
        self.assertTrue(cfg.CONF.OFC.enable_packet_filter)
        self.assertTrue(cfg.CONF.OFC.support_packet_filter_on_ofc_router)
        self.assertFalse(cfg.CONF.OFC.use_ssl)
        self.assertIsNone(cfg.CONF.OFC.key_file)
        self.assertIsNone(cfg.CONF.OFC.cert_file)

    def test_defaults_agent_opts(self):
        config.register_agent_opts()
        agent_config.register_root_helper(cfg.CONF)

        self.assertEqual('br-int', cfg.CONF.OVS.integration_bridge)
        self.assertEqual(2, cfg.CONF.AGENT.polling_interval)
        self.assertEqual('sudo', cfg.CONF.AGENT.root_helper)
