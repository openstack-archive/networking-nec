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

import eventlet
eventlet.monkey_patch()
import socket
import sys
import time

from neutron.agent import rpc as agent_rpc
from neutron.common import config as logging_config
from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron import context as q_context
from oslo_log import log as logging
from oslo_service import loopingcall

from networking_nec._i18n import _LE
from networking_nec.plugins.necnwa.agent import proxy_l2
from networking_nec.plugins.necnwa.agent import proxy_tenant
from networking_nec.plugins.necnwa.agent import server_manager
from networking_nec.plugins.necnwa.common import config
import networking_nec.plugins.necnwa.common.constants as nwa_const
from networking_nec.plugins.necnwa.l2.rpc import nwa_agent_callback
from networking_nec.plugins.necnwa.l2.rpc import nwa_proxy_callback
from networking_nec.plugins.necnwa.l2.rpc import tenant_binding_api
from networking_nec.plugins.necnwa.nwalib import client as nwa_cli


LOG = logging.getLogger(__name__)


class NECNWANeutronAgent(object):

    rpc_servers = dict()
    topic = nwa_const.NWA_AGENT_TOPIC

    def __init__(self, polling_interval):
        """Constructor.

        @param polling_interval: interval (secs) to check the nwa.
        """
        self.polling_interval = polling_interval
        self.need_sync = True

        self.conf = config.CONF
        self.host = socket.gethostname()
        self.agent_id = 'necnwa-q-agent.%s' % self.host

        self.client = nwa_cli.NwaClient()

        self.agent_state = {
            'binary': 'neutron-necnwa-agent',
            'host': config.CONF.host,
            'topic': nwa_const.NWA_AGENT_TOPIC,
            'configurations': {},
            'agent_type': nwa_const.NWA_AGENT_TYPE,
            'start_flag': True}

        self.server_manager = server_manager.ServerManager(self.topic, self)
        self.proxy_tenant = proxy_tenant.AgentProxyTenant(self, self.client)
        self.proxy_l2 = proxy_l2.AgentProxyL2(self, self.client,
                                              self.proxy_tenant)

        self.setup_rpc()

        LOG.debug('NWA Agent state %s', self.agent_state)

    def setup_rpc(self):
        """setup_rpc """

        self.context = q_context.get_admin_context_without_session()

        self.nwa_l2_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN
        )

        self.state_rpc = agent_rpc.PluginReportStateAPI(topics.REPORTS)
        self.callback_nwa = nwa_agent_callback.NwaAgentRpcCallback(
            self.context, self.server_manager)
        self.callback_proxy = nwa_proxy_callback.NwaProxyCallback(
            self.context, self.proxy_l2)

        # lbaas
        self.lbaas_driver = None
        self.callback_lbaas = None
        if self.conf.NWA.lbaas_driver:
            pass

        # fwaas
        self.fwaas_driver = None
        self.callback_fwaas = None
        if self.conf.NWA.fwaas_driver:
            pass

        # endpoints
        self.endpoints = [self.callback_nwa]

        # create connection
        self.conn = n_rpc.create_connection(new=True)

        self.conn.create_consumer(self.topic, self.endpoints,
                                  fanout=False)

        self.conn.consume_in_threads()

        report_interval = config.CONF.AGENT.report_interval
        if report_interval:
            heartbeat = loopingcall.FixedIntervalLoopingCall(
                self._report_state)
            heartbeat.start(interval=report_interval)

    def _report_state(self):
        try:
            queues = self.server_manager.get_rpc_server_topics()
            self.agent_state['configurations']['tenant_queues'] = queues
            self.state_rpc.report_state(self.context,
                                        self.agent_state)
            self.agent_state.pop('start_flag', None)

            servers = self.server_manager.get_rpc_server_tenant_ids()
            self.nwa_l2_rpc.update_tenant_rpc_servers(
                self.context, servers
            )

        except Exception as e:
            LOG.exception(_LE("Failed reporting state! %s"), str(e))

    def loop_handler(self):
        pass

    def daemon_loop(self):
        """Main processing loop for NECNWA Plugin Agent."""
        while True:
            self.loop_handler()
            time.sleep(self.polling_interval)


def main():
    logging_config.init(sys.argv[1:])
    logging_config.setup_logging()

    polling_interval = config.AGENT.polling_interval
    agent = NECNWANeutronAgent(polling_interval)

    agent.daemon_loop()

if __name__ == "__main__":
    main()
