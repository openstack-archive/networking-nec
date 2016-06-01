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
from oslo_config import cfg
from oslo_serialization import jsonutils

from networking_nec.nwa.common import utils as nwa_com_utils


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

    def _test_load_json_from_file_from_file(self, json_str=None):
        json_data = {'foo': 'bar'}
        json_file = self.get_temp_file_path('test.json')
        with open(json_file, 'w') as f:
            f.write(jsonutils.dumps(json_data))
        ret = nwa_com_utils.load_json_from_file('test', json_file,
                                                json_str, [])
        self.assertEqual(json_data, ret)

    def test_load_json_from_file_from_file(self):
        self._test_load_json_from_file_from_file()

    def test_load_json_from_file_from_str(self):
        json_data = {'foo': 'bar'}
        json_str = jsonutils.dumps(json_data)
        ret = nwa_com_utils.load_json_from_file('test', None, json_str, [])
        self.assertEqual(json_data, ret)

    def test_load_json_from_file_both_specified(self):
        # json_file has priority. json_str passed here is not evaluated.
        self._test_load_json_from_file_from_file(json_str='invalid')

    def test_load_json_from_file_no_json_file_abspath(self):
        json_file = 'test.json'
        self.assertRaises(cfg.Error,
                          nwa_com_utils.load_json_from_file,
                          'test', json_file, None, [])

    def test_load_json_from_file_with_invalid_json_file(self):
        json_file = self.get_temp_file_path('test.json')
        with open(json_file, 'w') as f:
            f.write('invalid json data')
        self.assertRaises(cfg.Error,
                          nwa_com_utils.load_json_from_file,
                          'test', json_file, None, [])

    def test_load_json_from_file_with_invalid_json_str(self):
        self.assertRaises(cfg.Error,
                          nwa_com_utils.load_json_from_file,
                          'test', None, 'invalid json str', [])

    def test_load_json_from_file_default_value(self):
        self.assertEqual(
            'test_data',
            nwa_com_utils.load_json_from_file('test', None, None, 'test_data'))
