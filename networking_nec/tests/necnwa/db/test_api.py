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

import logging
from sqlalchemy.orm.exc import NoResultFound
from mock import patch, MagicMock  # noqa
from neutron.tests import base

from networking_nec.plugins.necnwa.db.api import (  # noqa
    add_nwa_tenant_binding,
    chg_value,
    del_nwa_tenant_binding,
    get_nwa_tenant_binding,
    get_nwa_tenant_binding_by_tid,
    set_nwa_tenant_binding,
    update_json_nwa_tenant_id,
    update_json_post_CreateGeneralDev,
    update_json_post_CreateTenantFW,
    update_json_post_CreateTenantNW,
    update_json_post_CreateVLAN,
    update_json_post_SettingNAT,
    update_json_post_UpdateTenantFW,
    update_json_vlanid,
    ensure_port_binding,
)

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

session = MagicMock()
tenant_id = 'T1'
nwa_tenant_id = 'NWA-T1'
json_value = {'a': 1}
value_json = {'a': 1}
network_id = 'uuid-network_id-1'
device_id = 'uuid-device_id-1'
physical_network = 'DC1/Pod1-1'
network_name = 'PublicVLAN_1001'
device_owner = 'network:router_interface'
ip_address = '10.0.0.1'
mac_address = '12:34:56:78:9a'
cidr = 24


class itemval(base.BaseTestCase):
    value_json = None

    def __init__(self, v):
        self.value_json = v

    def __repr__(self):
        return str(self.value_json)


def setup():
    global session
    session = MagicMock()


class TestAddNwaTenantBinding(base.BaseTestCase):
    def test_add_nwa_tenant_binding_json_is_none(self):
        rc = add_nwa_tenant_binding(session, tenant_id, nwa_tenant_id, None)
        self.assertEqual(rc, False)

    def test_add_nwa_tenant_binding_tenant_id_no_match(self):
        session.query().filter().all = MagicMock(return_value=[1, 2])
        rc = add_nwa_tenant_binding(
            session, tenant_id, nwa_tenant_id, json_value
        )
        self.assertEqual(rc, False)

    def test_add_nwa_tenant_binding(self):
        session.reset_mock()
        session.query().filter().all.return_value = []
        rc = add_nwa_tenant_binding(
            session, tenant_id, nwa_tenant_id, json_value
        )
        self.assertEqual(rc, True)
        self.assertEqual(session.add.call_count, 1)

    def test_add_nwa_tenant_binding_2(self):
        session.reset_mock()
        session.query().filter().all.return_value = []
        rc = add_nwa_tenant_binding(
            session, tenant_id, nwa_tenant_id,
            {'a': 1, 'b': 2}
        )
        self.assertEqual(rc, True)
        self.assertEqual(session.add.call_count, 2)

    def test_add_nwa_tenant_binding_no_result_found(self):
        session.query().filter().all.side_effect = NoResultFound
        rc = add_nwa_tenant_binding(
            session, tenant_id, nwa_tenant_id, json_value
        )
        self.assertEqual(rc, False)


class TestChgValue(base.BaseTestCase):
    def test_chg_value(self):
        rb = chg_value('CreateTenant', "True")
        self.assertEqual(rb, True)

        rb = chg_value('CreateTenantNW', "False")
        self.assertEqual(rb, False)


class TestGetNwaTenantBinding(base.BaseTestCase):
    def test_get_nwa_tenant_binding(self):
        session.query().filter().filter().all.return_value = []
        rc = get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
        self.assertEqual(rc, None)

    def test_get_nwa_tenant_binding_1(self):
        nwa = MagicMock()
        nwa.json_key, nwa.json_value = 'a', 1
        session.query().filter().filter().all.return_value = [nwa]
        rc = get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
        self.assertEqual(rc.value_json, {'a': 1})

    def test_get_nwa_tenant_binding_no_result_found(self):
        session.query().filter().filter().all.side_effect = NoResultFound
        rc = get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
        self.assertEqual(rc, None)


class TestGetNwaTenantBindingByTid(base.BaseTestCase):
    def test_get_nwa_tenant_binding_by_tid(self):
        session.query().filter().all = MagicMock(return_value=MagicMock())
        rc = get_nwa_tenant_binding_by_tid(session, MagicMock())
        self.assertEqual(rc, None)

    def test_get_nwa_tenant_binding_by_tid_1(self):
        nwa = MagicMock()
        nwa.json_key, nwa.json_value = 'a', 1
        session.query().filter().all.return_value = [nwa]
        rc = get_nwa_tenant_binding_by_tid(session, tenant_id)
        self.assertEqual(rc.value_json, {'a': 1})

    def test_get_nwa_tenant_binding_by_tid_no_result_found(self):
        session.query().filter().all.side_effect = NoResultFound
        rc = get_nwa_tenant_binding_by_tid(session, tenant_id)
        self.assertEqual(rc, None)


