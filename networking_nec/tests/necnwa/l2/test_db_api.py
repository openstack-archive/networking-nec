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

from neutron.tests import base
from oslo_log import log as logging

from networking_nec.plugins.necnwa.l2.db_api import add_nwa_tenant_binding
from networking_nec.plugins.necnwa.l2.db_api import chg_value
from networking_nec.plugins.necnwa.l2.db_api import del_nwa_tenant_binding
from networking_nec.plugins.necnwa.l2.db_api import ensure_port_binding
from networking_nec.plugins.necnwa.l2.db_api import get_nwa_tenant_binding
from networking_nec.plugins.necnwa.l2.db_api \
    import get_nwa_tenant_binding_by_tid
from networking_nec.plugins.necnwa.l2.db_api import set_nwa_tenant_binding
from networking_nec.plugins.necnwa.l2.db_api import update_json_nwa_tenant_id
from networking_nec.plugins.necnwa.l2.db_api \
    import update_json_post_CreateGeneralDev
from networking_nec.plugins.necnwa.l2.db_api \
    import update_json_post_CreateTenantFW
from networking_nec.plugins.necnwa.l2.db_api \
    import update_json_post_CreateTenantNW
from networking_nec.plugins.necnwa.l2.db_api \
    import update_json_post_CreateVLAN
from networking_nec.plugins.necnwa.l2.db_api \
    import update_json_post_SettingNAT
from networking_nec.plugins.necnwa.l2.db_api \
    import update_json_post_UpdateTenantFW
from networking_nec.plugins.necnwa.l2.db_api import update_json_vlanid

# the below code is required to load test scenarios.
# If a test class has 'scenarios' attribute,
# tests are multiplied depending on their 'scenarios' attribute.
# This can be assigned to 'load_tests' in any test module to make this
# automatically work across tests in the module.
# For more details, see testscenarios document.
load_tests = testscenarios.load_tests_apply_scenarios

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
        rc = add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, None
        )
        self.assertFalse(rc)

    def test_add_nwa_tenant_binding_tenant_id_no_match(self):
        self.session.query().filter().all = MagicMock(return_value=[1, 2])
        rc = add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, JSON_VALUE
        )
        self.assertFalse(rc)

    def test_add_nwa_tenant_binding(self):
        self.session.reset_mock()
        self.session.query().filter().all.return_value = []
        rc = add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, JSON_VALUE
        )
        self.assertTrue(rc)
        self.assertEqual(self.session.add.call_count, 1)

    def test_add_nwa_tenant_binding_2(self):
        self.session.reset_mock()
        self.session.query().filter().all.return_value = []
        rc = add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID,
            {'a': 1, 'b': 2}
        )
        self.assertTrue(rc)
        self.assertEqual(self.session.add.call_count, 2)

    def test_add_nwa_tenant_binding_no_result_found(self):
        self.session.query().filter().all.side_effect = NoResultFound
        rc = add_nwa_tenant_binding(
            self.session, TENANT_ID, NWA_TENANT_ID, JSON_VALUE
        )
        self.assertFalse(rc)


class TestChgValue(base.BaseTestCase):
    def test_chg_value(self):
        rb = chg_value('CreateTenant', "True")
        self.assertTrue(rb)

        rb = chg_value('CreateTenantNW', "False")
        self.assertFalse(rb)


class TestGetNwaTenantBinding(base.BaseTestCase):
    def setUp(self):
        super(TestGetNwaTenantBinding, self).setUp()
        self.session = MagicMock()

    def test_get_nwa_tenant_binding(self):
        self.session.query().filter().filter().all.return_value = []
        rc = get_nwa_tenant_binding(self.session, TENANT_ID, NWA_TENANT_ID)
        self.assertIsNone(rc)

    def test_get_nwa_tenant_binding_1(self):
        nwa = MagicMock()
        nwa.json_key, nwa.json_value = 'a', 1
        self.session.query().filter().filter().all.return_value = [nwa]
        rc = get_nwa_tenant_binding(self.session, TENANT_ID, NWA_TENANT_ID)
        self.assertEqual(rc.value_json, {'a': 1})

    def test_get_nwa_tenant_binding_no_result_found(self):
        self.session.query().filter().filter().all.side_effect = NoResultFound
        rc = get_nwa_tenant_binding(self.session, TENANT_ID, NWA_TENANT_ID)
        self.assertIsNone(rc)


class TestGetNwaTenantBindingByTid(base.BaseTestCase):
    def setUp(self):
        super(TestGetNwaTenantBindingByTid, self).setUp()
        self.session = MagicMock()

    def test_get_nwa_tenant_binding_by_tid(self):
        self.session.query().filter().all = MagicMock(return_value=MagicMock())
        rc = get_nwa_tenant_binding_by_tid(self.session, MagicMock())
        self.assertIsNone(rc)

    def test_get_nwa_tenant_binding_by_tid_1(self):
        nwa = MagicMock()
        nwa.json_key, nwa.json_value = 'a', 1
        self.session.query().filter().all.return_value = [nwa]
        rc = get_nwa_tenant_binding_by_tid(self.session, TENANT_ID)
        self.assertEqual(rc.value_json, {'a': 1})

    def test_get_nwa_tenant_binding_by_tid_no_result_found(self):
        self.session.query().filter().all.side_effect = NoResultFound
        rc = get_nwa_tenant_binding_by_tid(self.session, TENANT_ID)
        self.assertIsNone(rc)


