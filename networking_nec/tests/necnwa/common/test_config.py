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

# -*- mode: python; coding: utf-8 -*-
# GIT: $Id$
import logging
from neutron.tests import base

from networking_nec.plugins.necnwa.common import config as cfg

log_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s,%(msecs).03d - %(levelname)s - '

    '%H:%M:%S'
)
log_handler.setFormatter(formatter)
log_handler.setLevel(logging.INFO)
LOG = logging.getLogger()
LOG.addHandler(log_handler)
LOG.setLevel(logging.INFO)


class TestNWAConfig(base.BaseTestCase):

    def test_section_default_NWA_ServerURL(self):
        self.assertEqual(cfg.CONF.NWA.ServerURL, None)

    def test_section_default_NWA_AccessKeyId(self):
        self.assertEqual(cfg.CONF.NWA.AccessKeyId, None)

    def test_section_default_NWA_SecretAccessKey(self):
        self.assertEqual(cfg.CONF.NWA.SecretAccessKey, None)

    def test_section_default_NWA_ResourceGroupName(self):
        self.assertEqual(cfg.CONF.NWA.ResourceGroupName, None)

    def test_section_default_NWA_RegionName(self):
        self.assertEqual(cfg.CONF.NWA.RegionName, 'RegionOne')

    def test_section_default_NWA_ScenarioPollingTimer(self):
        self.assertEqual(cfg.CONF.NWA.ScenarioPollingTimer, 10)

    def test_section_default_NWA_ScenarioPollingCount(self):
        self.assertEqual(cfg.CONF.NWA.ScenarioPollingCount, 6)

    def test_section_default_NWA_IronicAZPrefix(self):
        self.assertEqual(cfg.CONF.NWA.IronicAZPrefix, 'BM_')

    def test_section_default_NWA_NwaDir(self):
        self.assertEqual(cfg.CONF.NWA.NwaDir, None)

    def test_section_default_NWA_PolicyFWDefault(self):
        self.assertEqual(cfg.CONF.NWA.PolicyFWDefault, False)

    def test_section_default_NWA_ResourceGroup(self):
        self.assertEqual(cfg.CONF.NWA.ResourceGroup, None)

    def test_section_default_NWA_PortMap(self):
        self.assertEqual(cfg.CONF.NWA.PortMap, None)
