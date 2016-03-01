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

from neutron.common import rpc as n_rpc
from neutron_fwaas.db.firewall import firewall_db
from neutron_fwaas.services.firewall.fwaas_plugin import FirewallPlugin
from oslo_config import cfg
from oslo_log import log as logging

from networking_nec.nwa.common import constants as nwa_const
import networking_nec.nwa.fwaas.rpc.agent_api as nwa_fw_api
import networking_nec.nwa.fwaas.rpc.agent_callback as nwa_fw_callback

LOG = logging.getLogger(__name__)


class FirewallAgentApiProxy(object):
    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, plugin):
        self.plugin = plugin

    def create_firewall(self, context, firewall):
        tid = firewall['tenant_id']
        proxy = self.plugin.get_nwa_fwaas_proxy(tid)
        proxy.create_firewall(context, firewall)

    def update_firewall(self, context, firewall):
        tid = firewall['tenant_id']
        proxy = self.plugin.get_nwa_fwaas_proxy(tid)
        proxy.update_firewall(context, firewall)

    def delete_firewall(self, context, firewall):
        tid = firewall['tenant_id']
        proxy = self.plugin.get_nwa_fwaas_proxy(tid)
        proxy.delete_firewall(context, firewall)


class NECNwaFWaaSDriver(FirewallPlugin):

    supported_extension_aliases = ["fwaas", "fwaasrouterinsertion"]

    # pylint: disable=super-init-not-called
    def __init__(self):
        """Do the initialization for the firewall service plugin here."""
        self.start_rpc_listeners()

        self.agent_rpc = FirewallAgentApiProxy(self)
        firewall_db.subscribe()
        self.nwa_fwaas_proxies = {}

    def start_rpc_listeners(self):
        self.endpoints = [nwa_fw_callback.FWaaSAgentCallback(self)]

        self.conn = n_rpc.create_connection()
        self.conn.create_consumer(
            nwa_const.NWA_FIREWALL_PLUGIN, self.endpoints, fanout=False)
        return self.conn.consume_in_threads()

    def get_nwa_fwaas_proxy(self, tenant_id):
        if tenant_id not in self.nwa_fwaas_proxies:
            self.nwa_fwaas_proxies[tenant_id] = nwa_fw_api.FWaaSAgentApi(
                nwa_const.NWA_AGENT_TOPIC, cfg.CONF.host, tenant_id
            )
        return self.nwa_fwaas_proxies[tenant_id]
