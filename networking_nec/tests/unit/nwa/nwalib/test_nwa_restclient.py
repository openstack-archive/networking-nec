# Copyright 2016 NEC Corporation.  All rights reserved.
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

from networking_nec.nwa.nwalib import exceptions as nwa_exc
from networking_nec.nwa.nwalib import nwa_restclient


class TestNwaRestClient(base.BaseTestCase):

    def test_get_client_with_host_port(self):
        client = nwa_restclient.NwaRestClient('127.0.0.1', 8080, True)
        self.assertEqual('127.0.0.1', client.host)
        self.assertEqual(8080, client.port)
        self.assertIs(True, client.use_ssl)

    def test_get_client_with_url(self):
        cfg.CONF.set_override('server_url', 'http://127.0.0.1:8888',
                              group='NWA')
        client = nwa_restclient.NwaRestClient()
        self.assertEqual('127.0.0.1', client.host)
        self.assertEqual(8888, client.port)
        self.assertIs(False, client.use_ssl)

    def test_get_client_with_url_with_https(self):
        cfg.CONF.set_override('server_url', 'https://192.168.1.1:8080',
                              group='NWA')
        client = nwa_restclient.NwaRestClient()
        self.assertEqual('192.168.1.1', client.host)
        self.assertEqual(8080, client.port)
        self.assertIs(True, client.use_ssl)

    def test_get_client_with_no_parameter(self):
        self.assertRaises(cfg.Error, nwa_restclient.NwaRestClient)

    def test_get_client_auth_function(self):
        cfg.CONF.set_override('access_key_id',
                              '5g2ZMAdMwZ1gQqZagNqbJSrlopQUAUHILcP2nmxVs28=',
                              group='NWA')
        cfg.CONF.set_override('secret_access_key',
                              'JE35Lup5CvI68lneFS4EtSGCh1DnG8dBtTRycPQ83QA=',
                              group='NWA')
        client = nwa_restclient.NwaRestClient('127.0.0.1', 8080, True)
        self.assertEqual(
            client.auth(
                'Wed, 11 Feb 2015 17:24:51 GMT',
                '/umf/tenant/DC1'
            ),
            b'SharedKeyLite 5g2ZMAdMwZ1gQqZagNqbJSrlopQUAUHILcP2nmxVs28='
            b':mNd/AZJdMawfhJpVUT/lQcH7fPMz+4AocKti1jD1lCI='
        )

    def test_get_client_auth_function_with_parameters(self):
        client = nwa_restclient.NwaRestClient('127.0.0.1', 8080, True,
                                              access_key_id='user',
                                              secret_access_key='password')
        self.assertEqual(
            client.auth(
                'Wed, 11 Feb 2015 17:24:51 GMT',
                '/umf/tenant/DC1'
            ),
            b'SharedKeyLite user:d7ym8ADuKFoIphXojb1a36lvMb5KZK7fPYKz7RlDcpw='
        )

    @mock.patch('networking_nec.nwa.nwalib.restclient.RestClient.rest_api')
    def test_rest_api_return_check(self, ra):
        client = nwa_restclient.NwaRestClient('127.0.0.5', 8085, False)

        body = {'a': 1}
        url = '/path'
        ra.return_value = (200, None)
        hst, rd = client.rest_api('GET', url, body)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

        failed = {
            'status': 'FAILED', 'progress': '100'
        }
        ra.return_value = (200, failed)
        client.post_data = url, body
        hst, rd = client.rest_api('GET', url, body)
        self.assertEqual(hst, 200)
        self.assertEqual(rd, failed)

        ra.side_effect = nwa_exc.NwaException(200, 'msg1', None)
        hst, rd = client.rest_api('GET', url, body)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

    @mock.patch('requests.request')
    def test_rest_api_raise(self, rr):
        def myauth(a, b):
            pass

        rr.side_effect = OSError
        rcl = nwa_restclient.NwaRestClient('127.0.0.3', 8083, True, myauth)
        body = {'a': 1}
        url = 'http://127.0.0.5:8085/path'
        self.assertRaises(
            OSError,
            rcl.rest_api, 'GET', url, body
        )
