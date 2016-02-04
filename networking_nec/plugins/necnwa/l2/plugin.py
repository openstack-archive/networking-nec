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

from neutron.api.rpc.handlers import dhcp_rpc
from neutron.api.rpc.handlers import metadata_rpc
from neutron.api.rpc.handlers import securitygroups_rpc
from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.db import agents_db
from neutron.extensions import multiprovidernet as mpnet
from neutron.extensions import providernet as provider
from neutron.plugins.ml2 import db as db_ml2
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2 import plugin as ml2_plugin
from oslo_log import log as logging

from networking_nec._i18n import _LI, _LW
from networking_nec.plugins.necnwa.common import constants as nwa_const
from networking_nec.plugins.necnwa.l2 import db_api as necnwa_api
from networking_nec.plugins.necnwa.l2.rpc import ml2_server_callback
from networking_nec.plugins.necnwa.l2.rpc import nwa_agent_api
from networking_nec.plugins.necnwa.l2.rpc import nwa_l2_server_callback
from networking_nec.plugins.necnwa.l2.rpc import nwa_proxy_api
from networking_nec.plugins.necnwa.l2.rpc import tenant_binding_callback

LOG = logging.getLogger(__name__)


class NECNWAL2Plugin(ml2_plugin.Ml2Plugin):

    def __init__(self):
        super(NECNWAL2Plugin, self).__init__()
        self._nwa_agent_rpc_setup()

    def _nwa_agent_rpc_setup(self):
        self.nwa_rpc = nwa_agent_api.NECNWAAgentApi(
            nwa_const.NWA_AGENT_TOPIC
        )
        self.nwa_proxies = dict()

    def start_rpc_listeners(self):
        self.endpoints = [
            ml2_server_callback.NwaML2ServerRpcCallbacks(
                self.notifier, self.type_manager),
            nwa_l2_server_callback.NwaL2ServerRpcCallback(),
            tenant_binding_callback.TenantBindingServerRpcCallback(),
            securitygroups_rpc.SecurityGroupServerRpcCallback(),
            dhcp_rpc.DhcpRpcCallback(),
            agents_db.AgentExtRpcCallback(),
            metadata_rpc.MetadataRpcCallback()]

        self.topic = topics.PLUGIN
        self.conn = n_rpc.create_connection(new=True)
        self.conn.create_consumer(self.topic, self.endpoints,
                                  fanout=False)
        return self.conn.consume_in_threads()

    def _extend_network_dict_provider(self, context, network):
        if 'id' not in network:
            LOG.debug("Network has no id")
            network[provider.NETWORK_TYPE] = None
            network[provider.PHYSICAL_NETWORK] = None
            network[provider.SEGMENTATION_ID] = None
            return

        id = network['id']
        segments = db_ml2.get_network_segments(
            context.session, id, filter_dynamic=True)

        if not segments:
            LOG.debug("Network %s has no segments", id)
            network[provider.NETWORK_TYPE] = None
            network[provider.PHYSICAL_NETWORK] = None
            network[provider.SEGMENTATION_ID] = None
        elif len(segments) > 1:
            network[mpnet.SEGMENTS] = [
                {provider.NETWORK_TYPE: segment[api.NETWORK_TYPE],
                 provider.PHYSICAL_NETWORK: segment[api.PHYSICAL_NETWORK],
                 provider.SEGMENTATION_ID: segment[api.SEGMENTATION_ID]}
                for segment in segments]
        else:
            segment = segments[0]
            network[provider.NETWORK_TYPE] = segment[api.NETWORK_TYPE]
            network[provider.PHYSICAL_NETWORK] = segment[api.PHYSICAL_NETWORK]
            network[provider.SEGMENTATION_ID] = segment[api.SEGMENTATION_ID]

    def get_network(self, context, id, fields=None):
        session = context.session

        with session.begin(subtransactions=True):
            network = self._get_network(context, id)
            result = self._make_network_dict(network, fields)
            self._extend_network_dict_provider(context, result)

        return self._fields(result, fields)

    def get_networks(self, context, filters=None, fields=None,
                     sorts=None, limit=None, marker=None, page_reverse=False):
        return super(
            NECNWAL2Plugin,
            self
        ).get_networks(context, filters, None, sorts,
                       limit, marker, page_reverse)

    def _create_nwa_agent_tenant_queue(self, context, tenant_id):
        if (
                self._is_alive_nwa_agent(context) and
                necnwa_api.get_nwa_tenant_queue(
                    context.session,
                    tenant_id
                ) is None
        ):
            self.nwa_rpc.create_server(context, tenant_id)
            necnwa_api.add_nwa_tenant_queue(context.session, tenant_id)
        else:
            LOG.warning(_LW('%s is not alive.') %
                        nwa_const.NWA_AGENT_TYPE)

    def create_network(self, context, network):
        result = super(NECNWAL2Plugin,
                       self).create_network(context, network)
        self._create_nwa_agent_tenant_queue(context, context.tenant_id)
        return result

    def delete_network(self, context, id):
        result = super(NECNWAL2Plugin,
                       self).delete_network(context, id)
        return result

    def create_port(self, context, port):
        result = super(NECNWAL2Plugin,
                       self).create_port(context, port)

        return result

    def get_nwa_topics(self, context, tid):
        topics = []
        rss = self.nwa_rpc.get_nwa_rpc_servers(context)
        if isinstance(rss, dict) and rss.get('nwa_rpc_servers'):
            topics = [t.get('topic') for t in rss['nwa_rpc_servers']
                      if t.get('tenant_id') == tid]
        return topics

    def get_nwa_proxy(self, tid, context=None):
        if tid not in self.nwa_proxies.keys():
            self.nwa_proxies[tid] = nwa_proxy_api.NECNWAProxyApi(
                nwa_const.NWA_AGENT_TOPIC, tid
            )
            if context:
                self._create_nwa_agent_tenant_queue(context, tid)
                topics = self.get_nwa_topics(context, tid)
                if len(topics) == 1:
                    LOG.info(_LI('NWA tenant queue: new topic is %s'),
                             str(topics[0]))
                else:
                    LOG.warning(_LW('NWA tenant queue is not created. tid=%s'),
                                tid)
        LOG.debug('proxy tid=%s', tid)
        return self.nwa_proxies[tid]

    def _is_alive_nwa_agent(self, context):
        agents = self.get_agents(
            context,
            filters={'agent_type': [nwa_const.NWA_AGENT_TYPE]}
        )
        return any(agent['alive'] for agent in agents)
