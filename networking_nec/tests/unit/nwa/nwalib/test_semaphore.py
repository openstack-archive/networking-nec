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

from networking_nec.nwa.nwalib import semaphore as nwa_sem


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
