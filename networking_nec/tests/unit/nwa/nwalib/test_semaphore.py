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

from networking_nec.plugins.necnwa.nwalib import semaphore as nwa_sem


class TestThread(base.BaseTestCase):
    def test_stop(self):
        t1 = nwa_sem.Thread(mock.MagicMock())
        t1.stop()

    def test_wait(self):
        t1 = nwa_sem.Thread(mock.MagicMock())
        t1.wait()


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

    def _check_push_history(self, param):
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
        post1 = mock.MagicMock()
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
            self._check_push_history(param)
