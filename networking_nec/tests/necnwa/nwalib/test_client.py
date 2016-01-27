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

import logging
from mock import MagicMock
from mock import patch
import os
import requests

from neutron.tests import base

from networking_nec.plugins.necnwa.common.config import cfg
from networking_nec.plugins.necnwa.nwalib import client
from networking_nec.plugins.necnwa.nwalib import exceptions as nwa_exc
from networking_nec.plugins.necnwa.nwalib import restclient
from networking_nec.plugins.necnwa.nwalib import semaphore as nwa_sem
from networking_nec.plugins.necnwa.nwalib import workflow

LOG = logging.getLogger()

TENANT_ID = 'OpenT9004'
CONTEXT = MagicMock()

# create general dev
DC_RESOURCE_GROUP_POD1 = 'OpenStack/DC1/Common/Pod1Grp/Pod1'
DC_RESOURCE_GROUP_POD2 = 'OpenStack/DC1/Common/Pod2Grp/Pod2'

# create tenant nw
DC_RESOURCE_GROUP_APP1 = 'OpenStack/DC1/Common/App1Grp/App1'

RESULTS = {}

CONFIG_FILE_CONTENTS = """
#
[OpenStack]
NeutronDBid = neutron
NeutronDBpw = password
NeutronDBtable = neutron

[NWA]
server_url = http://127.0.0.1:12081
access_key_id = 5g2ZMAdMwZ1gQqZagNqbJSrlopQUAUHILcP2nmxVs28=
secret_access_key = JE35Lup5CvI68lneFS4EtSGCh1DnG8dBtTRycPQ83QA=
resource_group_name = OpenStack/DC1/Common/App1Grp/App1
scenario_polling_timer =5
resource_group = [
   {
       "physical_network": "physnet1",
       "device_owner":"compute:None",
       "ResourceGroupName":"OpenStack/DC1/Common/Pod1Grp/Pod1"
   },
   {
       "physical_network": "physnet1",
       "device_owner":"network:dhcp",
       "ResourceGroupNliame":"OpenStack/DC1/Common/Pod1Grp/Pod1"
   },
   {
       "physical_network": "physnet2",
       "device_owner":"network:dhcp",
       "ResourceGroupName":"OpenStack/DC1/Common/Pod2Grp/Pod2"
   },
   {
       "physical_network": "physnet1",
       "device_owner":"compute:AZ1",
       "ResourceGroupName":"OpenStack/DC1/Common/Pod1Grp/Pod1"
   },
   {
       "physical_network": "physnet2",
       "device_owner":"compute:AZ2",
       "ResourceGroupName":"OpenStack/DC1/Common/Pod2Grp/Pod2"
   },
   {
       "physical_network": "physnet3",
       "device_owner":"network:router_gateway",
       "ResourceGroupName":"OpenStack/DC1/Common/App1"
   },
   {
       "physical_network": "physnet3",
       "device_owner":"network:router_interface",
       "ResourceGroupName":"OpenStack/DC1/Common/App1"
   },
   {
       "physical_network":"",
       "device_owner":"Stopper",
       "ResourceGroupName":"Stopper"
   }]
"""

DEFAULT_NAMEID = {
    'CreateTenantNW': '40030001',
    'DeleteTenantNW': '40030016',
    'CreateVLAN': '40030002',
    'DeleteVLAN': '40030018',
    'CreateGeneralDev': '40030021',
    'DeleteGeneralDev': '40030022',
    'CreateTenantFW': '40030019',
    'UpdateTenantFW': '40030009',
    'DeleteTenantFW': '40030020',
    'SettingNAT': '40030005',
    'DeleteNAT': '40030011',
    'SettingFWPolicy': '40030081',
    'SettingLBPolicy': '40030091',
    'CreateTenantLB': '40030092',
    'UpdateTenantLB': '40030093',
    'DeleteTenantLB': '40030094',
}


def ok1(ctx, http_status, rj, *args, **kwargs):
    RESULTS['success'] = {
        'context': ctx,
        'http_status': http_status,
        'result': rj
    }


def ng1(ctx, http_status, rj, *args, **kwargs):
    RESULTS['failure'] = {
        'context': ctx,
        'http_status': http_status,
        'result': rj
    }
    if kwargs.get('exception', None):
        RESULTS['failure']['exception'] = kwargs['exception']


