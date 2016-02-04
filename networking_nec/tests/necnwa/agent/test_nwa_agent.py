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

import neutron
NEUTRON_CONF = (neutron.__path__[0] +
                '/../etc/neutron.conf')
from neutron.common import config
from neutron.common import rpc
from neutron.tests import base
from oslo_config import cfg
from oslo_log import log as logging

import networking_nec
NECNWA_INI = (networking_nec.__path__[0] +
              '/../etc/neutron/plugins/nec/necnwa.ini')
from networking_nec.plugins.necnwa.agent import nwa_agent

LOG = logging.getLogger(__name__)


def init_nwa_client_patch(mock):
    succeed = (200, {
        'status': 'SUCCESS',
        'resultdata': {
            'LogicalNWName': 'LNW_BusinessVLAN_4000',
            'TenantFWName': 'T1',
            'VlanID': '4000',
        }
    })
    mock.create_general_dev.return_value = succeed
    mock.create_tenant.return_value = succeed
    mock.create_tenant_nw.return_value = succeed
    mock.create_vlan.return_value = succeed
    mock.delete_general_dev.return_value = succeed
    mock.delete_tenant.return_value = succeed
    mock.delete_tenant_nw.return_value = succeed
    mock.delete_vlan.return_value = succeed


class TestNECNWANeutronAgentBase(base.BaseTestCase):

    @patch('oslo_service.loopingcall.FixedIntervalLoopingCall')
    @patch('neutron.common.rpc.Connection.consume_in_threads')
    @patch('neutron.common.rpc.create_connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1, f2, f3, f4, f5):
        super(TestNECNWANeutronAgentBase, self).setUp()
        self._patch_nwa_client()
        self._config_parse()
        self.context = MagicMock()
        self.agent = nwa_agent.NECNWANeutronAgent(10)
        rpc.init(cfg.ConfigOpts())

    def _patch_nwa_client(self):
        path = 'networking_nec.plugins.necnwa.nwalib.client.NwaClient'
        patcher = patch(path)
        self.addCleanup(patcher.stop)
        cli = patcher.start()
        self.nwacli = MagicMock()
        cli.return_value = self.nwacli
        init_nwa_client_patch(self.nwacli)

    def _config_parse(self, conf=None, args=None):
        """Create the default configurations."""
        if args is None:
            args = []
        # args += ['--config-file', NEUTRON_CONF]
        args += ['--config-file', NECNWA_INI]

        if conf is None:
            config.init(args=args)
        else:
            conf(args)


class TestNECNWANeutronAgentAsNwaClient(TestNECNWANeutronAgentBase):

    @patch('neutron.common.rpc.Connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('networking_nec.plugins.necnwa.l2.rpc.tenant_binding_api.TenantBindingServerRpcApi')  # noqa
    def test__setup_rpc(self, f1, f2, f3):
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


@patch('networking_nec.plugins.necnwa.agent.nwa_agent.NECNWANeutronAgent')  # noqa
@patch('neutron.common.config')
@patch('sys.argv')
def test_main(f1, f2, f3):
    nwa_agent.main()
