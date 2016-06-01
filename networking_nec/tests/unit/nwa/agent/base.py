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
from neutron.common import rpc
from neutron.tests import base
from oslo_config import cfg

from networking_nec.nwa.agent import nwa_agent


def _init_nwa_client_patch(mocked_nwacli):
    succeed = (200, {
        'status': 'SUCCEED',
        'resultdata': {
            'LogicalNWName': 'LNW_BusinessVLAN_4000',
            'TenantFWName': 'T1',
            'VlanID': '4000',
        }
    })
    mocked_nwacli.tenant.create_tenant.return_value = succeed
    mocked_nwacli.tenant.delete_tenant.return_value = succeed

    mocked_nwacli.l2.create_general_dev.return_value = succeed
    mocked_nwacli.l2.create_tenant_nw.return_value = succeed
    mocked_nwacli.l2.create_vlan.return_value = succeed
    mocked_nwacli.l2.delete_general_dev.return_value = succeed
    mocked_nwacli.l2.delete_tenant_nw.return_value = succeed
    mocked_nwacli.l2.delete_vlan.return_value = succeed


class TestNWAAgentBase(base.BaseTestCase):

    @mock.patch('oslo_service.loopingcall.FixedIntervalLoopingCall')
    @mock.patch('neutron.common.rpc.Connection.consume_in_threads')
    @mock.patch('neutron.common.rpc.create_connection')
    @mock.patch('neutron.agent.rpc.PluginReportStateAPI')
    @mock.patch('neutron.common.rpc.get_client')
    def setUp(self, f1, f2, f3, f4, f5):
        super(TestNWAAgentBase, self).setUp()

        cli = mock.patch('networking_nec.nwa.nwalib.client.NwaClient').start()
        self.nwacli = cli.return_value
        _init_nwa_client_patch(self.nwacli)

        self.agent = nwa_agent.NECNWANeutronAgent(10)
        rpc.init(cfg.ConfigOpts())
