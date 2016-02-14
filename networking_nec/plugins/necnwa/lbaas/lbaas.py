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

from neutron.plugins.common import constants
from neutron_lbaas.services.loadbalancer.drivers.common \
    import agent_driver_base
from oslo_log import log as logging
import oslo_messaging

from networking_nec.plugins.necnwa.common import constants as nwa_const

LOG = logging.getLogger(__name__)


class LoadBalancerNWAAgentApi(agent_driver_base.LoadBalancerAgentApi):
    """Plugin side of plugin to agent RPC API."""

    def __init__(self, topic):
        target = oslo_messaging.Target(topic=topic, version='1.0')
        self.client = n_rpc.get_client(target)


class NECNWALBaaSDriver(agent_driver_base.AgentDriverBase):
    device_driver = 'necnwa_lbaas'

    def __init__(self, plugin):

        if (
                not self.device_driver or
                not self._is_active_agent()
        ):
            raise agent_driver_base.DriverNotSpecified()

        self.agent_rpcs = dict()
        self.plugin = plugin
        self._set_callbacks_on_plugin()

    def _is_active_agent(self):
        # True: necnwa_agent is active
        # False: necnwa_agent is not active
        return True

    def get_agent_rpc(self, tid):
        if tid not in self.agent_rpcs.keys():
            agent_topic = "%s-%s" % (nwa_const.NWA_AGENT_TOPIC, tid)
            self.agent_rpcs[tid] = LoadBalancerNWAAgentApi(agent_topic)
        return self.agent_rpcs[tid]

    def create_pool(self, context, pool):
        agent_rpc = self.get_agent_rpc(pool['tenant_id'])
        agent_rpc.create_pool(context, pool, None, self.device_driver)

    def update_pool(self, context, old_pool, pool):
        agent_rpc = self.get_agent_rpc(pool['tenant_id'])

        if pool['status'] in constants.ACTIVE_PENDING_STATUSES:
            agent_rpc.update_pool(context, old_pool, pool, None)
        else:
            agent_rpc.delete_pool(context, pool)

    def delete_pool(self, context, pool):
        self.plugin._delete_db_pool(context, pool['id'])

        agent_rpc = self.get_agent_rpc(pool['tenant_id'])
        agent_rpc.delete_pool(context, pool, None)

    def create_member(self, context, member):
        agent_rpc = self.get_agent_rpc(member['tenant_id'])
        agent_rpc.create_member(context, member, None)

    def update_member(self, context, old_member, member):
        agent_rpc = self.get_agent_rpc(member['tenant_id'])

        if member['pool_id'] != old_member['pool_id']:
            old_pool_agent = self.plugin.get_lbaas_agent_hosting_pool(
                context, old_member['pool_id'])
            if old_pool_agent:
                agent_rpc.delete_member(context, old_member,
                                        old_pool_agent['agent']['host'])
            agent_rpc.create_member(context, member, None)
        else:
            agent_rpc.update_member(context, old_member, member, None)

    def delete_member(self, context, member):
        agent_rpc = self.get_agent_rpc(member['tenant_id'])

        self.plugin._delete_db_member(context, member['id'])
        agent_rpc.delete_member(context, member, None)

    def create_vip(self, context, vip):
        agent_rpc = self.get_agent_rpc(vip['tenant_id'])

        agent_rpc.create_vip(context, vip, None)

    def update_vip(self, context, old_vip, vip):
        agent_rpc = self.get_agent_rpc(vip['tenant_id'])

        if vip['status'] in constants.ACTIVE_PENDING_STATUSES:
            agent_rpc.update_vip(context, old_vip, vip, None)
        else:
            agent_rpc.delete_vip(context, vip, None)

    def delete_vip(self, context, vip):
        agent_rpc = self.get_agent_rpc(vip['tenant_id'])

        self.plugin._delete_db_vip(context, vip['id'])
        agent_rpc.delete_vip(context, vip, None)

    def create_pool_health_monitor(self, context, healthmon, pool_id):
        agent_rpc = self.get_agent_rpc(healthmon['tenant_id'])

        agent_rpc.create_pool_health_monitor(
            context, healthmon, pool_id, None
        )

    def update_pool_health_monitor(
            self, context, old_health_monitor,
            health_monitor, pool_id
    ):
        agent_rpc = self.get_agent_rpc(health_monitor['tenant_id'])

        agent_rpc.update_pool_health_monitor(
            context, old_health_monitor,
            health_monitor, pool_id, None
        )

    def delete_pool_health_monitor(
            self, context, health_monitor, pool_id
    ):
        agent_rpc = self.get_agent_rpc(health_monitor['tenant_id'])

        self.plugin._delete_db_pool_health_monitor(
            context, health_monitor['id'], pool_id
        )

        agent_rpc.delete_pool_health_monitor(
            context, health_monitor, pool_id, None
        )
