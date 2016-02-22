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

from mock import patch
from neutron.tests import base
import requests

from networking_nec.plugins.necnwa.nwalib import exceptions as nwa_exc
from networking_nec.plugins.necnwa.nwalib import restclient


class TestRestClient(base.BaseTestCase):
    def setUp(self):
        super(TestRestClient, self).setUp()
        self.rcl = restclient.RestClient()

    def test__init_default(self):
        kwargs = {}
        url = 'http://127.0.0.1:8080'
        auth = 'auth'
        self.rcl._init_default(kwargs, url, auth)
        self.assertEqual(kwargs['host'], '127.0.0.1')
        self.assertEqual(kwargs['port'], 8080)
        self.assertFalse(kwargs['use_ssl'])
        self.assertEqual(kwargs['auth'], auth)

        url = 'https://127.0.0.1:8080'
        self.rcl._init_default(kwargs, url, auth)
        self.assertTrue(kwargs['use_ssl'])

    def test_url(self):
        rcl = restclient.RestClient('127.0.0.2', 8081, True)
        path = '/path'
        u = rcl.url(path)
        self.assertEqual(u, 'https://127.0.0.2:8081' + path)

    def test__make_headers(self):
        pass

    @patch('requests.request')
    def test__send_receive(self, rr):
        def myauth(a, b):
            pass

        rcl = restclient.RestClient('127.0.0.3', 8083, True, myauth)
        rcl._send_receive('GET', '/path')
        self.assertEqual(rr.call_count, 1)

    @patch('requests.request')
    def test_rest_api(self, rr):
        def myauth(a, b):
            pass

        rcl = restclient.RestClient('127.0.0.4', 8084, True, myauth)
        body = {}
        url = 'http://127.0.0.4:8084/path'
        rr.side_effect = requests.exceptions.RequestException
        self.assertRaises(
            nwa_exc.NwaException,
            rcl.rest_api, 'GET', url, body
        )

    def test___report_workflow_error(self):
        self.rcl._report_workflow_error(None, 0)

    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.'
           'rest_api')
    def test_rest_api_return_check(self, ra):
        body = {'a': 1}
        url = 'http://127.0.0.5:8085/path'
        ra.return_value = (200, None)
        hst, rd = self.rcl.rest_api_return_check('GET', url, body)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

        failed = {
            'status': 'FAILED', 'progress': '100'
        }
        ra.return_value = (200, failed)
        self.rcl.post_data = url, body
        hst, rd = self.rcl.rest_api_return_check('GET', url, body)
        self.assertEqual(hst, 200)
        self.assertEqual(rd, failed)

        ra.side_effect = nwa_exc.NwaException(200, 'msg1', None)
        hst, rd = self.rcl.rest_api_return_check('GET', url, body)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

    @patch('requests.request')
    def test_rest_api_return_check_raise(self, rr):
        def myauth(a, b):
            pass

        rr.side_effect = OSError
        rcl = restclient.RestClient('127.0.0.3', 8083, True, myauth)
        body = {'a': 1}
        url = 'http://127.0.0.5:8085/path'
        self.assertRaises(
            OSError,
            rcl.rest_api_return_check, 'GET', url, body
        )

    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.'
           'rest_api_return_check')
    def test_get(self, rarc):
        self.rcl.get('')
        self.assertEqual(rarc.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.'
           'rest_api_return_check')
    def test_post(self, rarc):
        self.rcl.post('')
        self.assertEqual(rarc.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.'
           'rest_api_return_check')
    def test_put(self, rarc):
        self.rcl.put('')
        self.assertEqual(rarc.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.'
           'rest_api_return_check')
    def test_delete(self, rarc):
        self.rcl.delete('')
        self.assertEqual(rarc.call_count, 1)
