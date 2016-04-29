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

from mock import MagicMock
from mock import patch
from sqlalchemy.orm.exc import NoResultFound
import testscenarios

from neutron import context
from neutron.tests import base
from neutron.tests.unit import testlib_api

from networking_nec.nwa.l2 import db_api

TENANT_ID = 'T1'
NWA_TENANT_ID = 'NWA-T1'
JSON_VALUE = {'a': 1}
VALUE_JSON = {'a': 1}
NETWORK_ID = 'uuid-network_id-1'
DEVICE_ID = 'uuid-device_id-1'
PHYSICAL_NETWORK = 'DC1/Pod1-1'
NETWORK_NAME = 'PublicVLAN_1001'
DEVICE_OWNER = 'network:router_interface'
IP_ADDRESS = '10.0.0.1'
MAC_ADDRESS = '12:34:56:78:9a'
CIDR = 24


class itemval(base.BaseTestCase):
    value_json = None

    def __init__(self, v):
        self.value_json = v

    def __repr__(self):
        return str(self.value_json)


class TestNWATenantBinding(base.BaseTestCase):
    def test_nwa_tenant_binding(self):
        ntb = db_api.NWATenantBinding('T1', 'NWA-T1', {'key': 'value'})
        self.assertIsNotNone(ntb)
        self.assertEqual(str(ntb),
                         "<TenantBinding(T1,NWA-T1,{'key': 'value'})>")


class TestAddNwaTenantBinding(testlib_api.SqlTestCaseLight):
    nwa_tenant1 = 'NWA01'
    nwa_tenant2 = 'NWA02'
    tenant1 = 'ffffffffff0000000000000000000001'
    tenant2 = 'ffffffffff0000000000000000000002'
    key1 = 'Key-1'
    key2 = 'Key-2'
    value1 = 'Value-1'
    value2 = 'Value-2'
    value_json1 = {key1: value1}
    value_json2 = {key2: value2}

    def setUp(self):
        super(TestAddNwaTenantBinding, self).setUp()
        self.ssn = context.get_admin_context().session

    def get_t1(self):
        return db_api.get_nwa_tenant_binding(
            self.ssn, self.tenant1, self.nwa_tenant1)

    def add_t1(self, value_json):
        return db_api.add_nwa_tenant_binding(
            self.ssn, self.tenant1, self.nwa_tenant1, value_json)

    def del_t1(self):
        return db_api.del_nwa_tenant_binding(
            self.ssn, self.tenant1, self.nwa_tenant1)

    def test_add_del(self):
        self.assertIsNone(self.get_t1())  # not found
        self.assertTrue(self.add_t1(self.value_json1))

        # already added
        self.assertFalse(self.add_t1(self.value_json2))
        self.assertEqual(self.get_t1().value_json, self.value_json1)

        self.assertTrue(self.del_t1())
        # already deleted
        self.assertFalse(self.del_t1())
        self.assertIsNone(self.get_t1())

    def test_add_del_tenant_id_difference(self):
        self.assertIsNone(self.get_t1())  # not found
        self.assertTrue(self.add_t1(self.value_json1))

        self.assertFalse(       # already exits
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant2,
                self.value_json2))
        self.assertTrue(        # diffrent tenant id
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant1,
                self.value_json2))

        self.assertEqual(self.get_t1().value_json, self.value_json1)
        self.assertEqual(
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant1).value_json,
            self.value_json2)

        self.assertTrue(self.del_t1())
        self.assertEqual(       # no effect
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant1).value_json,
            self.value_json2)

    def test_tenant_id_no_match(self):
        self.assertIsNone(self.get_t1())  # not found
        self.assertTrue(        # succeed
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant1,
                {self.key1: self.value1}))
        self.assertFalse(       # not found
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant1))
        self.assertEqual(       # get same value
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant1).value_json,
            {self.key1: self.value1})

    def test_nwa_tenant_id_no_match(self):
        self.assertIsNone(self.get_t1())  # not found
        self.assertTrue(        # succeed
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant2,
                {self.key2: self.value2}))
        self.assertFalse(       # not found
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant1))
        self.assertEqual(       # get same value
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant2).value_json,
            {self.key2: self.value2})

    def test_value_is_empty_string(self):
        self.assertTrue(
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant1, {self.key1: ''}))
        self.assertEqual(
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant1).value_json,
            {self.key1: ''})

    def test_value_is_none(self):
        self.assertTrue(
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant1, {self.key1: None}))
        self.assertEqual(
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant1).value_json,
            {self.key1: u''})

    def test_value_is_true(self):
        self.assertTrue(
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant1, {self.key1: True}))
        self.assertEqual(
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant1).value_json,
            {self.key1: True})

    def test_value_is_false(self):
        self.assertTrue(
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant2, {self.key1: False}))
        self.assertEqual(
            db_api.get_nwa_tenant_binding(
                self.ssn, self.tenant2, self.nwa_tenant2).value_json,
            {self.key1: False})

    def test_json_value_not_dict(self):
        self.assertFalse(
            db_api.add_nwa_tenant_binding(
                self.ssn, self.tenant1, self.nwa_tenant1,
                [self.value1, self.value2]))    # list


