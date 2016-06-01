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
from sqlalchemy.orm import exc as sa_exc

from neutron.common import exceptions as n_exc
from neutron.tests import base

from networking_nec.nwa.l3.plugin import NECNWAL3Plugin


class TestNECNWAL3Plugin(base.BaseTestCase):

    @patch('neutron.services.l3_router.l3_router_plugin.'
           'L3RouterPlugin.__init__')
    def setUp(self, l3p):
        super(TestNECNWAL3Plugin, self).setUp()
        self.plg = NECNWAL3Plugin()
        self.context = MagicMock()
        self.floating = {
            'floating_ip_address': '172.16.0.107',
            'fixed_ip_address': '192.168.120.107',
            'router_id': 'uuid-router_id-107',
            'floating_network_id': 'uuid-network_id-107',
            'tenant_id': 'T-107',
            'floating_port_id': 'uuid-floating_port_id-107',
        }

    @patch('neutron.db.l3_db.L3_NAT_db_mixin.create_floatingip')
    def test_create_floatingip(self, cfip):
        floatingip = MagicMock()
        cfip.return_value = 0
        rc = self.plg.create_floatingip(self.context, floatingip)
        self.assertEqual(rc, 0)

    @patch('neutron.db.l3_db.L3_NAT_db_mixin.update_floatingip')
    @patch('networking_nec.nwa.l3_plugin.NECNWAL3Plugin._delete_nat')
    @patch('neutron.services.l3_router.l3_router_plugin.'
           'L3RouterPlugin.update_floatingip')
    def _test_update_floatingip(self, ufip, ndn, nsn):
        floatingip = {
            'floatingip': {
                'port_id': None
            }
        }
        fid = 'uuid-fid-100'
        ufip.return_value = 0
        self.context.session.query().filter_by().one.return_value = \
            self.floating
        rc = self.plg.update_floatingip(self.context, fid, floatingip)
        self.assertEqual(rc, 0)

        floatingip = {
            'floatingip': {
                'port_id': 'uuid-port_id-101'
            }
        }
        rc = self.plg.update_floatingip(self.context, fid, floatingip)
        self.assertEqual(rc, 0)

        floatingip = {
            'floatingip': {
                'port_id1': 'uuid-port_id-102'
            }
        }
        rc = self.plg.update_floatingip(self.context, fid, floatingip)
        self.assertEqual(rc, 0)

    def test_update_floatingip_raise_before_super_call(self):
        floatingip = {
            'floatingip': {
                'port_id': None
            }
        }
        fid = 'uuid-fid-111'
        self.context.session.query().filter_by().one.side_effect = \
            sa_exc.NoResultFound
        self.assertRaises(
            n_exc.PortNotFound,
            self.plg.update_floatingip, self.context, fid, floatingip
        )

    @patch('neutron.services.l3_router.l3_router_plugin.'
           'L3RouterPlugin.update_floatingip')
    def _test_update_floatingip_raise_after_super_call(self, uifp):
        floatingip = {
            'floatingip': {
                'port_id': 'uuid-port_id_112'
            }
        }
        fid = 'uuid-fid-112'
        self.context.session.query().filter_by().one.side_effect = \
            sa_exc.NoResultFound
        self.assertRaises(
            n_exc.PortNotFound,
            self.plg.update_floatingip, self.context, fid, floatingip
        )
