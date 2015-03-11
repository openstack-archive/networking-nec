# Copyright 2012-2015 NEC Corporation.  All rights reserved.
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

from oslo_log import log as logging
import oslo_messaging

from neutron.agent import securitygroups_rpc as sg_rpc
from neutron.common import exceptions as n_exc
from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.db import securitygroups_rpc_base as sg_db_rpc

from networking_nec.plugins.openflow.db import api as ndb
from networking_nec.plugins.openflow import utils as necutils


LOG = logging.getLogger(__name__)


class SecurityGroupServerRpcMixin(sg_db_rpc.SecurityGroupServerRpcMixin):

    @staticmethod
    def get_port_from_device(device):
        port = ndb.get_port_from_device(device)
        if port:
            port['device'] = device
        LOG.debug("NECPluginV2.get_port_from_device() called, "
                  "device=%(device)s => %(ret)s.",
                  {'device': device, 'ret': port})
        return port


class NECPluginV2AgentNotifierApi(sg_rpc.SecurityGroupAgentRpcApiMixin):
    '''RPC API for NEC plugin agent.'''

    def __init__(self, topic):
        self.topic = topic
        self.topic_port_update = topics.get_topic_name(
            topic, topics.PORT, topics.UPDATE)
        target = oslo_messaging.Target(topic=topic, version='1.0')
        self.client = n_rpc.get_client(target)

    def port_update(self, context, port):
        cctxt = self.client.prepare(topic=self.topic_port_update, fanout=True)
        cctxt.cast(context, 'port_update', port=port)


class NECPluginV2RPCCallbacks(object):

    target = oslo_messaging.Target(version='1.0')

    def __init__(self, plugin):
        super(NECPluginV2RPCCallbacks, self).__init__()
        self.plugin = plugin

    def update_ports(self, rpc_context, **kwargs):
        """Update ports' information and activate/deavtivate them.

        Expected input format is:
            {'topic': 'q-agent-notifier',
             'agent_id': 'nec-q-agent.' + <hostname>,
             'datapath_id': <datapath_id of br-int on remote host>,
             'port_added': [<new PortInfo>,...],
             'port_removed': [<removed Port ID>,...]}
        """
        LOG.debug("NECPluginV2RPCCallbacks.update_ports() called, "
                  "kwargs=%s .", kwargs)
        datapath_id = kwargs['datapath_id']
        session = rpc_context.session
        for p in kwargs.get('port_added', []):
            id = p['id']
            portinfo = ndb.get_portinfo(session, id)
            if portinfo:
                if (necutils.cmp_dpid(portinfo.datapath_id, datapath_id) and
                        portinfo.port_no == p['port_no']):
                    LOG.debug("update_ports(): ignore unchanged portinfo in "
                              "port_added message (port_id=%s).", id)
                    continue
                ndb.del_portinfo(session, id)
            port = self._get_port(rpc_context, id)
            if port:
                ndb.add_portinfo(session, id, datapath_id, p['port_no'],
                                 mac=p.get('mac', ''))
                # NOTE: Make sure that packet filters on this port exist while
                # the port is active to avoid unexpected packet transfer.
                if portinfo:
                    self.plugin.l2mgr.deactivate_port(rpc_context, port,
                                                      raise_exc=False)
                    self.plugin.deactivate_packet_filters_by_port(
                        rpc_context, id, raise_exc=False)
                self.plugin.activate_packet_filters_by_port(rpc_context, id)
                self.plugin.l2mgr.activate_port_if_ready(rpc_context, port)
        for id in kwargs.get('port_removed', []):
            portinfo = ndb.get_portinfo(session, id)
            if not portinfo:
                LOG.debug("update_ports(): ignore port_removed message "
                          "due to portinfo for port_id=%s was not "
                          "registered", id)
                continue
            if not necutils.cmp_dpid(portinfo.datapath_id, datapath_id):
                LOG.debug("update_ports(): ignore port_removed message "
                          "received from different host "
                          "(registered_datapath_id=%(registered)s, "
                          "received_datapath_id=%(received)s).",
                          {'registered': portinfo.datapath_id,
                           'received': datapath_id})
                continue
            ndb.del_portinfo(session, id)
            port = self._get_port(rpc_context, id)
            if port:
                self.plugin.l2mgr.deactivate_port(rpc_context, port,
                                                  raise_exc=False)
                self.plugin.deactivate_packet_filters_by_port(
                    rpc_context, id, raise_exc=False)

    def _get_port(self, context, port_id):
        try:
            return self.plugin.get_port(context, port_id)
        except n_exc.PortNotFound:
            return None
