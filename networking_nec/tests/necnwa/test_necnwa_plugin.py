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
import re
from mock import patch, MagicMock
from nose.tools import ok_, eq_, raises
from sqlalchemy.orm import exc as sa_exc
from neutron.common import exceptions as n_exc

from neutron.plugins.necnwa.common import config
from neutron.plugins.necnwa.necnwa_plugin import (
    NWAClientError,
    NECNWAServicePlugin
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

context = MagicMock()
floating = {
    'floating_ip_address': '172.16.0.107',
    'fixed_ip_address': '192.168.120.107',
    'router_id': 'uuid-router_id-107',
    'floating_network_id': 'uuid-network_id-107',
    'tenant_id': 'T-107',
    'floating_port_id': 'uuid-floating_port_id-107',
}
rcode = MagicMock()


def setup():
    config.CONF.NWA.PolicyFWDefault = True
    config.CONF.NWA.ScenarioPollingCount = 1
    config.CONF.NWA.ScenarioPollingTimer = 0.01


class TestNECNWAServicePlugin:

    @patch('neutron.services.l3_router.l3_router_plugin.'
           'L3RouterPlugin.__init__')
    def setUp(self, l3p):
        self.plg = NECNWAServicePlugin()

    @patch('neutron.db.l3_db.L3_NAT_db_mixin.create_floatingip')
    def test_create_floatingip(self, cfip):
        floatingip = MagicMock()
        cfip.return_value = 0
        rc = self.plg.create_floatingip(context, floatingip)
        eq_(rc, 0)

    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_setting_nat')
    @patch('neutron.plugins.necnwa.necnwa_utils.nwa_delete_nat')
    @patch('neutron.services.l3_router.l3_router_plugin.'
           'L3RouterPlugin.update_floatingip')
    def test_update_floatingip(self, ufip, ndn, nsn):
        floatingip = {
            'floatingip': {
                'port_id': None
            }
        }
        fid = 'uuid-fid-100'
        ufip.return_value = 0
        context.session.query().filter_by().one.return_value = floating
        rc = self.plg.update_floatingip(context, fid, floatingip)
        eq_(rc, 0)

        floatingip = {
            'floatingip': {
                'port_id': 'uuid-port_id-101'
            }
        }
        rc = self.plg.update_floatingip(context, fid, floatingip)
        eq_(rc, 0)

        floatingip = {
            'floatingip': {
                'port_id1': 'uuid-port_id-102'
            }
        }
        rc = self.plg.update_floatingip(context, fid, floatingip)
        eq_(rc, 0)

    @raises(n_exc.PortNotFound)
    def test_update_floatingip_raise_before_super_call(self):
        floatingip = {
            'floatingip': {
                'port_id': None
            }
        }
        fid = 'uuid-fid-111'
        context.session.query().filter_by().one.side_effect = sa_exc.NoResultFound
        self.plg.update_floatingip(context, fid, floatingip)

    @raises(n_exc.PortNotFound)
    @patch('neutron.services.l3_router.l3_router_plugin.'
           'L3RouterPlugin.update_floatingip')
    def test_update_floatingip_raise_after_super_call(self, uifp):
        floatingip = {
            'floatingip': {
                'port_id': 'uuid-port_id_112'
            }
        }
        fid = 'uuid-fid-112'
        context.session.query().filter_by().one.side_effect = sa_exc.NoResultFound
        self.plg.update_floatingip(context, fid, floatingip)

    def check_called(self, cstfp, param):
        if param.get('dev_params', None):
            cstfp.assert_any_call(
                context, param['router_id'], param['dev_params']
            )
        if param.get('def_params', None):
            cstfp.assert_any_call(
                context, param['router_id'], param['def_params']
            )
        if param.get('call_count', None):
            eq_(cstfp.call_count, param['call_count'])
