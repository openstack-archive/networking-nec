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

from neutron.tests import base
from oslo_config import cfg

# It is required to register nwa options
from networking_nec.nwa.common import config  # noqa


class TestNWAConfig(base.BaseTestCase):

    def test_section_default_NWA_server_url(self):
        self.assertIsNone(cfg.CONF.NWA.server_url)

    def test_section_default_NWA_access_key_id(self):
        self.assertIsNone(cfg.CONF.NWA.access_key_id)

    def test_section_default_NWA_secret_access_key(self):
        self.assertIsNone(cfg.CONF.NWA.secret_access_key)

    def test_section_default_NWA_resource_group_name(self):
        self.assertIsNone(cfg.CONF.NWA.resource_group_name)

    def test_section_default_NWA_region_name(self):
        self.assertEqual(cfg.CONF.NWA.region_name, 'RegionOne')

    def test_section_default_NWA_scenario_polling_timer(self):
        self.assertEqual(cfg.CONF.NWA.scenario_polling_timer, 10)

    def test_section_default_NWA_scenario_polling_count(self):
        self.assertEqual(cfg.CONF.NWA.scenario_polling_count, 6)

    def test_section_default_NWA_use_necnwa_router(self):
        self.assertIsInstance(cfg.CONF.NWA.use_necnwa_router, bool)
        self.assertTrue(cfg.CONF.NWA.use_necnwa_router)

    def test_section_default_NWA_use_neutron_vlan_id(self):
        self.assertIsInstance(cfg.CONF.NWA.use_neutron_vlan_id, bool)
        self.assertFalse(cfg.CONF.NWA.use_neutron_vlan_id)

    def test_section_default_NWA_ironic_az_prefix(self):
        self.assertEqual(cfg.CONF.NWA.ironic_az_prefix, 'BM_')

    def test_section_default_NWA_use_setting_fw_policy(self):
        self.assertFalse(cfg.CONF.NWA.use_setting_fw_policy)

    def test_section_default_NWA_resource_group(self):
        self.assertIsNone(cfg.CONF.NWA.resource_group)

    def test_section_default_NWA_resource_group_file(self):
        self.assertIsNone(cfg.CONF.NWA.resource_group_file)
