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

from mock import patch
from oslo_config import cfg

from networking_nec.nwa.agent import nwa_agent
from networking_nec.tests.unit.nwa.agent import base


class TestNECNWANeutronAgentAsNwaClient(base.TestNWAAgentBase):

    @patch('neutron.common.rpc.Connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
           'TenantBindingServerRpcApi')
    def test__setup_rpc(self, f1, f2, f3):
        self.agent.setup_rpc()
        self.assertIsNotNone(self.agent.host)
        self.assertIsNotNone(self.agent.agent_id)
        self.assertIsNotNone(self.agent.context)
        self.assertIsNotNone(self.agent.nwa_l2_rpc)
        self.assertIsNotNone(self.agent.state_rpc)
        self.assertIsNotNone(self.agent.callback_nwa)
        self.assertIsNotNone(self.agent.callback_proxy)

    @patch('neutron.common.rpc.Connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('networking_nec.nwa.l2.rpc.tenant_binding_api.'
           'TenantBindingServerRpcApi')
    def test__setup_rpc_no_report_interval(self, f1, f2, f3):
        self.agent.conf.NWA.lbaas_driver = True
        self.agent.conf.NWA.fwaas_driver = True
        cfg.CONF.AGENT.report_interval = 0
        self.agent.setup_rpc()
        self.assertIsNotNone(self.agent.host)
        self.assertIsNotNone(self.agent.agent_id)
        self.assertIsNotNone(self.agent.context)
        self.assertIsNotNone(self.agent.nwa_l2_rpc)
        self.assertIsNotNone(self.agent.state_rpc)
        self.assertIsNotNone(self.agent.callback_nwa)
        self.assertIsNotNone(self.agent.callback_proxy)

    def test__report_state(self):
        self.assertIsNone(self.agent._report_state())

    def test_loop_handler(self):
        self.assertIsNone(self.agent.loop_handler())

    @patch('time.sleep')
    def test_daemon_loop(self, f1):
        f1.side_effect = ValueError('dummy exception')
        self.assertRaises(
            ValueError,
            self.agent.daemon_loop
        )


@patch('networking_nec.nwa.agent.nwa_agent.NECNWANeutronAgent')
@patch('neutron.common.config')
@patch('sys.argv')
def test_main(f1, f2, f3):
    nwa_agent.main()
