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
# from neutron.plugins.common import constants as const
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_serialization import jsonutils

# Don't remove l3_dvr_db
import neutron.db.l3_dvr_db     # noqa

from neutron_fwaas.db.firewall import firewall_db
# from neutron_fwaas.db.firewall import firewall_router_insertion_db
# from neutron_fwaas.extensions import firewall as fw_ext
from neutron_fwaas.services.firewall.fwaas_plugin import FirewallCallbacks
from neutron_fwaas.services.firewall.fwaas_plugin import FirewallPlugin

from networking_nec.plugins.necnwa.agent import necnwa_agent_rpc

LOG = logging.getLogger(__name__)


class NECNWAFirewallCallbacks(FirewallCallbacks):

    target = oslo_messaging.Target(version='1.0')

    def __init__(self, plugin):
        super(NECNWAFirewallCallbacks, self).__init__()
        self.plugin = plugin


class NECNWAFirewallAgentApi(object):
    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, topic, host, tenant_id):
        self.host = host
        target = oslo_messaging.Target(
            topic='%s-%s' % (topic, tenant_id),
            version=self.BASE_RPC_API_VERSION)

        self.client = n_rpc.get_client(target)

    def create_firewall(self, context, firewall):
        cctxt = self.client.prepare()
        LOG.debug("[RPC] create_firewall %s" % firewall)
        cctxt.cast(
            context, 'create_firewall',
            firewall=firewall,
            host=self.host
        )
        LOG.debug("[RPC] create_firewall end")

    def update_firewall(self, context, firewall):
        cctxt = self.client.prepare()
        cctxt.cast(
            context, 'update_firewall',
            firewall=firewall,
            host=self.host
        )

    def delete_firewall(self, context, firewall):
        cctxt = self.client.prepare()
        cctxt.cast(
            context, 'delete_firewall',
            firewall=firewall,
            host=self.host
        )


class NECNWAFirewallAgentApiProxy(object):
    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, plugin):
        self.plugin = plugin

    def create_firewall(self, context, firewall):
        tid = firewall['tenant_id']
        proxy = self.plugin._get_nwa_fwaas_proxy(tid)
        proxy.create_firewall(context, firewall)

    def update_firewall(self, context, firewall):
        tid = firewall['tenant_id']
        proxy = self.plugin._get_nwa_fwaas_proxy(tid)
        proxy.update_firewall(context, firewall)

    def delete_firewall(self, context, firewall):
        tid = firewall['tenant_id']
        proxy = self.plugin._get_nwa_fwaas_proxy(tid)
        proxy.delete_firewall(context, firewall)


class NECNWAFirewallPlugin(
    FirewallPlugin
):

    supported_extension_aliases = ["fwaas", "fwaasrouterinsertion"]

    def __init__(self):
        # self.endpoints = [NECNWAFirewallCallbacks(self)]
        self.endpoints = [FirewallCallbacks(self)]
        self.conn = n_rpc.create_connection(new=True)
        self.conn.create_consumer(
            necnwa_agent_rpc.NWA_FIREWALL_PLUGIN,
            self.endpoints,
            fanout=False
        )
        self.agent_rpc = NECNWAFirewallAgentApiProxy(self)
        self.conn.consume_in_threads()
        self.nwa_fwaas_proxies = dict()
        firewall_db.subscribe()

    def create_firewall(self, context, firewall):
        LOG.debug("[NWA] create_firewall %s" % firewall)
        return super(NECNWAFirewallPlugin, self).create_firewall(
            context, firewall
        )

    def update_firewall(self, context, id, firewall):
        LOG.debug("[NWA] update_firewall %s %s" % (id, firewall))
        return super(NECNWAFirewallPlugin, self).update_firewall(context,
                                                                 id, firewall)

    def delete_firewall(self, context, id):
        LOG.debug("[NWA] delete_firewall %s" % id)
        return super(NECNWAFirewallPlugin, self).delete_firewall(context, id)

    def update_firewall_policy(self, context, id, firewall_policy):
        LOG.debug("[NWA] update_firewall_policy id=%s, firewall_policy=%s" %
                  (id, firewall_policy))
        return super(NECNWAFirewallPlugin, self).update_firewall_policy(
            context, id, firewall_policy)

    def update_firewall_rule(self, context, id, firewall_rule):
        ret = super(NECNWAFirewallPlugin, self).update_firewall_rule(
            context, id, firewall_rule)
        LOG.debug("id=%s" % id)
        LOG.debug("firewall_rule=%s" % jsonutils.dumps(
            firewall_rule,
            indent=4,
            sort_keys=True
        ))
        return ret

    def insert_rule(self, context, id, rule_info):
        ret = super(NECNWAFirewallPlugin, self).insert_rule(context, id,
                                                            rule_info)
        LOG.debug("id=%s" % id)
        LOG.debug("rule_info=%s" % jsonutils.dumps(
            rule_info,
            indent=4,
            sort_keys=True
        ))
        return ret

    def remove_rule(self, context, id, rule_info):
        ret = super(NECNWAFirewallPlugin, self).remove_rule(context, id,
                                                            rule_info)
        LOG.debug("id=%s" % id)
        LOG.debug("rule_info=%s" % jsonutils.dumps(
            rule_info,
            indent=4,
            sort_keys=True
        ))
        return ret

    def _get_nwa_fwaas_proxy(self, tid):
        if tid not in self.nwa_fwaas_proxies.keys():
            self.nwa_fwaas_proxies[tid] = NECNWAFirewallAgentApi(
                necnwa_agent_rpc.NWA_AGENT_TOPIC, cfg.CONF.host, tid
            )

        return self.nwa_fwaas_proxies[tid]
