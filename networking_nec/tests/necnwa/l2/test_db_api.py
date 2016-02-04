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

from neutron import context
from neutron.tests import base
from neutron.tests.unit import testlib_api
from oslo_log import log as logging

from networking_nec.plugins.necnwa.l2 import db_api

LOG = logging.getLogger(__name__)

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


class TestAddNwaTenantBinding(base.BaseTestCase):

    def setUp(self):
        super(TestAddNwaTenantBinding, self).setUp()
        self.session = MagicMock()

    def test_add_nwa_tenant_binding_json_is_none(self):
        rc = db_api.add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, None
        )
        self.assertFalse(rc)

    def test_add_nwa_tenant_binding_tenant_id_no_match(self):
        self.session.query().filter().all = MagicMock(return_value=[1, 2])
        rc = db_api.add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, JSON_VALUE
        )
        self.assertFalse(rc)

    def test_add_nwa_tenant_binding(self):
        self.session.reset_mock()
        self.session.query().filter().all.return_value = []
        rc = db_api.add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, JSON_VALUE
        )
        self.assertTrue(rc)
        self.assertEqual(self.session.add.call_count, 1)

    def test_add_nwa_tenant_binding_2(self):
        self.session.reset_mock()
        self.session.query().filter().all.return_value = []
        rc = db_api.add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID,
            {'a': 1, 'b': 2}
        )
        self.assertTrue(rc)
        self.assertEqual(self.session.add.call_count, 2)

    def test_add_nwa_tenant_binding_no_result_found(self):
        self.session.query().filter().all.side_effect = NoResultFound
        rc = db_api.add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, JSON_VALUE
        )
        self.assertFalse(rc)


class TestChgValue(base.BaseTestCase):
    def test_chg_value(self):
        rb = db_api.chg_value('CreateTenant', "True")
        self.assertTrue(rb)

        rb = db_api.chg_value('CreateTenantNW', "False")
        self.assertFalse(rb)


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


class TestGetNwaTenantBindingByTid(base.BaseTestCase):
    def setUp(self):
        super(TestGetNwaTenantBindingByTid, self).setUp()
        self.session = MagicMock()

    def test_get_nwa_tenant_binding_by_tid(self):
        self.session.query().filter().all = MagicMock(return_value=MagicMock())
        rc = db_api.get_nwa_tenant_binding_by_tid(self.session, MagicMock())
        self.assertIsNone(rc)

    def test_get_nwa_tenant_binding_by_tid_1(self):
        nwa = MagicMock()
        nwa.json_key, nwa.json_value = 'a', 1
        self.session.query().filter().all.return_value = [nwa]
        rc = db_api.get_nwa_tenant_binding_by_tid(self.session, TENANT_ID)
        self.assertEqual(rc.value_json, {'a': 1})

    def test_get_nwa_tenant_binding_by_tid_no_result_found(self):
        self.session.query().filter().all.side_effect = NoResultFound
        rc = db_api.get_nwa_tenant_binding_by_tid(self.session, TENANT_ID)
        self.assertIsNone(rc)


class TestSetNwaTenantBinding(base.BaseTestCase):
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def check_set_nwa_tenant_binding(self, param, gntb):
        self.session = MagicMock()
        gntb.return_value = param['old_value_json']
        rc = db_api.set_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, param['new_value_json']
        )
        self.assertEqual(rc, param['return'])
        if 'call_count_update' in param:
            self.assertEqual(self.session.query().filter().one.call_count,
                             param['call_count_update'])
        if 'call_count_insert' in param:
            self.assertEqual(self.session.execute.call_count,
                             param['call_count_insert'])
        if 'call_count_delete' in param:
            self.assertEqual(self.session.delete.call_count,
                             param['call_count_delete'])

    def test_set_nwa_tenant_binding(self):
        test_params = [
            {
                'return': False,
                'old_value_json': None,
                'new_value_json': None
            },
            {
                'return': False,
                'old_value_json': itemval(1),
                'new_value_json': None
            },
            {
                'return': False,
                'old_value_json': itemval({'a': 1}),
                'new_value_json': None
            },
            {
                # same key, same value
                'return': True,
                'old_value_json': itemval({'a': 1}),
                'new_value_json': {'a': 1},
                'call_count_update': 0,
                'call_count_insert': 0,
                'call_count_delete': 0
            },
            {
                # same key, same value (True, "True") XXX
                'return': True,
                'old_value_json': itemval({'a': "True"}),
                'new_value_json': {'a': True},
                'call_count_update': 1,
                'call_count_insert': 0,
                'call_count_delete': 0
            },
            {
                # same key, same value (ignore case)
                'return': True,
                'old_value_json': itemval({'A': 1}),
                'new_value_json': {'a': 1},
                'call_count_update': 1,
                'call_count_insert': 1,
                'call_count_delete': 1
            },
            {
                # same key, different value
                'return': True,
                'old_value_json': itemval({'a': 1}),
                'new_value_json': {'a': 2},
                'call_count_update': 1,
                'call_count_insert': 0,
                'call_count_delete': 0
            },
            {
                # diffrent key
                'return': True,
                'old_value_json': itemval({'a': 1}),
                'new_value_json': {'b': 2},
                'call_count_update': 1,
                'call_count_insert': 1,
                'call_count_delete': 1
            },
            {
                # diffrent key, multiple
                'return': True,
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
            },
        ]
        for param in test_params:
            self.check_set_nwa_tenant_binding(param)


class TestDelNwaTenantBinding(base.BaseTestCase):
    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def check_del_nwa_tenant_binding(self, param, gntb):
        self.session = MagicMock()
        gntb.return_value = param['old_value_json']
        rc = db_api.del_nwa_tenant_binding(self.session, TENANT_ID,
                                           NWA_TENANT_ID)
        self.assertEqual(rc, param['return'])

    def test_del_nwa_tenant_binding(self):
        test_params = [
            {
                'return': False,
                'old_value_json': None
            },
            {
                'return': True,
                'old_value_json': 1
            }
        ]
        for param in test_params:
            self.check_del_nwa_tenant_binding(param)

    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test_del_nwa_tenant_binding_no_result_found(self, gntb):
        gntb.return_value = 1
        self.session = MagicMock()
        self.session.query().filter().delete.side_effect = NoResultFound
        rc = db_api.del_nwa_tenant_binding(self.session, TENANT_ID,
                                           NWA_TENANT_ID)
        self.assertFalse(rc)


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
