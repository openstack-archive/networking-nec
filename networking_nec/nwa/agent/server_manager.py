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
from neutron.common import rpc as n_rpc
from oslo_config import cfg
from oslo_log import log as logging
from oslo_messaging.rpc.server import get_rpc_server
from oslo_messaging.target import Target

from networking_nec._i18n import _LW, _LI, _LE
from networking_nec.nwa.common import constants as nwa_const

LOG = logging.getLogger(__name__)


class ServerManager(object):
    """Implementation of nwa_agent_callback.NwaAgentRpcCallback."""

    rpc_servers = {}

    def __init__(self, topic, agent_top, size=1000):
        super(ServerManager, self).__init__()
        self.topic = topic
        self.agent_top = agent_top
        self.greenpool_size = size
        self.greenpool = eventlet.greenpool.GreenPool(self.greenpool_size)

    def get_rpc_server_topics(self):
        return [v['topic'] for v in self.rpc_servers.values()]

    def get_rpc_server_tenant_ids(self):
        return [{'tenant_id': tid} for tid in self.rpc_servers]

    def create_tenant_rpc_server(self, tid):
        """create_ blocking rpc server

        @param tid: openstack tenant id
        """
        ret = {}

        if tid in self.rpc_servers:
            LOG.warning(
                _LW("already in message queue and server. queue=%s"),
                self.rpc_servers[tid]['topic']
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

        LOG.debug("RPCServer create: topic=%s", topic)
        if self.greenpool.free() < 1:
            self.greenpool_size += nwa_const.NWA_GREENPOOL_ADD_SIZE
            self.greenpool.resize(self.greenpool_size)
            LOG.info(_LI('RPCServer greenpool resize %s'), self.greenpool_size)

        def server_start():
            while True:
                try:
                    LOG.debug('RPCServer thread %d start %s',
                              (self.greenpool.running(), server))
                    server.start()
                    LOG.debug('RPCServer thread end %s', server)
                    break
                except Exception as e:
                    LOG.exception(_LE('RPCServer thread start failed: %s'), e)

        self.rpc_servers[tid] = {
            'thread': self.greenpool.spawn(server_start),
            'server': server,
            'topic': topic
        }
        eventlet.sleep(0)
        LOG.info(_LI('RPCServer started: %(topic)s server=%(server)s'),
                 {'topic': topic, 'server': server})

        ret['result'] = 'SUCCESS'
        ret['tenant_id'] = tid
        ret['topic'] = topic

        return ret

    def delete_tenant_rpc_server(self, tid):
        if tid not in self.rpc_servers:
            LOG.warning(_LW("rpc server not found. tid=%s"), tid)
            return {'result': 'FAILED'}

        LOG.debug('RPCServer delete: stop %s', tid)
        self.rpc_servers[tid]['server'].stop()

        LOG.debug('RPCServer delete: wait %s', tid)
        self.rpc_servers[tid]['server'].wait()

        LOG.debug('RPCServer delete: pop %s', tid)
        self.rpc_servers.pop(tid)

        LOG.debug('RPCServer delete: sleep %s', tid)
        eventlet.sleep(0)

        ret = {
            'result': 'SUCCESS',
            'tenant_id': tid
        }

        LOG.debug("RPCServer deleted: %s", ret)

        return ret
