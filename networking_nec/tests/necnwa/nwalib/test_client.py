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

import os
import unittest
import logging
import requests
from mock import patch, MagicMock
from nose.tools import eq_, ok_, raises
from neutron.plugins.necnwa.nwalib.client import (
    NwaException,
    RestClient,
    Thread,
    Semaphore,
    NwaClient,
    NwaWorkflow,
    send_queue_is_not_empty
)
from neutron.plugins.necnwa.common.config import cfg


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


class TestNwaException(unittest.TestCase):
    def test___str__(self):
        exc = NwaException(200, 'msg1', MagicMock())
        eq_(str(exc), 'http status: 200, msg1')


class TestNwaWorkflow(unittest.TestCase):
    def test_strerror(self):
        em = NwaWorkflow.strerror('1')
        eq_(em, 'Unknown parent node')
        em = NwaWorkflow.strerror('299')
        eq_(em, 'Unknown error')

    def test_get_errno_from_resultdata(self):
        geterrno = NwaWorkflow.get_errno_from_resultdata
        rc = geterrno({})
        ok_(rc is None)

        rc = geterrno({
            'resultdata': {}
        })
        ok_(rc is None)

        rc = geterrno({
            'resultdata': {
                'ErrorMessage': ''
            }
        })
        ok_(rc is None)

        rc = geterrno({
            'resultdata': {
                'ErrorMessage': 'ErrorNumber=100'
            }
        })
        eq_(rc, '100')

        rc = geterrno({
            'resultdata': {
                'ErrorMessage': 'ReservationErrorCode = 101'
            }
        })
        eq_(rc, '101')

    def test_update_nameid(self):
        save1 = NwaWorkflow._nameid
        save2 = NwaWorkflow._nameid_initialized

        update_nameid = NwaWorkflow.update_nameid
        NwaWorkflow._nameid_initialized = True
        update_nameid(None)

        NwaWorkflow._nameid_initialized = False
        update_nameid([1])
        eq_(NwaWorkflow._nameid_initialized, True)

        NwaWorkflow._nameid = save1
        NwaWorkflow._nameid_initialized = save2


class TestRestClient(unittest.TestCase):
    def setUp(self):
        self.rcl = RestClient()

    def test__init_default(self):
        kwargs = {}
        url = 'http://127.0.0.1:8080'
        auth = 'auth'
        self.rcl._init_default(kwargs, url, auth)
        eq_(kwargs['host'], '127.0.0.1')
        eq_(kwargs['port'], 8080)
        ok_(kwargs['use_ssl'] is False)
        eq_(kwargs['auth'], auth)

        url = 'https://127.0.0.1:8080'
        self.rcl._init_default(kwargs, url, auth)
        ok_(kwargs['use_ssl'] is True)

    def test_url(self):
        rcl = RestClient('127.0.0.2', 8081, True)
        path = '/path'
        u = rcl.url(path)
        eq_(u, 'https://127.0.0.2:8081' + path)

    def test__make_headers(self):
        pass

    @patch('requests.request')
    def test__send_receive(self, rr):
        def myauth(a, b):
            pass

        rcl = RestClient('127.0.0.3', 8083, True, myauth)
        rcl._send_receive('GET', '/path')
        eq_(rr.call_count, 1)

    @raises(NwaException)
    @patch('requests.request')
    def test_rest_api(self, rr):
        def myauth(a, b):
            pass

        rcl = RestClient('127.0.0.4', 8084, True, myauth)
        body = {}
        url = 'http://127.0.0.4:8084/path'
        rr.side_effect = requests.exceptions.RequestException
        rcl.rest_api('GET', url, body)

    def test___report_workflow_error(self):
        self.rcl._report_workflow_error(None, 0)

    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api')
    def test_rest_api_return_check(self, ra):
        body = {'a': 1}
        url = 'http://127.0.0.5:8085/path'
        ra.return_value = (200, None)
        hst, rd = self.rcl.rest_api_return_check('GET', url, body)
        eq_(hst, 200)
        ok_(rd is None)

        failed = {
            'status': 'FAILED', 'progress': '100'
        }
        ra.return_value = (200, failed)
        self.rcl.post_data = url, body
        hst, rd = self.rcl.rest_api_return_check('GET', url, body)
        eq_(hst, 200)
        eq_(rd, failed)

        ra.side_effect = NwaException(200, 'msg1', None)
        hst, rd = self.rcl.rest_api_return_check('GET', url, body)
        eq_(hst, 200)
        eq_(rd, None)

    @raises(OSError)
    @patch('requests.request')
    def test_rest_api_return_check_raise(self, rr):
        def myauth(a, b):
            pass

        rr.side_effect = OSError
        rcl = RestClient('127.0.0.3', 8083, True, myauth)
        body = {'a': 1}
        url = 'http://127.0.0.5:8085/path'
        rcl.rest_api_return_check('GET', url, body)

    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api_return_check')
    def test_get(self, rarc):
        self.rcl.get('')
        eq_(rarc.call_count, 1)

    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api_return_check')
    def test_post(self, rarc):
        self.rcl.post('')
        eq_(rarc.call_count, 1)

    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api_return_check')
    def test_put(self, rarc):
        self.rcl.put('')
        eq_(rarc.call_count, 1)

    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.'
           'rest_api_return_check')
    def test_delete(self, rarc):
        self.rcl.delete('')
        eq_(rarc.call_count, 1)


