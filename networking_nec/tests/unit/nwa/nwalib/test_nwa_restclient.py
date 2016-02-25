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

TENANT_ID = 'OpenT9004'


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


class TestNwaRestClientWorkflow(base.BaseTestCase):

    def setUp(self):
        super(TestNwaRestClientWorkflow, self).setUp()
        host = '127.0.0.1'
        port = '12081'
        access_key_id = 'PzGIIoLbL7ttHFkDHqLguFz/7+VsVJbDmV0iLWAkJ0g='
        secret_access_key = 'nbvX65iujFoYomXTKROF9GKUN6L2rAM/sI+cvNdW7sw='

        self.nwa = nwa_restclient.NwaRestClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key
        )
        self.nwa.workflow_first_wait = 0

    def test_get_client_workflow_parameters(self):
        cfg.CONF.set_override('scenario_polling_first_timer', 1, group='NWA')
        cfg.CONF.set_override('scenario_polling_timer', 2, group='NWA')
        cfg.CONF.set_override('scenario_polling_count', 3, group='NWA')
        nwa_client = nwa_restclient.NwaRestClient('127.0.0.1', 8080, True)
        self.assertEqual(1, nwa_client.workflow_first_wait)
        self.assertEqual(2, nwa_client.workflow_wait_sleep)
        self.assertEqual(3, nwa_client.workflow_retry_count)

    def test_workflow_kick_and_wait_raise(self):
        call_ne = mock.MagicMock(
            side_effect=nwa_exc.NwaException(200, 'm1', None))
        call_ne.__name__ = 'POST'
        self.assertRaises(
            nwa_exc.NwaException,
            self.nwa.workflow_kick_and_wait, call_ne, None, None
        )

    @mock.patch('eventlet.semaphore.Semaphore.locked')
    @mock.patch('networking_nec.nwa.nwalib.nwa_restclient.NwaRestClient.'
                'workflowinstance')
    def test_workflow_kick_and_wait(self, wki, lock):
        call = mock.MagicMock()
        call.__name__ = 'POST'
        call.return_value = 200, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

        call.return_value = 200, {'executionid': 1}
        wki.return_value = 201, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 201)
        self.assertIsNone(rd)

        call.return_value = 200, {'executionid': '1'}
        wki.return_value = 202, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 202)
        self.assertIsNone(rd)

        wki.return_value = 201, {'status': 'RUNNING'}
        self.nwa.workflow_retry_count = 1
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 201)
        self.assertIsNone(rd)

        wki.side_effect = Exception
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

    @mock.patch('eventlet.semaphore.Semaphore.locked')
    @mock.patch('networking_nec.nwa.nwalib.nwa_restclient.NwaRestClient.'
                'workflow_kick_and_wait')
    @mock.patch('networking_nec.nwa.nwalib.workflow.NwaWorkflow._nameid',
                new_callable=mock.PropertyMock)
    def test_call_workflow(self, nameid, wkaw, lock):
        call = mock.MagicMock()
        call.__name__ = 'POST'

        wkaw.return_value = 200, '0'
        nameid.return_value = {'name_0': 'url_0'}
        hst, rd = self.nwa.call_workflow('0', call, 'name_0', 'body_0')
        self.assertEqual(hst, 200)
        self.assertEqual(rd, '0')

        wkaw.return_value = 201, '1'
        nameid.return_value = {'name_1': 'url_1'}
        hst, rd = self.nwa.call_workflow('1', call, 'name_1', 'body_1')
        self.assertEqual(hst, 201)
        self.assertEqual(rd, '1')

    def test_get_reserved_dc_resource(self):
        self.nwa.get_reserved_dc_resource(TENANT_ID)

    def test_get_tenant_resource(self):
        self.nwa.get_tenant_resource(TENANT_ID)

    def test_get_dc_resource_groups(self):
        self.nwa.get_dc_resource_groups('OpenStack/DC1/Common/Pod2Grp/Pod2')

    @mock.patch('networking_nec.nwa.nwalib.nwa_restclient.NwaRestClient.get')
    def test_get_workflow_list(self, get):
        get.return_value = 209, None
        hst, rd = self.nwa.get_workflow_list()
        self.assertEqual(hst, 209)
        self.assertIsNone(rd)

        get.side_effect = Exception
        hst, rd = self.nwa.get_workflow_list()
        self.assertIsNone(hst)
        self.assertIsNone(rd)

    def test_stop_workflowinstance(self):
        self.nwa.stop_workflowinstance('id-0')

    def test_update_workflow_list(self):
        self.nwa.update_workflow_list()

    def test_wait_workflow_done(self):
        self.nwa.wait_workflow_done(mock.MagicMock())
