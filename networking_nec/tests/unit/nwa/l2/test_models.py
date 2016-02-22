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

from neutron.tests import base

from networking_nec.nwa.l2 import models


class TestNWATenantKeyValue(base.BaseTestCase):
    def test_nwa_tenant_key_value(self):
        ntkv = models.NWATenantKeyValue('T1', 'NWA-T1', 'key', 'value')
        self.assertIsNotNone(ntkv)
        self.assertEqual(str(ntkv),
                         "<TenantKeyValue(T1,NWA-T1,{'key': 'value'})>")


class TestNWATenantQueue(base.BaseTestCase):
    def test_nwa_tenant_queue(self):
        ntq = models.NWATenantQueue('T1', 'NWA-T1', 'topic-1')
        self.assertIsNotNone(ntq)
        self.assertEqual(str(ntq),
                         "<TenantQueue(T1,NWA-T1,topic-1)>")
