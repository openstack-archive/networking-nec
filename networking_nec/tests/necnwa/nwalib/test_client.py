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
import six
import unittest

from neutron.tests import base

from networking_nec.plugins.necnwa.nwalib.client import (  # noqa
    NwaException,
    RestClient,
    Thread,
    Semaphore,
    NwaClient,
    NwaWorkflow,
    send_queue_is_not_empty
)
from networking_nec.plugins.necnwa.common.config import cfg


log_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s,%(msecs).03d - %(levelname)s - '
    '%(filename)s:%(lineno)d - %(message)s',
    '%H:%M:%S'
)
log_handler.setFormatter(formatter)
log_handler.setLevel(logging.INFO)
LOG = logging.getLogger()
LOG.addHandler(log_handler)
LOG.setLevel(logging.INFO)

log_handler.setLevel(logging.DEBUG)
LOG.setLevel(logging.DEBUG)

# using
# env NWA_SIMULATOR_SERVER=127.0.0.1:12081 nosetests -v --nocapture

nwa_host = '127.0.0.1'
nwa_port = 12081
if os.getenv("NWA_SIMULATOR_SERVER") is None:
    nwasim_noactive = True
else:
    nwasim_noactive = False
    server = os.getenv("NWA_SIMULATOR_SERVER")
    host, port = server.split(':')
    nwa_host = host
    nwa_port = int(port)

tenant_id = 'OpenT9004'
context = MagicMock()

# create general dev
dc_resource_group_pod1 = 'OpenStack/DC1/Common/Pod1Grp/Pod1'
dc_resource_group_pod2 = 'OpenStack/DC1/Common/Pod2Grp/Pod2'

# create tenant nw
dc_resource_group_app1 = 'OpenStack/DC1/Common/App1Grp/App1'

results = {}


def ok1(ctx, http_status, rj, *args, **kwargs):
    results['success'] = {
        'context': ctx,
        'http_status': http_status,
        'result': rj
    }


def ng1(ctx, http_status, rj, *args, **kwargs):
    results['failure'] = {
        'context': ctx,
        'http_status': http_status,
        'result': rj
    }
    if kwargs.get('exception', None):
        results['failure']['exception'] = kwargs['exception']


def init_async():
    results = {}                          # noqa


class TestNwaException(base.BaseTestCase):
    def test___str__(self):
        exc = NwaException(200, 'msg1', MagicMock())
        self.assertEqual(str(exc), 'http status: 200, msg1')


class TestNwaWorkflow(base.BaseTestCase):
    def test_strerror(self):
        em = NwaWorkflow.strerror('1')
        self.assertEqual(em, 'Unknown parent node')
        em = NwaWorkflow.strerror('299')
        self.assertEqual(em, 'Unknown error')

    def test_get_errno_from_resultdata(self):
        geterrno = NwaWorkflow.get_errno_from_resultdata
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

    def test_update_nameid(self):
        save1 = NwaWorkflow._nameid
        save2 = NwaWorkflow._nameid_initialized

        update_nameid = NwaWorkflow.update_nameid
        NwaWorkflow._nameid_initialized = True
        update_nameid(None)

        NwaWorkflow._nameid_initialized = False
        update_nameid([1])
        self.assertTrue(NwaWorkflow._nameid_initialized)

        NwaWorkflow._nameid = save1
        NwaWorkflow._nameid_initialized = save2


