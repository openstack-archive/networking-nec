# Copyright 2015 NEC Corporation
# All Rights Reserved.
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
#

import os

from oslo_config import cfg

import neutron
from neutron.tests.unit.db import test_db_base_plugin_v2 as test_db_plugin
from neutron.tests.unit import testlib_api


class NeutronDbPluginV2TestCase(test_db_plugin.NeutronDbPluginV2TestCase):
    pass


class SqlTestCase(testlib_api.SqlTestCase):
    pass