def init_async():
    RESULTS = {}                          # noqa


class TestNwaException(base.BaseTestCase):
    def test___str__(self):
        exc = nwa_exc.NwaException(200, 'msg1', MagicMock())
        self.assertEqual(str(exc), 'http status: 200, msg1')


class TestNwaWorkflow(base.BaseTestCase):
    def test_strerror(self):
        em = workflow.NwaWorkflow.strerror('1')
        self.assertEqual(em, 'Unknown parent node')
        em = workflow.NwaWorkflow.strerror('299')
        self.assertEqual(em, 'Unknown error')

    def test_get_errno_from_resultdata(self):
        geterrno = workflow.NwaWorkflow.get_errno_from_resultdata
        rc = geterrno({})
        self.assertIsNone(rc)

        rc = geterrno({
            'resultdata': {}
        })
        self.assertIsNone(rc)

        rc = geterrno({
            'resultdata': {
                'ErrorMessage': ''
            }
        })
        self.assertIsNone(rc)

        rc = geterrno({
            'resultdata': {
                'ErrorMessage': 'ErrorNumber=100'
            }
        })
        self.assertEqual(rc, '100')

        rc = geterrno({
            'resultdata': {
                'ErrorMessage': 'ReservationErrorCode = 101'
            }
        })
        self.assertEqual(rc, '101')

    @patch('networking_nec.plugins.necnwa.nwalib.workflow.'
           'NwaWorkflow._nameid', DEFAULT_NAMEID)
    def test_update_nameid(self):
        with patch('networking_nec.plugins.necnwa.nwalib.workflow.'
                   'NwaWorkflow._nameid_initialized', True):
            workflow.NwaWorkflow.update_nameid(None)  # no error

        with patch('networking_nec.plugins.necnwa.nwalib.workflow.'
                   'NwaWorkflow._nameid_initialized', False):
            workflow.NwaWorkflow.update_nameid([1])
            self.assertTrue(workflow.NwaWorkflow._nameid_initialized)


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


class TestThread(base.BaseTestCase):
    def test_stop(self):
        t1 = nwa_sem.Thread(MagicMock())
        t1.stop()
        self.assertTrue(True)

    def test_wait(self):
        t1 = nwa_sem.Thread(MagicMock())
        t1.wait()
        self.assertTrue(True)


class TestSemaphore(base.BaseTestCase):
    def test_get_tenant_semaphore(self):
        sem1 = nwa_sem.Semaphore.get_tenant_semaphore('T1')
        sem2 = nwa_sem.Semaphore.get_tenant_semaphore('T1')
        self.assertEqual(sem1, sem2)

        sem3 = nwa_sem.Semaphore.get_tenant_semaphore('T2')
        self.assertTrue(sem1 != sem3)

        nwa_sem.Semaphore.delete_tenant_semaphore('T1')
        sem4 = nwa_sem.Semaphore.get_tenant_semaphore('T1')
        self.assertTrue(sem1 != sem4)

    def test_get_tenant_semaphore_raise1(self):
        self.assertRaises(
            TypeError,
            nwa_sem.Semaphore.get_tenant_semaphore, 0
        )

    def test_get_tenant_semaphore_raise2(self):
        self.assertRaises(
            TypeError,
            nwa_sem.Semaphore.get_tenant_semaphore, ''
        )

    def test_delete_tenant_semaphore(self):
        nwa_sem.Semaphore.delete_tenant_semaphore('T11')
        self.assertTrue(True)

    def test_any_locked(self):
        sem1 = nwa_sem.Semaphore.get_tenant_semaphore('T21')
        with sem1.sem:
            locked = nwa_sem.Semaphore.any_locked()
            self.assertTrue(locked)
        locked = nwa_sem.Semaphore.any_locked()
        self.assertFalse(locked)

    def check_push_history(self, param):
        t31 = nwa_sem.Semaphore.get_tenant_semaphore('T31')
        t31.push_history(
            param['call'],
            param['url'],
            param['body'],
            param['http_status'],
            param['rj']
        )
        r1, r2 = t31.search_history(
            param['search_call'],
            param['search_url'],
            param['search_body']
        )
        self.assertEqual(r1, param['search_result1'])
        self.assertEqual(r2, param['search_result2'])

    def test_push_history(self):
        post1 = MagicMock()
        post1.__name__ = 'post001'
        succeed = {'status': 'SUCCESS'}
        failed = {'status': 'FAILED'}
        test_params = [
            {
                'body': 'body001', 'search_body': 'body001',
                'http_status': 201, 'search_result1': 201,
                'rj': succeed, 'search_result2': succeed
            },
            {
                'body': 'body002', 'search_body': 'body002',
                'http_status': 202, 'search_result1': 202,
                'rj': succeed, 'search_result2': succeed
            },
            {
                'body': 'body003', 'search_body': 'body001',
                'http_status': 203, 'rj': succeed,
                'search_result1': 201,
                'search_result2': succeed
            },
            {
                'body': 'body004', 'search_body': 'body001',
                'http_status': 204, 'rj': succeed,
                'search_result1': None, 'search_result2': None
            },
            {
                'body': 'body005', 'search_body': 'body005',
                'http_status': 205, 'rj': failed,
                'search_result1': None, 'search_result2': None
            },
            {
                'body': 'body006', 'search_body': 'body004',
                'http_status': 206, 'rj': succeed,
                'search_result1': 204, 'search_result2': succeed
            },
            {
                'body': 'body006', 'search_body': 'body004',
                'http_status': 206, 'rj': succeed,
                'search_result1': 204, 'search_result2': succeed
            }
        ]
        for param in test_params:
            param['call'] = post1
            param['search_call'] = post1
            param['url'] = 'url001'
            param['search_url'] = 'url001'
            yield self.check_push_history, param


