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

from networking_nec.nwa.nwalib import workflow


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

    def test_update_nameid(self):
        with mock.patch('networking_nec.nwa.nwalib.workflow'
                        '.NwaWorkflow._nameid',
                        new_callable=mock.PropertyMock) as nameid, \
                mock.patch('networking_nec.nwa.nwalib.workflow'
                           '.NwaWorkflow._nameid_initialized',
                           new_callable=mock.PropertyMock):

            # When nameid is initialized, nameid will be unchanged.
            workflow.NwaWorkflow._nameid_initialized = True
            nameid.return_value = mock.sentinel.nameid
            workflow.NwaWorkflow.update_nameid({'foo': '1'})
            self.assertTrue(workflow.NwaWorkflow._nameid_initialized)
            self.assertIs(mock.sentinel.nameid, workflow.NwaWorkflow._nameid)

            # If passed nameid is empty, nameid will be unchanged.
            workflow.NwaWorkflow._nameid_initialized = False
            nameid.return_value = mock.sentinel.nameid
            workflow.NwaWorkflow.update_nameid({})
            self.assertFalse(workflow.NwaWorkflow._nameid_initialized)
            self.assertIs(mock.sentinel.nameid, workflow.NwaWorkflow._nameid)

            # If nameid is not initialized and passed nameid is not empty,
            # nameid will be initialized.
            workflow.NwaWorkflow._nameid_initialized = False
            workflow.NwaWorkflow.update_nameid({'foo': '1'})
            self.assertTrue(workflow.NwaWorkflow._nameid_initialized)
            self.assertDictEqual({'foo': '1'}, workflow.NwaWorkflow._nameid)