class TestSetNwaTenantBinding(base.BaseTestCase):

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
             # diffrent key
             'expected_return_value': True,
             'old_value_json': itemval({'a': 1}),
             'new_value_json': {'b': 2},
             'call_count_update': 1,
             'call_count_insert': 1,
             'call_count_delete': 1
         }),
        ('old and new json has multiple different keys',
         {
             # diffrent key, multiple
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

    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test_set_nwa_tenant_binding(self, gntb):

        self.session = MagicMock()
        gntb.return_value = self.old_value_json
        rc = set_nwa_tenant_binding(
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


class TestDelNwaTenantBinding(base.BaseTestCase):

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

    @patch('networking_nec.plugins.necnwa.l2.db_api.get_nwa_tenant_binding')
    def test_del_nwa_tenant_binding(self, gntb):
        gntb.return_value = self.old_value_json
        self.session = MagicMock()
        if getattr(self, 'delete_not_found', False):
            self.session.query().filter().delete.side_effect = NoResultFound
        rc = del_nwa_tenant_binding(self.session, TENANT_ID, NWA_TENANT_ID)
        self.assertEqual(rc, self.expected_return_value)


class TestUpdateJsonNwaTenantId(base.BaseTestCase):
    def test_update_json_nwa_tenant_id(self):
        update_json_nwa_tenant_id(VALUE_JSON, NWA_TENANT_ID)


class TestUpdateJsonPostCreateTenantNW(base.BaseTestCase):
    def test_update_json_post__create_tenant_n_w(self):
        update_json_post_CreateTenantNW(VALUE_JSON)


class TestUpdateJsonVlanid(base.BaseTestCase):
    def test_update_json_vlanid(self):
        update_json_vlanid(
            VALUE_JSON, NETWORK_ID, PHYSICAL_NETWORK, 2, 302
        )


class TestUpdateJsonPostCreateVLAN(base.BaseTestCase):
    def test_update_json_post__create_vla_n(self):
        update_json_post_CreateVLAN(
            VALUE_JSON, NETWORK_ID, NETWORK_NAME,
            'uuid-subnet_id', CIDR,
            'PUBLICVLAN_102',
            PHYSICAL_NETWORK, 1, 201
        )


class TestUpdateJsonPostCreateTenantFW(base.BaseTestCase):
    def test_update_json_post__create_tenant_f_w(self):
        update_json_post_CreateTenantFW(
            VALUE_JSON, NETWORK_ID, NETWORK_NAME, PHYSICAL_NETWORK,
            2, 202, DEVICE_ID, DEVICE_OWNER,
            'T1',
            IP_ADDRESS, MAC_ADDRESS
        )


class TestUpdateJsonPostUpdateTenantFW(base.BaseTestCase):
    def test_update_json_post__update_tenant_f_w(self):
        update_json_post_UpdateTenantFW(
            VALUE_JSON, NETWORK_ID, NETWORK_NAME, PHYSICAL_NETWORK,
            3, 203, DEVICE_ID, IP_ADDRESS, MAC_ADDRESS
        )


class TestUpdateJsonPostCreateGeneralDev(base.BaseTestCase):
    def test_update_json_post__create_general_dev(self):
        update_json_post_CreateGeneralDev(
            VALUE_JSON, PHYSICAL_NETWORK, 4, NETWORK_ID, 204
        )


class TestUpdateJsonPostSettingNAT(base.BaseTestCase):
    def test_update_json_post__setting_na_t(self):
        update_json_post_SettingNAT(
            VALUE_JSON, DEVICE_ID,
            'uuid-fip-1',
            'uuid-network_id-1',
            '192.168.123.45',
            '192.168.123.46'
        )


class TestEnsurePortBinding(base.BaseTestCase):
    def setUp(self):
        super(TestEnsurePortBinding, self).setUp()
        self.session = MagicMock()

    def test_ensure_port_binding(self):
        port_id = 'uuid-port_id-1'
        self.session.query().filter_by().one.return_value = port_id
        rc = ensure_port_binding(self.session, port_id)
        self.assertEqual(rc, port_id)

    @patch('neutron.plugins.ml2.models.PortBinding')
    def test_ensure_port_binding_no_result_found(self, mpb):
        port_id = 'uuid-port_id-1'
        self.session.query().filter_by().one.side_effect = NoResultFound
        mpb.return_value = 'uuid-port_id-2'
        self.assertRaises(
            NoResultFound,
            ensure_port_binding, self.session, port_id
        )