class TestGetNwaTenantBinding(base.BaseTestCase):
    def setUp(self):
        super(TestGetNwaTenantBinding, self).setUp()
        self.session = MagicMock()

    def test_get_nwa_tenant_binding(self):
        self.session.query().filter().filter().all.return_value = []
        rc = db_api.get_nwa_tenant_binding(self.session,
                                           TENANT_ID, NWA_TENANT_ID)
        self.assertIsNone(rc)

    def test_get_nwa_tenant_binding_1(self):
        nwa = MagicMock()
        nwa.json_key, nwa.json_value = 'a', 1
        self.session.query().filter().filter().all.return_value = [nwa]
        rc = db_api.get_nwa_tenant_binding(self.session,
                                           TENANT_ID, NWA_TENANT_ID)
        self.assertEqual(rc.value_json, {'a': 1})

    def test_get_nwa_tenant_binding_no_result_found(self):
        self.session.query().filter().filter().all.side_effect = NoResultFound
        rc = db_api.get_nwa_tenant_binding(self.session,
                                           TENANT_ID, NWA_TENANT_ID)
        self.assertIsNone(rc)


class TestSetNwaTenantBinding(testscenarios.WithScenarios, base.BaseTestCase):

    scenarios = [
        ('old new json None',
         {
             'expected_return_value': False,
             'old_value_json': None,
             'new_value_json': None
         }),
        ('old json is 1 and new json is None',
         {
             'expected_return_value': False,
             'old_value_json': itemval(1),
             'new_value_json': None
         }),
        ('old json is dict and new json is None',
         {
             'expected_return_value': False,
             'old_value_json': itemval({'a': 1}),
             'new_value_json': None
         }),
        ('old and new json have same key and value',
         {
             # same key, same value
             'expected_return_value': True,
             'old_value_json': itemval({'a': 1}),
             'new_value_json': {'a': 1},
             'call_count_update': 0,
             'call_count_insert': 0,
             'call_count_delete': 0
         }),
        ('old and new json have same key and same value (True, "True")',
         {
             # same key, same value (True, "True") XXX
             'expected_return_value': True,
             'old_value_json': itemval({'a': "True"}),
             'new_value_json': {'a': True},
             'call_count_update': 1,
             'call_count_insert': 0,
             'call_count_delete': 0
         }),
        ('old and new json have same key (ignore case)',
         {
             # same key, same value (ignore case)
             'expected_return_value': True,
             'old_value_json': itemval({'A': 1}),
             'new_value_json': {'a': 1},
             'call_count_update': 1,
             'call_count_insert': 1,
             'call_count_delete': 1
         }),
        ('old and new json has same key and different value',
         {
             # same key, different value
             'expected_return_value': True,
             'old_value_json': itemval({'a': 1}),
             'new_value_json': {'a': 2},
             'call_count_update': 1,
             'call_count_insert': 0,
             'call_count_delete': 0
         }),
        ('old and new json has different keys',
         {
             # different key
             'expected_return_value': True,
             'old_value_json': itemval({'a': 1}),
             'new_value_json': {'b': 2},
             'call_count_update': 1,
             'call_count_insert': 1,
             'call_count_delete': 1
         }),
        ('old and new json has multiple different keys',
         {
             # different key, multiple
             'expected_return_value': True,
             'old_value_json': itemval({
                 'a': 0,
                 'b': 1
             }),
             'new_value_json': {
                 'b': 1,
                 'c': 2
             },
             'call_count_update': 1,
             'call_count_insert': 1,
             'call_count_delete': 1
         }),
        ]

    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_set_nwa_tenant_binding(self, gntb):

        self.session = MagicMock()
        gntb.return_value = self.old_value_json
        rc = db_api.set_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, self.new_value_json
        )
        self.assertEqual(rc, self.expected_return_value)
        if self.expected_return_value:
            self.assertEqual(self.session.query().filter().one.call_count,
                             self.call_count_update)
            self.assertEqual(self.session.execute.call_count,
                             self.call_count_insert)
            self.assertEqual(self.session.delete.call_count,
                             self.call_count_delete)