class TestRestClient(base.BaseTestCase):
    def setUp(self):
        super(TestRestClient, self).setUp()
        self.rcl = RestClient()

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
        rcl = RestClient('127.0.0.2', 8081, True)
        path = '/path'
        u = rcl.url(path)
        self.assertEqual(u, 'https://127.0.0.2:8081' + path)

    def test__make_headers(self):
        pass

    @patch('requests.request')
    def test__send_receive(self, rr):
        def myauth(a, b):
            pass

        rcl = RestClient('127.0.0.3', 8083, True, myauth)
        rcl._send_receive('GET', '/path')
        self.assertEqual(rr.call_count, 1)

    @patch('requests.request')
    def test_rest_api(self, rr):
        def myauth(a, b):
            pass

        rcl = RestClient('127.0.0.4', 8084, True, myauth)
        body = {}
        url = 'http://127.0.0.4:8084/path'
        rr.side_effect = requests.exceptions.RequestException
        self.assertRaises(
            NwaException,
            rcl.rest_api, 'GET', url, body
        )

    def test___report_workflow_error(self):
        self.rcl._report_workflow_error(None, 0)

    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.'
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

        ra.side_effect = NwaException(200, 'msg1', None)
        hst, rd = self.rcl.rest_api_return_check('GET', url, body)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

    @patch('requests.request')
    def test_rest_api_return_check_raise(self, rr):
        def myauth(a, b):
            pass

        rr.side_effect = OSError
        rcl = RestClient('127.0.0.3', 8083, True, myauth)
        body = {'a': 1}
        url = 'http://127.0.0.5:8085/path'
        self.assertRaises(
            OSError,
            rcl.rest_api_return_check, 'GET', url, body
        )

    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api_return_check')
    def test_get(self, rarc):
        self.rcl.get('')
        self.assertEqual(rarc.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api_return_check')
    def test_post(self, rarc):
        self.rcl.post('')
        self.assertEqual(rarc.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api_return_check')
    def test_put(self, rarc):
        self.rcl.put('')
        self.assertEqual(rarc.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api_return_check')
    def test_delete(self, rarc):
        self.rcl.delete('')
        self.assertEqual(rarc.call_count, 1)


class TestThread(base.BaseTestCase):
    def test_stop(self):
        t1 = Thread(MagicMock())
        t1.stop()
        self.assertTrue(True)

    def test_wait(self):
        t1 = Thread(MagicMock())
        t1.wait()
        self.assertTrue(True)


class TestSemaphore(object):
    def test_get_tenant_semaphore(self):
        sem1 = Semaphore.get_tenant_semaphore('T1')
        sem2 = Semaphore.get_tenant_semaphore('T1')
        self.assertEqual(sem1, sem2)

        sem3 = Semaphore.get_tenant_semaphore('T2')
        self.assertTrue(sem1 != sem3)

        Semaphore.delete_tenant_semaphore('T1')
        sem4 = Semaphore.get_tenant_semaphore('T1')
        self.assertTrue(sem1 != sem4)

    def test_get_tenant_semaphore_raise1(self):
        self.assertRaises(
            TypeError,
            Semaphore.get_tenant_semaphore, 0
        )

    def test_get_tenant_semaphore_raise2(self):
        self.assertRaises(
            TypeError,
            Semaphore.get_tenant_semaphore, ''
        )

    def test_delete_tenant_semaphore(self):
        Semaphore.delete_tenant_semaphore('T11')
        self.assertTrue(True)

    def test_any_locked(self):
        sem1 = Semaphore.get_tenant_semaphore('T21')
        with sem1.sem:
            locked = Semaphore.any_locked()
            self.assertTrue(locked)
        locked = Semaphore.any_locked()
        self.assertFalse(locked)

    def check_push_history(self, param):
        t31 = Semaphore.get_tenant_semaphore('T31')
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
        LOG.info(param)

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


class TestNwaClient(object):
    '''Test code for Nwa Client '''

    def setUp(self):
        super(TestNwaClient, self).setUp()
        host = nwa_host
        port = nwa_port
        access_key_id = 'PzGIIoLbL7ttHFkDHqLguFz/7+VsVJbDmV0iLWAkJ0g='
        secret_access_key = 'nbvX65iujFoYomXTKROF9GKUN6L2rAM/sI+cvNdW7sw='

        self.nwa = NwaClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key
        )
        self.nwa2 = NwaClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key
        )
        self.nwa.workflow_first_wait = 0.5
        self.nwa2.workflow_first_wait = 0.5

    def get_vlan_info(self):
        self.business_vlan = self.public_vlan = None
        self.business_vlan_name = self.public_vlan_name = None
        rj = self.nwa.get_reserved_dc_resource(tenant_id)
        for node in rj.get('GroupNode'):
            node_type = node.get('Type')
            if node_type == 'BusinessVLAN':
                self.business_vlan = node
                self.business_vlan_name = node['VLAN'][0]['LogicalName']
            elif node_type == 'PublicVLAN':
                self.public_vlan = node
                self.public_vlan_name = node['VLAN'][0]['LogicalName']
        # print json.dumps(self.business_vlan, indent=4, sort_keys=True)

    @unittest.skipIf(nwasim_noactive, '')
    def test_tenant(self):
        tenantid = 'OpenT9001'
        try:
            self.nwa.delete_tenant(tenantid)
        except Exception:
            pass
        rj = self.nwa.create_tenant(tenantid)
        self.assertEqual(rj, (200, {}))
        rj = self.nwa.delete_tenant(tenantid)
        self.assertEqual(rj, (200, {}))

    @unittest.skipIf(nwasim_noactive, '')
    def test_tenant_nw(self):
        tenantid = 'OpenT9002'
        dcresgrp = dc_resource_group_pod1
        ctx = {'context': 10}
        try:
            self.nwa.delete_tenant(tenantid)
        except Exception:
            pass
        self.nwa.create_tenant(tenantid)
        init_async()
        rj1 = self.nwa.create_tenant_nw(ok1, ng1, ctx, tenantid, dcresgrp)
        rj2 = self.nwa.delete_tenant_nw(ok1, ng1, ctx, tenantid)

        # print(json.dumps(rj, indent=4, sort_keys=True))
        self.assertEqual(rj1['http_status'], 200)
        self.assertIsNoeNone(rj1['result']['resultdata']['TenantID'])

        # print(json.dumps(rj, indent=4, sort_keys=True))
        self.assertEqual(rj2['http_status'], 200)
        self.assertIsNotNone(rj2['result']['resultdata']['TenantID'])

        self.nwa.delete_tenant(tenantid)

    @unittest.skipIf(nwasim_noactive, '')
    def test_tenant_nw_async(self):
        tenantid1 = 'OpenT9001'
        tenantid2 = 'OpenT9002'
        dcresgrp = dc_resource_group_pod1
        ctx = {'context': 10}
        try:
            self.nwa.delete_tenant(tenantid1)
        except Exception:
            pass
        self.nwa.create_tenant(tenantid1)
        init_async()
        rj1 = self.nwa.create_tenant_nw(ok1, ng1, ctx, tenantid1, dcresgrp)
        rj2 = self.nwa2.delete_tenant_nw(ok1, ng1, ctx, tenantid2)

        # print(json.dumps(rj, indent=4, sort_keys=True))
        self.assertEqual(rj1['http_status'], 200)
        self.assertIsNotNone(rj1['result']['resultdata']['TenantID'])

        # print(json.dumps(rj, indent=4, sort_keys=True))
        self.assertEqual(rj2['http_status'], 200)
        self.assertIsNoeNone(rj2['result']['resultdata']['TenantID'])

        self.nwa.delete_tenant(tenantid1)

    @unittest.skipIf(nwasim_noactive, '')
    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('networking_nec.plugins.necnwa.nwalib.client.Semaphore.push_history')  # noqa
    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.call_workflow')  # noqa
    def test_apply_async(self, cawk, puhi, lock):
        def mkreq(*args, **kwargs):
            return mkreq, 'url100', 'body100'

        init_async()
        ctx = 100
        tid = 'T100'
        resp1 = {
            'status': 'SUCCESS',
            'resultdata': {}
        }
        cawk.return_value = (200, resp1)
        lock.return_value = True
        rj, rd = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        self.assertEqual(rj['http_status'], 200)
        self.assertEqual(rj['context'], ctx)
        self.assertEqual(rj['result'], resp1)

        init_async()
        resp2 = {
            'status': 'FAILED',
            'resultdata': {}
        }
        cawk.return_value = (200, resp2)
        rj, rd = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        self.assertEqual(rj['http_status'], 200)
        self.assertEqual(rj['context'], ctx)
        self.assertEqual(rj['result'], resp2)

        init_async()
        orgexc = MagicMock()
        orgexc.args = [
            IOError(5, 'I/O Error')
        ]
        orgexc.__str__ = lambda x: 'Other Error'
        cawk.side_effect = NwaException(200, 'apply_async-message-1', orgexc)
        rj = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        self.assertEqual(rj['http_status'], 200)
        self.assertEqual(rj['context'], ctx)
        self.assertIsNone(rj['result'])
        self.assertEqual(rj['exception']['errno'], 5)
        self.assertEqual(rj['exception']['message'], 'I/O Error')

        init_async()
        orgexc = MagicMock()
        orgexc.__str__ = lambda x: 'Other Error'
        cawk.side_effect = NwaException(200, 'apply_async-message-2', orgexc)
        rj = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        self.assertEqual(rj['http_status'], 200)
        self.assertEqual(rj['context'], ctx)
        self.assertIsNone(rj['result'])
        self.assertEqual(rj['exception']['errno'], 0)
        self.assertEqual(rj['exception']['message'], 'Other Error')
        init_async()

        init_async()
        cawk.side_effect = Exception
        rj = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        self.assertEqual(rj['http_status'], -1)
        self.assertEqual(rj['context'], ctx)
        self.assertIsNone(rj['result'])
        init_async()

    def test_workflow_kick_and_wait_raise(self):
        call_ne = MagicMock(side_effect=NwaException(200, 'm1', None))
        call_ne.__name__ = 'POST'
        self.assertRaises(
            NwaException,
            self.nwa.workflow_kick_and_wait, call_ne, None, None
        )

    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')  # noqa
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
    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.workflow_kick_and_wait')  # noqa
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

        s = Semaphore()
        s.hook = hook
        hst, rd = self.nwa.call_workflow(mkreq, '3', '3', nocache=s.hook)
        self.assertEqual(hst, 203)
        self.assertEqual(rd, '3')

    def test_get_reserved_dc_resource(self):
        self.nwa.get_reserved_dc_resource(tenant_id)
        self.assertTrue(True)

    def test_get_tenant_resource(self):
        self.nwa.get_tenant_resource(tenant_id)
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
            ok1, ng1, context, tenant_id,
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
            ok1, ng1, context, tenant_id,
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
            ok1, ng1, context, tenant_id,
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
            ok1, ng1, context, tenant_id,
            fw_name, vlan_devaddr,
            vlan_name, vlan_type
        )
        return rt

    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')  # noqa
    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.post')
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

    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')  # noqa
    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.post')
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

    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')  # noqa
    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.post')
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

    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.call_workflow')  # noqa
    def test_setting_fw_policy(self, cawk):
        cawk.return_value = (200, {'status': 'SUCCESS'})
        props = {'Property': 1}
        fw_name = 'TFW8'
        rd, rj = self.nwa.setting_fw_policy(tenant_id, fw_name, props)
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')

        cawk.return_value = (500, None)
        rd, rj = self.nwa.setting_fw_policy(tenant_id, fw_name, props)
        self.assertEqual(rd, 500)

    def create_general_dev(self, vlan_name):
        init_async()
        dcresgrp_name = 'Common/App/Pod3'
        rd, rj = self.nwa.create_general_dev(
            ok1, ng1, context, tenant_id,
            dcresgrp_name, vlan_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        return rd, rj

    def delete_general_dev(self, vlan_name):
        init_async()
        dcresgrp_name = 'Common/App/Pod3'
        rd, rj = self.nwa.delete_general_dev(
            ok1, ng1, context, tenant_id,
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

    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')  # noqa
    @patch('networking_nec.plugins.necnwa.nwalib.client.RestClient.post')
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


class TestNwaClientCli(base.BaseTestCase):
    '''Test code for Nwa Client in interactive. '''

    def setUp(self):
        super(TestNwaClientCli, self).setUp()
        self.nwa = NwaClient(
            host=nwa_host,
            port=nwa_port,
            access_key_id='access_key_id',
            secret_access_key='secret_access_key'
        )
        hst, rj = self.nwa.get_dc_resource_groups()
        self.dc_resource_groups = rj.get('Groups')
        self.get_vlan_info()
        self.nwa.workflow_first_wait = 0.5

    def get_vlan_info(self):
        self.business_vlan = self.public_vlan = None
        self.business_vlan_name = self.public_vlan_name = None
        hst, rj = self.nwa.get_reserved_dc_resource(tenant_id)
        for node in rj.get('GroupNode'):
            node_type = node.get('Type')
            if node_type == 'BusinessVLAN':
                self.business_vlan = node
                self.business_vlan_name = node['VLAN'][0]['LogicalName']
            elif node_type == 'PublicVLAN':
                self.public_vlan = node
                self.public_vlan_name = node['VLAN'][0]['LogicalName']
        # print json.dumps(self.business_vlan, indent=4, sort_keys=True)

    @unittest.skipIf(nwasim_noactive, '')
    def test_workflowinstance(self):
        try:
            nwa = NwaClient(
                host=nwa_host,
                port=nwa_port,
                access_key_id='access_key_id',
                secret_access_key='secret_access_key'
            )
            rj = nwa.workflowinstance('(*0*)400300012015013100003')
            self.assertEqual(rj, (500, None))
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_tenant(self):
        try:
            rj = self.nwa.create_tenant(tenant_id)
            self.assertEqual(rj, (200, {}))
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_tenant(self):
        try:
            rj = self.nwa.delete_tenant(tenant_id)
            self.assertEqual(rj, (200, {}))
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_tenant_nw(self):
        try:
            init_async()
            rj, rd = self.nwa.create_tenant_nw(
                ok1, ng1, context, tenant_id, dc_resource_group_app1
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertTrue(isinstance(rd, dict))
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_tenant_nw(self):
        try:
            init_async()
            rj = self.nwa.delete_tenant_nw(ok1, ng1, context, tenant_id)
            self.assertIsInstance(rj, dict)
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_vlan(self):
        try:
            init_async()
            ipaddr = '172.16.0.0'
            mask = 24
            rj, rd = self.nwa.create_vlan(ok1, ng1, context, tenant_id, ipaddr,
                                          mask)
            self.assertIsInstance(rj, dict)
            self.assertIsInstance(rd, dict)
            rd = rd.get('resultdata')
            self.assertEqual(rd.get('VlanIPSubnet'), ipaddr)
            self.assertEqual(rd.get('VlanSubnetMask'), '255.255.255.0')
            logical_name = rd.get('LogicalNWName')
            self.assertIsInstance(logical_name, six.string_types)
            self.assertGreater(len(logical_name), 1)
            self.business_vlan_name = logical_name
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_vlan(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            rj2, rd2 = self.nwa.delete_vlan(ok1, ng1, context, tenant_id,
                                            vlan_name)
            self.assertIsInstance(rj2, dict)
            self.assertIsInstance(rd2, dict)
            rd2 = rd2.get('resultdata')
            self.assertIsInstance(rd2.get('NWAResult'), six.string_types)
            self.assertGreater(len(rd2.get('NWAResult')), 1)
            self.business_vlan_name = None
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_tenant_fw(self):
        try:
            init_async()
            vlan_devaddr = '172.16.0.254'
            vlan_name = self.business_vlan['VLAN'][0]['LogicalName']
            vlan_type = 'BusinessVLAN'
            rj, rd = self.nwa.create_tenant_fw(
                ok1, ng1, context, tenant_id,
                dc_resource_group_app1,
                vlan_devaddr, vlan_name, vlan_type
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_update_tenant_fw(self):
        try:
            init_async()
            device_name = 'TFW0'
            device_type = 'TFW'
            vlan_name = self.business_vlan['VLAN'][0]['LogicalName']
            vlan_type = 'BusinessVLAN'
            rj = self.nwa.update_tenant_fw(
                ok1, ng1, context, tenant_id,
                device_name, device_type, vlan_name, vlan_type
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_tenant_fw(self):
        try:
            init_async()
            device_name = 'TFW0'
            device_type = 'TFW'
            rj = self.nwa.delete_tenant_fw(
                ok1, ng1, context, tenant_id,
                device_name, device_type
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_update_nat(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            vlan_type = 'BusinessVLAN'
            local_ip = '172.16.0.5'
            global_ip = '10.0.4.5'
            fw_name = 'TFW78'
            rj = self.nwa.update_nat(
                ok1, ng1, context, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip, fw_name
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_setting_nat(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            vlan_type = 'BusinessVLAN'
            local_ip = '172.16.0.5'
            global_ip = '10.0.4.5'
            fw_name = 'TFW78'
            rj = self.nwa.setting_nat(
                ok1, ng1, context, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip, fw_name
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_nat(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            vlan_type = 'BusinessVLAN'
            local_ip = '172.16.0.5'
            global_ip = '10.0.0.5'
            fw_name = 'TFW78'
            rj = self.nwa.delete_nat(
                ok1, ng1, context, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip, fw_name
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_setting_fw_policy_async(self):
        try:
            init_async()
            fw_name = 'TFW80'
            props = {}
            rj = self.nwa.setting_fw_policy_async(
                ok1, ng1, context, tenant_id,
                fw_name, props
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_general_dev(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            rj = self.nwa.create_general_dev(
                ok1, ng1, context, tenant_id,
                dc_resource_group_pod1,
                vlan_name, 'BusinessVLAN'
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_general_dev(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            rj = self.nwa.delete_general_dev(
                ok1, ng1, context, tenant_id,
                dc_resource_group_pod1,
                vlan_name, 'BusinessVLAN'
            )
            self.assertIsInstance(rj, dict)
            self.assertEqual(rj['http_status'], 200)
            self.assertEqual(rj['result']['status'], 'SUCCESS')
        except Exception:
            self.assertTrue(False, 'Exception occured')


class TestUtNwaClient(base.BaseTestCase):
    '''Unit test for NwaClient '''

    def setUp(self):
        super(TestUtNwaClient, self).setUp()
        self.nwa = NwaClient(load_workflow_list=False)
        self.tenant_id = 'OpenT9004'

    def test__create_tenant_nw(self):
        method, url, body = self.nwa._create_tenant_nw(
            self.tenant_id,
            dc_resource_group_app1
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegexpMatches(url, NwaWorkflow.path('CreateTenantNW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         dc_resource_group_app1)
        self.assertEqual(body['CreateNW_OperationType'], 'CreateTenantNW')

    def test__delete_tenant_nw(self):
        method, url, body = self.nwa._delete_tenant_nw(
            self.tenant_id
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegexpMatches(url, NwaWorkflow.path('DeleteTenantNW'))
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
        self.assertRegexpMatches(url, NwaWorkflow.path('CreateVLAN'))
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
        self.assertRegexpMatches(url, NwaWorkflow.path('DeleteVLAN'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['DeleteNW_VlanType1'], vlan_type)

    def test__create_tenant_fw(self):
        vlan_devaddr = '10.0.0.254'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        method, url, body = self.nwa._create_tenant_fw(
            self.tenant_id, dc_resource_group_app1,
            vlan_devaddr, vlan_name, vlan_type
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegexpMatches(url, NwaWorkflow.path('CreateTenantFW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         dc_resource_group_app1)
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
        self.assertRegexpMatches(url, NwaWorkflow.path('UpdateTenantFW'))
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
        self.assertRegexpMatches(url, NwaWorkflow.path('DeleteTenantFW'))
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
        self.assertRegexpMatches(url, NwaWorkflow.path('SettingNAT'))
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
        self.assertRegexpMatches(url, NwaWorkflow.path('SettingFWPolicy'))
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
        self.assertRegexpMatches(url, NwaWorkflow.path('DeleteNAT'))
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
            self.tenant_id, dc_resource_group_pod1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-1'
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegexpMatches(url, NwaWorkflow.path('CreateGeneralDev'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         dc_resource_group_pod1)
        self.assertEqual(body['CreateNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['CreateNW_VlanType1'], vlan_type)
        self.assertEqual(body['CreateNW_PortType1'], port_type)

    def test__delete_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        method, url, body = self.nwa._delete_general_dev(
            self.tenant_id, dc_resource_group_pod1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-2'
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegexpMatches(url, NwaWorkflow.path('DeleteGeneralDev'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_DCResourceGroupName'],
                         dc_resource_group_pod1)
        self.assertEqual(body['DeleteNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['DeleteNW_VlanType1'], vlan_type)


class TestSendQueueIsNotEmpty(base.BaseTestCase):
    def test_send_queue_is_not_empty(self):
        rb = send_queue_is_not_empty()
        self.assertFalse(rb)


class TestConfig(base.BaseTestCase):
    '''Unit test for NwaClient config. '''

    def setUp(self):
        super(TestConfig, self).setUp()
        from os.path import dirname, realpath, abspath  # noqa
        pyfile = __file__.rstrip('c')
        self.inidir = dirname(realpath(abspath(pyfile))) + '/'

    def test_nwa_config(self):
        cfgfile = self.inidir + 'nwa001.ini'
        cfg.CONF(args=[], default_config_files=[cfgfile])
        nwa1 = NwaClient()
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
        nwa2 = NwaClient(host=host, port=port, use_ssl=True)
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
