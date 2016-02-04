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
from oslo_config import cfg
from oslo_log import log as logging
from oslo_messaging.rpc.server import get_rpc_server
from oslo_messaging.target import Target

from networking_nec._i18n import _LW

LOG = logging.getLogger(__name__)


class ServerManager(object):
    """Implementation of nwa_agent_callback.NwaAgentRpcCallback."""

    rpc_servers = {}

    def __init__(self, topic, agent_top):
        super(ServerManager, self).__init__()
        self.topic = topic
        self.agent_top = agent_top

    def get_rpc_server_topics(self):
        return [v['topic'] for k, v in self.rpc_servers.items()]

    def get_rpc_server_tenant_ids(self):
        return [{'tenant_id': tid} for tid in self.rpc_servers.keys()]

    def create_tenant_rpc_server(self, tid):
        """create_ blocking rpc server

        @param tid: openstack tenant id
        """
        ret = dict()

        if tid in self.rpc_servers.keys():
            LOG.warning(
                _LW("already in message queue and server."
                    " queue=%s") % self.rpc_servers[tid]['topic']
            )
            return {'result': 'FAILED'}

        topic = "%s-%s" % (self.topic, tid)

        target = Target(
            topic=topic, server=cfg.CONF.host, fanout=False)

        assert n_rpc.TRANSPORT is not None
        serializer = n_rpc.RequestContextSerializer(None)

        server = get_rpc_server(
            n_rpc.TRANSPORT, target,
            self.agent_top.endpoints,
            'blocking', serializer
        )
        self.rpc_servers[tid] = {
            'server': server,
            'topic': topic
        }

        LOG.debug("RPCServer create: topic=%s", topic)

        self.rpc_servers[tid]['server'].start()

        ret['result'] = 'SUCCESS'
        ret['tenant_id'] = tid
        ret['topic'] = topic

        return ret

    def delete_tenant_rpc_server(self, tid):
        if tid not in self.rpc_servers.keys():
            LOG.warning(_LW("rpc server not found. tid=%s"), tid)
            return {'result': 'FAILED'}

        self.rpc_servers[tid]['server'].stop()
        self.rpc_servers.pop(tid)

        ret = {
            'result': 'SUCCESS',
            'tenant_id': tid
        }

        LOG.debug("RPCServer delete: %s", ret)

        return ret
