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

import datetime

import mock
from neutron.tests import base
import requests

from networking_nec.nwa.nwalib import exceptions as nwa_exc
from networking_nec.nwa.nwalib import restclient


class TestRestClient(base.BaseTestCase):
    def setUp(self):
        super(TestRestClient, self).setUp()
        self.rcl = restclient.RestClient()

    def test__url(self):
        rcl = restclient.RestClient('127.0.0.2', 8081, True)
        path = '/path'
        u = rcl._url(path)
        self.assertEqual(u, 'https://127.0.0.2:8081' + path)

    @mock.patch('networking_nec.nwa.nwalib.restclient.utcnow')
    @mock.patch('requests.request')
    def test__send_receive(self, rr, utcnow):
        now_for_test = datetime.datetime(2016, 2, 24, 5, 23)
        now_string = 'Wed, 24 Feb 2016 05:23:00 GMT'
        utcnow.return_value = now_for_test
        myauth = mock.Mock()
        myauth.return_value = mock.sentinel.auth_val
        rcl = restclient.RestClient('127.0.0.3', 8083, True, myauth)
        rcl._send_receive('GET', '/path')
        rr.assert_called_once_with(
            'GET', 'https://127.0.0.3:8083/path',
            data=None,
            headers={'Authorization': mock.sentinel.auth_val,
                     'Content-Type': 'application/json',
                     'Date': now_string,
                     'X-UMF-API-Version': restclient.UMF_API_VERSION},
            verify=False,
            proxies={'no': 'pass'})
        myauth.assert_called_once_with(now_string, '/path')

    @mock.patch('requests.request')
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

    @mock.patch('requests.request')
    def test_rest_api_raise(self, rr):
        def myauth(a, b):
            pass

        rr.side_effect = OSError
        rcl = restclient.RestClient('127.0.0.3', 8083, True, myauth)
        body = {'a': 1}
        url = 'http://127.0.0.5:8085/path'
        self.assertRaises(
            OSError,
            rcl.rest_api, 'GET', url, body
        )

    @mock.patch('networking_nec.nwa.nwalib.restclient.RestClient.rest_api')
    def test_get(self, rarc):
        self.rcl.get('')
        self.assertEqual(rarc.call_count, 1)

    @mock.patch('networking_nec.nwa.nwalib.restclient.RestClient.rest_api')
    def test_post(self, rarc):
        self.rcl.post('')
        self.assertEqual(rarc.call_count, 1)

    @mock.patch('networking_nec.nwa.nwalib.restclient.RestClient.rest_api')
    def test_put(self, rarc):
        self.rcl.put('')
        self.assertEqual(rarc.call_count, 1)

    @mock.patch('networking_nec.nwa.nwalib.restclient.RestClient.rest_api')
    def test_delete(self, rarc):
        self.rcl.delete('')
        self.assertEqual(rarc.call_count, 1)