class TestNwaClient(base.BaseTestCase):
    '''Test code for Nwa Client '''

    def setUp(self):
        super(TestNwaClient, self).setUp()
        host = '127.0.0.1'
        port = '12081'
        access_key_id = 'PzGIIoLbL7ttHFkDHqLguFz/7+VsVJbDmV0iLWAkJ0g='
        secret_access_key = 'nbvX65iujFoYomXTKROF9GKUN6L2rAM/sI+cvNdW7sw='

        self.nwa = client.NwaClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key
        )
        self.nwa2 = client.NwaClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key
        )
        self.nwa.workflow_first_wait = 0.5
        self.nwa2.workflow_first_wait = 0.5

    def get_vlan_info(self):
        self.business_vlan = self.public_vlan = None
        self.business_vlan_name = self.public_vlan_name = None
        rj = self.nwa.get_reserved_dc_resource(TENANT_ID)
        for node in rj.get('GroupNode'):
            node_type = node.get('Type')
            if node_type == 'BusinessVLAN':
                self.business_vlan = node
                self.business_vlan_name = node['VLAN'][0]['LogicalName']
            elif node_type == 'PublicVLAN':
                self.public_vlan = node
                self.public_vlan_name = node['VLAN'][0]['LogicalName']
        # print json.dumps(self.business_vlan, indent=4, sort_keys=True)

    def test_workflow_kick_and_wait_raise(self):
        call_ne = MagicMock(side_effect=nwa_exc.NwaException(200, 'm1', None))
        call_ne.__name__ = 'POST'
        self.assertRaises(
            nwa_exc.NwaException,
            self.nwa.workflow_kick_and_wait, call_ne, None, None
        )

    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    def test_workflow_kick_and_wait(self, wki, lock):
        call = MagicMock()
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

    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflow_kick_and_wait')
    def test_call_workflow(self, wkaw, lock):
        call = MagicMock()
        call.__name__ = 'POST'

        def mkreq(tid, b, nocache=None):
            return call, 'url_' + str(tid), 'body_' + str(b)

        wkaw.return_value = 200, '0'
        hst, rd = self.nwa.call_workflow(mkreq, '0', '0')
        self.assertEqual(hst, 200)
        self.assertEqual(rd, '0')

        wkaw.return_value = 201, '1'
        hst, rd = self.nwa.call_workflow(mkreq, '1', '1')
        self.assertEqual(hst, 201)
        self.assertEqual(rd, '1')

        # 'nocache' in kwargs
        wkaw.return_value = 202, '2'
        hst, rd = self.nwa.call_workflow(mkreq, '2', '2', nocache=True)
        self.assertEqual(hst, 202)
        self.assertEqual(rd, '2')

        # 'nocache' is hook function
        wkaw.return_value = 203, '3'

        def hook(self, *args, **kwargs):
            self.assertEqual(args[0].__name__, 'POST')
            self.assertEqual(args[1], 'url_3')
            self.assertEqual(args[2], 'body_3')
            self.assertEqual(args[3], 203)
            self.assertEqual(args[4], '3')

        s = nwa_sem.Semaphore()
        s.hook = hook
        hst, rd = self.nwa.call_workflow(mkreq, '3', '3', nocache=s.hook)
        self.assertEqual(hst, 203)
        self.assertEqual(rd, '3')

    def test_get_reserved_dc_resource(self):
        self.nwa.get_reserved_dc_resource(TENANT_ID)
        self.assertTrue(True)

    def test_get_tenant_resource(self):
        self.nwa.get_tenant_resource(TENANT_ID)
        self.assertTrue(True)

    def test_get_dc_resource_groups(self):
        self.nwa.get_dc_resource_groups('OpenStack/DC1/Common/Pod2Grp/Pod2')
        self.assertTrue(True)

    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.get')
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
        self.assertTrue(True)

    def test_update_workflow_list(self):
        self.nwa.update_workflow_list()
        self.assertTrue(True)

    def test_wait_workflow_done(self):
        self.nwa.wait_workflow_done(MagicMock())
        self.assertTrue(True)

    def create_vlan(self):
        init_async()
        vlan_type = 'PublicVLAN'
        ipaddr = '172.16.0.0'
        mask = '28'
        rt = self.nwa.create_vlan(
            ok1, ng1, CONTEXT, TENANT_ID,
            vlan_type, ipaddr, mask
        )
        return rt

    def delete_nat(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_100'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.5'
        global_ip = '10.0.1.5'
        fw_name = 'TFW77'
        rt = self.nwa.delete_nat(
            ok1, ng1, CONTEXT, TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        return rt

    def setting_nat(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.6'
        global_ip = '10.0.1.6'
        fw_name = 'TFW78'
        rt = self.nwa.setting_nat(
            ok1, ng1, CONTEXT, TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        return rt

    def update_tenant_fw(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        vlan_devaddr = '192.168.6.254'
        fw_name = 'TFW79'
        rt = self.nwa.update_tenant_fw(
            ok1, ng1, CONTEXT, TENANT_ID,
            fw_name, vlan_devaddr,
            vlan_name, vlan_type
        )
        return rt

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.post')
    def test_delete_nat(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.delete_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.delete_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.delete_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.post')
    def test_setting_nat(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.setting_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.setting_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.setting_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.post')
    def test_update_tenant_fw(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.update_tenant_fw()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in428 history
        rd, rj = self.update_tenant_fw()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.update_tenant_fw()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.call_workflow')
    def test_setting_fw_policy(self, cawk):
        cawk.return_value = (200, {'status': 'SUCCESS'})
        props = {'Property': 1}
        fw_name = 'TFW8'
        rd, rj = self.nwa.setting_fw_policy(TENANT_ID, fw_name, props)
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')

        cawk.return_value = (500, None)
        rd, rj = self.nwa.setting_fw_policy(TENANT_ID, fw_name, props)
        self.assertEqual(rd, 500)

    def create_general_dev(self, vlan_name):
        init_async()
        dcresgrp_name = 'Common/App/Pod3'
        rd, rj = self.nwa.create_general_dev(
            ok1, ng1, CONTEXT, TENANT_ID,
            dcresgrp_name, vlan_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        return rd, rj

    def delete_general_dev(self, vlan_name):
        init_async()
        dcresgrp_name = 'Common/App/Pod3'
        rd, rj = self.nwa.delete_general_dev(
            ok1, ng1, CONTEXT, TENANT_ID,
            dcresgrp_name, vlan_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        return rd, rj

    def test_general_dev(self):
        params = [
            (5, ['dA', 'dB', 'dC', 'dD', 'dA']),
            (4, ['d1', 'd2', 'd3', 'd1']),
            (3, ['cA', 'dA', 'cA']),      # delete to "create"
            (3, ['c1', 'd2', 'c1']),      # don't delete if name is not same.
            (3, ['cB', 'dB', 'cC']),
            (4, ['cX', 'dX', 'cX', 'dX']),
            (6, ['c1', 'c2', 'd1', 'd2', 'c1', 'd1']),
            (4, ['cE', 'dE', 'dE', 'dE']),
        ]
        for count, vlan_names in params:
            yield self.check_general_dev, count, vlan_names

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.post')
    def check_general_dev(self, count, vlan_names, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        post.reset_mock()
        for vlan_name in vlan_names:
            name = vlan_name[1:]
            LOG.info(name)
            if vlan_name.startswith('c'):
                self.assertEqual(self.create_general_dev(name)[0], 200)
            else:
                self.assertEqual(self.delete_general_dev(name)[0], 200)
        self.assertEqual(post.call_count, count)


class TestUtNwaClient(base.BaseTestCase):
    '''Unit test for NwaClient '''

    def setUp(self):
        super(TestUtNwaClient, self).setUp()
        self.nwa = client.NwaClient(load_workflow_list=False)
        self.tenant_id = 'OpenT9004'

    def test__create_tenant_nw(self):
        method, url, body = self.nwa._create_tenant_nw(
            self.tenant_id,
            DC_RESOURCE_GROUP_APP1
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('CreateTenantNW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         DC_RESOURCE_GROUP_APP1)
        self.assertEqual(body['CreateNW_OperationType'], 'CreateTenantNW')

    def test__delete_tenant_nw(self):
        method, url, body = self.nwa._delete_tenant_nw(
            self.tenant_id
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteTenantNW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)

    def test__create_vlan(self):
        vlan_type = 'BusinessVLAN'
        ipaddr = '10.0.0.0'
        mask = 24
        open_nid = 'UUID'
        method, url, body = self.nwa._create_vlan(
            self.tenant_id, vlan_type, ipaddr, mask, open_nid
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('CreateVLAN'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_IPSubnetMask1'], mask)
        self.assertEqual(body['CreateNW_IPSubnetAddress1'], ipaddr)
        self.assertEqual(body['CreateNW_VlanType1'], vlan_type)
        self.assertEqual(body['CreateNW_VlanLogicalID1'], open_nid)

    def test__delete_vlan(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        method, url, body = self.nwa._delete_vlan(
            self.tenant_id, vlan_name, vlan_type
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteVLAN'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['DeleteNW_VlanType1'], vlan_type)

    def test__create_tenant_fw(self):
        vlan_devaddr = '10.0.0.254'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        method, url, body = self.nwa._create_tenant_fw(
            self.tenant_id, DC_RESOURCE_GROUP_APP1,
            vlan_devaddr, vlan_name, vlan_type
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('CreateTenantFW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         DC_RESOURCE_GROUP_APP1)
        self.assertEqual(body['CreateNW_Vlan_DeviceAddress1'], vlan_devaddr)
        self.assertEqual(body['CreateNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['CreateNW_VlanType1'], vlan_type)

    def test__update_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        method, url, body = self.nwa._update_tenant_fw(
            self.tenant_id,
            device_name, device_type,
            vlan_name, vlan_type, 'connect'
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('UpdateTenantFW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['ReconfigNW_DeviceName1'], device_name)
        self.assertEqual(body['ReconfigNW_DeviceType1'], device_type)
        self.assertEqual(body['ReconfigNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['ReconfigNW_VlanType1'], vlan_type)

    def test__delete_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        method, url, body = self.nwa._delete_tenant_fw(
            self.tenant_id,
            device_name, device_type,
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteTenantFW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_DeviceName1'], device_name)
        self.assertEqual(body['DeleteNW_DeviceType1'], device_type)

    def test__setting_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        method, url, body = self.nwa._setting_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('SettingNAT'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['ReconfigNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['ReconfigNW_VlanType1'], vlan_type)
        self.assertEqual(body['LocalIP'], local_ip)
        self.assertEqual(body['GlobalIP'], global_ip)

    def test__setting_fw_policy(self):
        fw_name = 'TFW8'
        props = {'properties': [1]}
        method, url, body = self.nwa._setting_fw_policy(
            self.tenant_id, fw_name, props
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('SettingFWPolicy'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DCResourceType'], 'TFW_Policy')
        self.assertEqual(body['DCResourceOperation'], 'Setting')
        self.assertIsInstance(body['DeviceInfo'], dict)
        self.assertEqual(body['Property'], props)
        di = body['DeviceInfo']
        self.assertEqual(di['DeviceName'], fw_name)
        self.assertEqual(di['Type'], 'TFW')

    def test__delete_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        method, url, body = self.nwa._delete_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteNAT'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['DeleteNW_VlanType1'], vlan_type)
        self.assertEqual(body['LocalIP'], local_ip)
        self.assertEqual(body['GlobalIP'], global_ip)

    def test__create_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        method, url, body = self.nwa._create_general_dev(
            self.tenant_id, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-1'
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('CreateGeneralDev'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         DC_RESOURCE_GROUP_POD1)
        self.assertEqual(body['CreateNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['CreateNW_VlanType1'], vlan_type)
        self.assertEqual(body['CreateNW_PortType1'], port_type)

    def test__delete_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        method, url, body = self.nwa._delete_general_dev(
            self.tenant_id, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-2'
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteGeneralDev'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_DCResourceGroupName'],
                         DC_RESOURCE_GROUP_POD1)
        self.assertEqual(body['DeleteNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['DeleteNW_VlanType1'], vlan_type)


class TestSendQueueIsNotEmpty(base.BaseTestCase):
    def test_send_queue_is_not_empty(self):
        rb = client.send_queue_is_not_empty()
        self.assertFalse(rb)


class TestConfig(base.BaseTestCase):
    '''Unit test for NwaClient config. '''

    def setUp(self):
        super(TestConfig, self).setUp()
        from os.path import dirname, realpath, abspath  # noqa
        pyfile = __file__.rstrip('c')
        self.inidir = dirname(realpath(abspath(pyfile))) + '/'

    def make_nwa001_ini(self):
        cfgfile = self.get_temp_file_path('nwa001.ini')
        with open(cfgfile, 'w') as f:
            f.write(CONFIG_FILE_CONTENTS)
        return cfgfile

    def test_nwa_config(self):
        cfgfile = self.make_nwa001_ini()
        cfg.CONF(args=[], default_config_files=[cfgfile])
        nwa1 = client.NwaClient()
        self.assertEqual(nwa1.host, '127.0.0.1')
        self.assertEqual(nwa1.port, 12081)
        self.assertFalse(nwa1.use_ssl)
        self.assertEqual(nwa1.workflow_first_wait, 2)
        self.assertEqual(nwa1.workflow_wait_sleep, 5)
        self.assertEqual(nwa1.workflow_retry_count, 6)
        self.assertEqual(
            nwa1.auth(
                'Wed, 11 Feb 2015 17:24:51 GMT',
                '/umf/tenant/DC1'
            ),
            'SharedKeyLite 5g2ZMAdMwZ1gQqZagNqbJSrlopQUAUHILcP2nmxVs28='
            ':mNd/AZJdMawfhJpVUT/lQcH7fPMz+4AocKti1jD1lCI='
        )
        headers = nwa1._make_headers('/')
        self.assertEqual(headers.get('Content-Type'), 'application/json')
        self.assertIsNotNone(headers.get('X-UMF-API-Version'))
        self.assertIsNotNone(headers.get('Authorization'))
        self.assertIsNotNone(headers.get('Date'))

        host = '1.2.3.4'
        port = 12345
        nwa2 = client.NwaClient(host=host, port=port, use_ssl=True)
        self.assertEqual(nwa2.host, host)
        self.assertEqual(nwa2.port, port)
        self.assertTrue(nwa2.use_ssl)
        auth = nwa2.define_auth_function('user', 'password')
        self.assertEqual(
            auth(
                'Wed, 11 Feb 2015 17:24:51 GMT',
                '/umf/tenant/DC1'
            ),
            'SharedKeyLite user:d7ym8ADuKFoIphXojb1a36lvMb5KZK7fPYKz7RlDcpw='
        )
        os.remove(cfgfile)