class TestSetNwaTenantBinding(base.BaseTestCase):
    @patch('networking_nec.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def check_set_nwa_tenant_binding(self, param, gntb):
        session = MagicMock()
        gntb.return_value = param['old_value_json']
        rc = set_nwa_tenant_binding(
            session, tenant_id, nwa_tenant_id, param['new_value_json']
        )
        self.assertEqual(rc, param['return'])
        if 'call_count_update' in param:
            self.assertEqual(session.query().filter().one.call_count,
                             param['call_count_update'])
        if 'call_count_insert' in param:
            self.assertEqual(session.execute.call_count,
                             param['call_count_insert'])
        if 'call_count_delete' in param:
            self.assertEqual(session.delete.call_count,
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
            yield self.check_set_nwa_tenant_binding, param


class TestDelNwaTenantBinding(base.BaseTestCase):
    @patch('networking_nec.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def check_del_nwa_tenant_binding(self, param, gntb):
        session = MagicMock()
        gntb.return_value = param['old_value_json']
        rc = del_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
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
            yield self.check_del_nwa_tenant_binding, param

    @patch('networking_nec.plugins.necnwa.db.api.get_nwa_tenant_binding')
    def test_del_nwa_tenant_binding_no_result_found(self, gntb):
        gntb.return_value = 1
        session.query().filter().delete.side_effect = NoResultFound
        rc = del_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
        self.assertEqual(rc, False)


class TestUpdateJsonNwaTenantId(base.BaseTestCase):
    def test_update_json_nwa_tenant_id(self):
        update_json_nwa_tenant_id(value_json, nwa_tenant_id)


class TestUpdateJsonPostCreateTenantNW(base.BaseTestCase):
    def test_update_json_post__create_tenant_n_w(self):
        update_json_post_CreateTenantNW(value_json)


class TestUpdateJsonVlanid(base.BaseTestCase):
    def test_update_json_vlanid(self):
        update_json_vlanid(
            value_json, network_id, physical_network, 2, 302
        )


class TestUpdateJsonPostCreateVLAN(base.BaseTestCase):
    def test_update_json_post__create_vla_n(self):
        update_json_post_CreateVLAN(
            value_json, network_id, network_name,
            'uuid-subnet_id', cidr,
            'PublicVLAN_102',
            physical_network, 1, 201
        )


class TestUpdateJsonPostCreateTenantFW(base.BaseTestCase):
    def test_update_json_post__create_tenant_f_w(self):
        update_json_post_CreateTenantFW(
            value_json, network_id, network_name, physical_network,
            2, 202, device_id, device_owner,
            'T1',
            ip_address, mac_address
        )


class TestUpdateJsonPostUpdateTenantFW(base.BaseTestCase):
    def test_update_json_post__update_tenant_f_w(self):
        update_json_post_UpdateTenantFW(
            value_json, network_id, network_name, physical_network,
            3, 203, device_id, ip_address, mac_address
        )


class TestUpdateJsonPostCreateGeneralDev(base.BaseTestCase):
    def test_update_json_post__create_general_dev(self):
        update_json_post_CreateGeneralDev(
            value_json, physical_network, 4, network_id, 204
        )


class TestUpdateJsonPostSettingNAT(base.BaseTestCase):
    def test_update_json_post__setting_na_t(self):
        update_json_post_SettingNAT(
            value_json, device_id,
            'uuid-fip-1',
            'uuid-network_id-1',
            '192.168.123.45',
            '192.168.123.46'
        )


class TestEnsurePortBinding(base.BaseTestCase):
    def test_ensure_port_binding(self):
        port_id = 'uuid-port_id-1'
        session.query().filter_by().one.return_value = port_id
        rc = ensure_port_binding(session, port_id)
        self.assertEqual(rc, port_id)

    @patch('neutron.plugins.ml2.models.PortBinding')
    def test_ensure_port_binding_no_result_found(self, mpb):
        port_id = 'uuid-port_id-1'
        session.query().filter_by().one.side_effect = NoResultFound
        mpb.return_value = 'uuid-port_id-2'
        self.assertRaises(
            NoResultFound,
            ensure_port_binding, session, port_id
        )