class TestThread(unittest.TestCase):
    def test_stop(self):
        t1 = Thread(MagicMock())
        t1.stop()
        ok_(True)

    def test_wait(self):
        t1 = Thread(MagicMock())
        t1.wait()
        ok_(True)


class TestSemaphore(object):
    def test_get_tenant_semaphore(self):
        sem1 = Semaphore.get_tenant_semaphore('T1')
        sem2 = Semaphore.get_tenant_semaphore('T1')
        eq_(sem1, sem2)

        sem3 = Semaphore.get_tenant_semaphore('T2')
        ok_(sem1 != sem3)

        Semaphore.delete_tenant_semaphore('T1')
        sem4 = Semaphore.get_tenant_semaphore('T1')
        ok_(sem1 != sem4)

    @raises(TypeError)
    def test_get_tenant_semaphore_raise1(self):
        Semaphore.get_tenant_semaphore(0)

    @raises(TypeError)
    def test_get_tenant_semaphore_raise2(self):
        Semaphore.get_tenant_semaphore('')

    def test_delete_tenant_semaphore(self):
        Semaphore.delete_tenant_semaphore('T11')
        ok_(True)

    def test_any_locked(self):
        sem1 = Semaphore.get_tenant_semaphore('T21')
        with sem1.sem:
            locked = Semaphore.any_locked()
            eq_(locked, True)
        locked = Semaphore.any_locked()
        eq_(locked, False)

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
        eq_(r1, param['search_result1'])
        eq_(r2, param['search_result2'])
        LOG.info(param)

    def test_push_history(self):
        post1 = MagicMock()
        post1.__name__ = 'post001'
        succeed = {'status': 'SUCCEED'}
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
    '''Test code for Nwa Client
    '''

    def setUp(self):
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
        eq_(rj, (200, {}))
        rj = self.nwa.delete_tenant(tenantid)
        eq_(rj, (200, {}))

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
        gt1 = self.nwa.create_tenant_nw(ok1, ng1, ctx, tenantid, dcresgrp)
        gt2 = self.nwa.delete_tenant_nw(ok1, ng1, ctx, tenantid)

        gt1.wait()
        rj = results.get('success')
        # print(json.dumps(rj, indent=4, sort_keys=True))
        eq_(rj['http_status'], 200)
        ok_(rj['result']['resultdata']['TenantID'] is not None)

        gt2.wait()
        rj = results.get('success')
        # print(json.dumps(rj, indent=4, sort_keys=True))
        eq_(rj['http_status'], 200)
        ok_(rj['result']['resultdata']['TenantID'] is not None)

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
        gt1 = self.nwa.create_tenant_nw(ok1, ng1, ctx, tenantid1, dcresgrp)
        gt2 = self.nwa2.delete_tenant_nw(ok1, ng1, ctx, tenantid2)

        gt1.wait()
        rj = results.get('success')
        # print(json.dumps(rj, indent=4, sort_keys=True))
        eq_(rj['http_status'], 200)
        ok_(rj['result']['resultdata']['TenantID'] is not None)

        gt2.wait()
        rj = results.get('success')
        # print(json.dumps(rj, indent=4, sort_keys=True))
        eq_(rj['http_status'], 200)
        ok_(rj['result']['resultdata']['TenantID'] is not None)

        self.nwa.delete_tenant(tenantid1)

    @unittest.skipIf(nwasim_noactive, '')
    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('neutron.plugins.necnwa.nwalib.client.Semaphore.push_history')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.call_workflow')
    def test_apply_async(self, cawk, puhi, lock):
        def mkreq(*args, **kwargs):
            return mkreq, 'url100', 'body100'

        init_async()
        ctx = 100
        tid = 'T100'
        resp1 = {
            'status': 'SUCCEED',
            'resultdata': {}
        }
        cawk.return_value = (200, resp1)
        lock.return_value = True
        gt = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        gt.wait()
        rk = results.get('success')
        eq_(rk['http_status'], 200)
        eq_(rk['context'], ctx)
        eq_(rk['result'], resp1)

        init_async()
        resp2 = {
            'status': 'FAILED',
            'resultdata': {}
        }
        cawk.return_value = (200, resp2)
        gt = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        gt.wait()
        rk = results.get('failure')
        eq_(rk['http_status'], 200)
        eq_(rk['context'], ctx)
        eq_(rk['result'], resp2)

        init_async()
        orgexc = MagicMock()
        orgexc.args = [
            IOError(5, 'I/O Error')
        ]
        orgexc.__str__ = lambda x: 'Other Error'
        cawk.side_effect = NwaException(200, 'apply_async-message-1', orgexc)
        gt = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        gt.wait()
        rk = results.get('failure')
        eq_(rk['http_status'], 200)
        eq_(rk['context'], ctx)
        eq_(rk['result'], None)
        eq_(rk['exception']['errno'], 5)
        eq_(rk['exception']['message'], 'I/O Error')

        init_async()
        orgexc = MagicMock()
        orgexc.__str__ = lambda x: 'Other Error'
        cawk.side_effect = NwaException(200, 'apply_async-message-2', orgexc)
        gt = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        gt.wait()
        rk = results.get('failure')
        eq_(rk['http_status'], 200)
        eq_(rk['context'], ctx)
        eq_(rk['result'], None)
        eq_(rk['exception']['errno'], 0)
        eq_(rk['exception']['message'], 'Other Error')
        init_async()

        init_async()
        cawk.side_effect = Exception
        gt = self.nwa.apply_async(mkreq, ok1, ng1, ctx, tid)
        gt.wait()
        rk = results.get('failure')
        eq_(rk['http_status'], -1)
        eq_(rk['context'], ctx)
        eq_(rk['result'], None)
        init_async()

    @raises(NwaException)
    def test_workflow_kick_and_wait_raise(self):
        call_ne = MagicMock(side_effect=NwaException(200, 'm1', None))
        call_ne.__name__ = 'POST'
        self.nwa.workflow_kick_and_wait(call_ne, None, None)

    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')
    def test_workflow_kick_and_wait(self, wki, lock):
        call = MagicMock()
        call.__name__ = 'POST'
        call.return_value = 200, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        eq_(hst, 200)
        eq_(rd, None)

        call.return_value = 200, {'executionid': 1}
        wki.return_value = 201, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        eq_(hst, 201)
        eq_(rd, None)

        call.return_value = 200, {'executionid': '1'}
        wki.return_value = 202, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        eq_(hst, 202)
        eq_(rd, None)

        wki.return_value = 201, {'status': 'RUNNING'}
        self.nwa.workflow_retry_count = 1
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        eq_(hst, 201)
        eq_(rd, None)

        wki.side_effect = Exception
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        eq_(hst, 200)
        eq_(rd, None)

    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.workflow_kick_and_wait')
    @patch('neutron.plugins.necnwa.nwalib.client.Semaphore.push_history')
    @patch('neutron.plugins.necnwa.nwalib.client.Semaphore.search_history')
    def test_call_workflow(self, sehi, puhi, wkaw, lock):
        call = MagicMock()
        call.__name__ = 'POST'

        def mkreq(a, b, nocache=None):
            return call, 'url_' + str(a), 'body_' + str(b)

        # 呼び出し履歴内で見つかり、履歴の内容を返す。
        sehi.return_value = 200, '0'
        hst, rd = self.nwa.call_workflow(mkreq, '0', '0')
        eq_(hst, 200)
        eq_(rd, '0')

        # 履歴にないので workflow_kick_and_wai呼び出し。kwargs=None
        sehi.return_value = None, None
        wkaw.return_value = 201, '1'
        puhi.reset_mock()
        hst, rd = self.nwa.call_workflow(mkreq, '1', '1')
        eq_(hst, 201)
        eq_(rd, '1')
        eq_(puhi.call_count, 1)

        # 'nocache' in kwargs
        sehi.return_value = None, None
        wkaw.return_value = 202, '2'
        puhi.reset_mock()
        hst, rd = self.nwa.call_workflow(mkreq, '2', '2', nocache=True)
        eq_(hst, 202)
        eq_(rd, '2')
        eq_(puhi.call_count, 0)

        # 'nocache' is hook function
        sehi.return_value = None, None
        wkaw.return_value = 203, '3'
        puhi.reset_mock()

        def hook(self, *args, **kwargs):
            eq_(args[0].__name__, 'POST')
            eq_(args[1], 'url_3')
            eq_(args[2], 'body_3')
            eq_(args[3], 203)
            eq_(args[4], '3')

        s = Semaphore()
        s.hook = hook
        hst, rd = self.nwa.call_workflow(mkreq, '3', '3', nocache=s.hook)
        eq_(hst, 203)
        eq_(rd, '3')
        eq_(puhi.call_count, 0)

    def test_get_reserved_dc_resource(self):
        self.nwa.get_reserved_dc_resource(tenant_id)
        ok_(True)

    def test_get_tenant_resource(self):
        self.nwa.get_tenant_resource(tenant_id)
        ok_(True)

    def test_get_dc_resource_groups(self):
        self.nwa.get_dc_resource_groups('OpenStack/DC1/Common/Pod2Grp/Pod2')
        ok_(True)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.get')
    def test_get_workflow_list(self, get):
        get.return_value = 209, None
        hst, rd = self.nwa.get_workflow_list()
        eq_(hst, 209)
        ok_(rd is None)

        get.side_effect = Exception
        hst, rd = self.nwa.get_workflow_list()
        ok_(hst is None)
        ok_(rd is None)

    def test_stop_workflowinstance(self):
        self.nwa.stop_workflowinstance('id-0')
        ok_(True)

    def test_update_workflow_list(self):
        self.nwa.update_workflow_list()
        ok_(True)

    def test_wait_workflow_done(self):
        self.nwa.wait_workflow_done(MagicMock())
        ok_(True)

    def create_vlan(self):
        init_async()
        vlan_type = 'PublicVLAN'
        ipaddr = '172.16.0.0'
        mask = '28'
        gt1 = self.nwa.create_vlan(
            ok1, ng1, context, tenant_id,
            vlan_type, ipaddr, mask
        )
        gt1.wait()
        return results.get('success')

    def delete_nat(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_100'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.5'
        global_ip = '10.0.1.5'
        fw_name = 'TFW77'
        gt1 = self.nwa.delete_nat(
            ok1, ng1, context, tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        gt1.wait()
        return results.get('success')

    def setting_nat(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.6'
        global_ip = '10.0.1.6'
        fw_name = 'TFW78'
        gt1 = self.nwa.setting_nat(
            ok1, ng1, context, tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        gt1.wait()
        return results.get('success')

    def update_tenant_fw(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        vlan_devaddr = '192.168.6.254'
        fw_name = 'TFW79'
        gt1 = self.nwa.update_tenant_fw(
            ok1, ng1, context, tenant_id,
            fw_name, vlan_devaddr,
            vlan_name, vlan_type
        )
        gt1.wait()
        return results.get('success')

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')
    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.post')
    def test_delete_nat(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCEED', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCEED'})

        rj = self.delete_nat()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rj = self.delete_nat()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rj = self.delete_nat()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')
    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.post')
    def test_setting_nat(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCEED', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCEED'})

        rj = self.setting_nat()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rj = self.setting_nat()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rj = self.setting_nat()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')
    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.post')
    def test_update_tenant_fw(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCEED', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCEED'})

        rj = self.update_tenant_fw()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

        post.reset_mock()                 # check no in428 history
        rj = self.update_tenant_fw()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rj = self.update_tenant_fw()
        eq_(rj['http_status'], 200)
        eq_(post.call_count, 1)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.call_workflow')
    def test_setting_fw_policy(self, cawk):
        cawk.return_value = (200, {'status': 'SUCCEED'})
        props = {'Property': 1}
        fw_name = 'TFW8'
        rj = self.nwa.setting_fw_policy(tenant_id, fw_name, props)
        eq_(rj['http_status'], 200)
        eq_(rj['status'], 'SUCCEED')

        cawk.return_value = (500, None)
        rj = self.nwa.setting_fw_policy(tenant_id, fw_name, props)
        eq_(rj['http_status'], 500)

    def create_general_dev(self, vlan_name):
        init_async()
        dcresgrp_name = 'Common/App/Pod3'
        gt1 = self.nwa.create_general_dev(
            ok1, ng1, context, tenant_id,
            dcresgrp_name, vlan_name
        )
        gt1.wait()
        return results.get('success')

    def delete_general_dev(self, vlan_name):
        init_async()
        dcresgrp_name = 'Common/App/Pod3'
        gt1 = self.nwa.delete_general_dev(
            ok1, ng1, context, tenant_id,
            dcresgrp_name, vlan_name
        )
        gt1.wait()
        return results.get('success')

    def test_general_dev(self):
        params = [
            (5, ['dA', 'dB', 'dC', 'dD', 'dA']),
            (3, ['d1', 'd2', 'd3', 'd1']),
            (3, ['cA', 'dA', 'cA']),      # deleteでcreateが削除される
            (2, ['c1', 'd2', 'c1']),      # 名前が違うと削除されない
            (3, ['cB', 'dB', 'cC']),
            (4, ['cX', 'dX', 'cX', 'dX']),
            (6, ['c1', 'c2', 'd1', 'd2', 'c1', 'd1']),
            (2, ['cE', 'dE', 'dE', 'dE']),
        ]
        for count, vlan_names in params:
            yield self.check_general_dev, count, vlan_names

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.workflowinstance')
    @patch('neutron.plugins.necnwa.nwalib.client.RestClient.post')
    def check_general_dev(self, count, vlan_names, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCEED', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCEED'})

        post.reset_mock()
        for vlan_name in vlan_names:
            name = vlan_name[1:]
            LOG.info(name)
            if vlan_name.startswith('c'):
                eq_(self.create_general_dev(name)['http_status'], 200)
            else:
                eq_(self.delete_general_dev(name)['http_status'], 200)
        eq_(post.call_count, count)


class TestNwaClientCli(unittest.TestCase):
    '''Test code for Nwa Client in interactive.
    '''

    def setUp(self):
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
            eq_(rj, (500, None))
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_tenant(self):
        try:
            rj = self.nwa.create_tenant(tenant_id)
            eq_(rj, (200, {}))
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_tenant(self):
        try:
            rj = self.nwa.delete_tenant(tenant_id)
            eq_(rj, (200, {}))
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_tenant_nw(self):
        try:
            init_async()
            gt = self.nwa.create_tenant_nw(
                ok1, ng1, context, tenant_id, dc_resource_group_app1
            )
            gt.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            rd = rj['result']['resultdata']
            ok_(isinstance(rd, dict))
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_tenant_nw(self):
        try:
            init_async()
            gt = self.nwa.delete_tenant_nw(ok1, ng1, context, tenant_id)
            gt.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_vlan(self):
        try:
            init_async()
            ipaddr = '172.16.0.0'
            mask = 24
            gt1 = self.nwa.create_vlan(ok1, ng1, context, tenant_id, ipaddr, mask)
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            rd = rj.get('result')
            self.assertIsInstance(rd, dict)
            rd = rd.get('resultdata')
            eq_(rd.get('VlanIPSubnet'), ipaddr)
            eq_(rd.get('VlanSubnetMask'), '255.255.255.0')
            logical_name = rd.get('LogicalNWName')
            self.assertIsInstance(logical_name, basestring)
            self.assertGreater(len(logical_name), 1)
            self.business_vlan_name = logical_name
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_vlan(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            gt2 = self.nwa.delete_vlan(ok1, ng1, context, tenant_id, vlan_name)
            gt2.wait()
            rj2 = results.get('success')
            self.assertIsInstance(rj2, dict)
            rd2 = rj2.get('result')
            self.assertIsInstance(rd2, dict)
            rd2 = rd2.get('resultdata')
            self.assertIsInstance(rd2.get('NWAResult'), basestring)
            self.assertGreater(len(rd2.get('NWAResult')), 1)
            self.business_vlan_name = None
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_tenant_fw(self):
        try:
            init_async()
            vlan_devaddr = '172.16.0.254'
            vlan_name = self.business_vlan['VLAN'][0]['LogicalName']
            vlan_type = 'BusinessVLAN'
            gt1 = self.nwa.create_tenant_fw(
                ok1, ng1, context, tenant_id,
                dc_resource_group_app1,
                vlan_devaddr, vlan_name, vlan_type
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_update_tenant_fw(self):
        try:
            init_async()
            device_name = 'TFW0'
            device_type = 'TFW'
            vlan_name = self.business_vlan['VLAN'][0]['LogicalName']
            vlan_type = 'BusinessVLAN'
            gt1 = self.nwa.update_tenant_fw(
                ok1, ng1, context, tenant_id,
                device_name, device_type, vlan_name, vlan_type
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_tenant_fw(self):
        try:
            init_async()
            device_name = 'TFW0'
            device_type = 'TFW'
            gt1 = self.nwa.delete_tenant_fw(
                ok1, ng1, context, tenant_id,
                device_name, device_type
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_update_nat(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            vlan_type = 'BusinessVLAN'
            local_ip = '172.16.0.5'
            global_ip = '10.0.4.5'
            fw_name = 'TFW78'
            gt1 = self.nwa.update_nat(
                ok1, ng1, context, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip, fw_name
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_setting_nat(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            vlan_type = 'BusinessVLAN'
            local_ip = '172.16.0.5'
            global_ip = '10.0.4.5'
            fw_name = 'TFW78'
            gt1 = self.nwa.setting_nat(
                ok1, ng1, context, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip, fw_name
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_nat(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            vlan_type = 'BusinessVLAN'
            local_ip = '172.16.0.5'
            global_ip = '10.0.0.5'
            fw_name = 'TFW78'
            gt1 = self.nwa.delete_nat(
                ok1, ng1, context, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip, fw_name
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_setting_fw_policy_async(self):
        try:
            init_async()
            fw_name = 'TFW80'
            props = {}
            gt1 = self.nwa.setting_fw_policy_async(
                ok1, ng1, context, tenant_id,
                fw_name, props
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_create_general_dev(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            gt1 = self.nwa.create_general_dev(
                ok1, ng1, context, tenant_id,
                dc_resource_group_pod1,
                vlan_name, 'BusinessVLAN'
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')

    @unittest.skipIf(nwasim_noactive, '')
    def test_delete_general_dev(self):
        try:
            init_async()
            vlan_name = self.business_vlan_name
            gt1 = self.nwa.delete_general_dev(
                ok1, ng1, context, tenant_id,
                dc_resource_group_pod1,
                vlan_name, 'BusinessVLAN'
            )
            gt1.wait()
            rj = results.get('success')
            self.assertIsInstance(rj, dict)
            eq_(rj['http_status'], 200)
            eq_(rj['result']['status'], 'SUCCEED')
        except:
            ok_(False, 'Exception occured')


class TestUtNwaClient(unittest.TestCase):
    '''Unit test for NwaClient
    '''

    def setUp(self):
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


class TestSendQueueIsNotEmpty(unittest.TestCase):
    def test_send_queue_is_not_empty(self):
        rb = send_queue_is_not_empty()
        ok_(rb is False)


class TestConfig(unittest.TestCase):
    '''Unit test for NwaClient config.
    '''
    def setUp(self):
        from os.path import dirname, realpath, abspath
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