class TestDelNwaTenantBinding(testscenarios.WithScenarios, base.BaseTestCase):

    scenarios = [
        ('old value json is None',
         {
             'expected_return_value': False,
             'old_value_json': None
         }),
        ('old value json is 1',
         {
             'expected_return_value': True,
             'old_value_json': 1
         }),
        ('no result found',
         {
             'expected_return_value': False,
             'old_value_json': 1,
             'delete_not_found': True,
         }),
    ]

    @patch('networking_nec.nwa.l2.db_api.get_nwa_tenant_binding')
    def test_del_nwa_tenant_binding(self, gntb):
        gntb.return_value = self.old_value_json
        self.session = MagicMock()
        if getattr(self, 'delete_not_found', False):
            self.session.query().filter().delete.side_effect = NoResultFound
        rc = db_api.del_nwa_tenant_binding(self.session, TENANT_ID,
                                           NWA_TENANT_ID)
        self.assertEqual(rc, self.expected_return_value)


class TestEnsurePortBinding(base.BaseTestCase):
    def setUp(self):
        super(TestEnsurePortBinding, self).setUp()
        self.session = MagicMock()

    def test_ensure_port_binding(self):
        port_id = 'uuid-port_id-1'
        self.session.query().filter_by().one.return_value = port_id
        rc = db_api.ensure_port_binding(self.session, port_id)
        self.assertEqual(rc, port_id)

    @patch('neutron.plugins.ml2.models.PortBinding')
    def test_ensure_port_binding_no_result_found(self, mpb):
        port_id = 'uuid-port_id-1'
        self.session.query().filter_by().one.side_effect = NoResultFound
        mpb.return_value = 'uuid-port_id-2'
        self.assertRaises(
            NoResultFound,
            db_api.ensure_port_binding, self.session, port_id
        )


class TestTenantQueue(testlib_api.SqlTestCase):

    tenant1 = 'ffffffffff0000000000000000000001'
    tenant2 = 'ffffffffff0000000000000000000002'
    tenant3 = 'ffffffffff0000000000000000000003'

    def setUp(self):
        super(TestTenantQueue, self).setUp()
        self.ssn = context.get_admin_context().session

    def test_add_del_tenant_queue(self):
        ret = db_api.get_nwa_tenant_queue(self.ssn, self.tenant1)
        self.assertFalse(ret)  # not found
        ret = db_api.add_nwa_tenant_queue(self.ssn, self.tenant1)
        self.assertTrue(ret)  # succeed
        ret = db_api.add_nwa_tenant_queue(self.ssn, self.tenant1)
        self.assertFalse(ret)  # already registered
        ret = db_api.get_nwa_tenant_queue(self.ssn, self.tenant1)
        self.assertTrue(ret)  # item found
        ret = db_api.del_nwa_tenant_queue(self.ssn, self.tenant1)
        self.assertTrue(ret)  # delete succeed
        ret = db_api.del_nwa_tenant_queue(self.ssn, self.tenant1)
        self.assertFalse(ret)  # do nothing
        ret = db_api.get_nwa_tenant_queue(self.ssn, self.tenant1)
        self.assertFalse(ret)  # not found

    def test_add_tenant_queue_no_result_found(self):
        session = MagicMock()
        session.query().filter().all.side_effect = NoResultFound
        self.assertFalse(
            db_api.add_nwa_tenant_queue(session, self.tenant1))

    def test_add_tenant_queue_detail(self):
        ret = db_api.add_nwa_tenant_queue(
            self.ssn, self.tenant1, 'nwa_%s' % self.tenant1, topic='foo')
        self.assertTrue(ret)
        ret = db_api.get_nwa_tenant_queue(self.ssn, self.tenant1)
        self.assertEqual(self.tenant1, ret.tenant_id)
        self.assertEqual('nwa_%s' % self.tenant1, ret.nwa_tenant_id)
        self.assertEqual('foo', ret.topic)

        ret = db_api.add_nwa_tenant_queue(self.ssn, self.tenant2)
        self.assertTrue(ret)
        ret = db_api.get_nwa_tenant_queue(self.ssn, self.tenant2)
        self.assertEqual(self.tenant2, ret.tenant_id)
        self.assertEqual('', ret.nwa_tenant_id)
        self.assertEqual('', ret.topic)

    def test_get_tenant_queues(self):
        ret = db_api.get_nwa_tenant_queues(self.ssn)
        self.assertEqual(0, len(ret))

        self.assertTrue(db_api.add_nwa_tenant_queue(self.ssn, self.tenant1))
        self.assertTrue(db_api.add_nwa_tenant_queue(self.ssn, self.tenant2))
        self.assertTrue(db_api.add_nwa_tenant_queue(self.ssn, self.tenant3))

        ret = db_api.get_nwa_tenant_queues(self.ssn)
        self.assertEqual(3, len(ret))

        self.assertTrue(db_api.del_nwa_tenant_queue(self.ssn, self.tenant1))

        ret = db_api.get_nwa_tenant_queues(self.ssn)
        self.assertEqual(2, len(ret))

        self.assertTrue(db_api.del_nwa_tenant_queue(self.ssn, self.tenant2))
        self.assertTrue(db_api.del_nwa_tenant_queue(self.ssn, self.tenant3))

        ret = db_api.get_nwa_tenant_queues(self.ssn)
        self.assertEqual(0, len(ret))
