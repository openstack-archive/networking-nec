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

import unittest
from nose.tools import ok_, eq_
from neutron.plugins.necnwa.db.models import (
    NWATenantBinding,
    NWATenantBindingN
)


class TestNWATenantBinding(unittest.TestCase):
    def test_nwa_tenant_binding(self):
        ntb = NWATenantBinding('T1', 'NWA-T1', {'key': 'value'})
        ok_(ntb is not None)
        eq_(str(ntb), "<TenantState(T1,NWA-T1,{'key': 'value'})>")


class TestNWATenantBindingN(unittest.TestCase):
    def test_nwa_tenant_binding(self):
        ntbn = NWATenantBindingN('T1', 'NWA-T1', 'key', 'value')
        ok_(ntbn is not None)
        eq_(str(ntbn), "<TenantState(T1,NWA-T1,{'key': 'value'})>")
