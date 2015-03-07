# Copyright 2012-2013 NEC Corporation.  All rights reserved.
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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from neutron.agent import securitygroups_rpc as sg_rpc
from neutron.api import extensions as neutron_extensions
from neutron.api.rpc.agentnotifiers import dhcp_rpc_agent_api
from neutron.api.rpc.handlers import dhcp_rpc
from neutron.api.rpc.handlers import l3_rpc
from neutron.api.rpc.handlers import metadata_rpc
from neutron.api.rpc.handlers import securitygroups_rpc
from neutron.common import constants as const
from neutron.common import exceptions as n_exc
from neutron.common import log as call_log
from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.db import agents_db
from neutron.db import agentschedulers_db
from neutron.db import allowedaddresspairs_db as addr_pair_db
from neutron.db import db_base_plugin_v2
from neutron.db import external_net_db
from neutron.db import portbindings_base
from neutron.db import quota_db  # noqa
from neutron.extensions import allowedaddresspairs as addr_pair
from neutron.plugins.common import constants as svc_constants
from neutron.plugins.nec import extensions

from networking_nec.plugins.openflow import l2manager
from networking_nec.plugins.openflow import ofc_manager
from networking_nec.plugins.openflow import packet_filter
from networking_nec.plugins.openflow import portbindings as bindings
from networking_nec.plugins.openflow import router as router_plugin
from networking_nec.plugins.openflow import rpc

LOG = logging.getLogger(__name__)


class NECPluginV2Impl(db_base_plugin_v2.NeutronDbPluginV2,
                      external_net_db.External_net_db_mixin,
                      router_plugin.RouterMixin,
                      rpc.SecurityGroupServerRpcMixin,
                      agentschedulers_db.DhcpAgentSchedulerDbMixin,
                      router_plugin.L3AgentSchedulerDbMixin,
                      packet_filter.PacketFilterMixin,
                      bindings.PortBindingMixin,
                      addr_pair_db.AllowedAddressPairsMixin):

    def setup_extension_aliases(self, aliases):
        sg_rpc.disable_security_group_extension_by_config(aliases)
        self.remove_packet_filter_extension_if_disabled(aliases)

    def __init__(self):
        super(NECPluginV2Impl, self).__init__()
        self.ofc = ofc_manager.OFCManager(self.safe_reference)
        self.l2mgr = l2manager.L2Manager(self.safe_reference)
        self.base_binding_dict = self._get_base_binding_dict()
        portbindings_base.register_port_dict_function()

        neutron_extensions.append_api_extensions_path(extensions.__path__)

        self.setup_rpc()
        self.l3_rpc_notifier = router_plugin.L3AgentNotifyAPI()

        self.network_scheduler = importutils.import_object(
            cfg.CONF.network_scheduler_driver
        )
        self.router_scheduler = importutils.import_object(
            cfg.CONF.router_scheduler_driver
        )

        router_plugin.load_driver(self.safe_reference, self.ofc)
        self.start_periodic_dhcp_agent_status_check()

    def setup_rpc(self):
        self.service_topics = {svc_constants.CORE: topics.PLUGIN,
                               svc_constants.L3_ROUTER_NAT: topics.L3PLUGIN}
        self.conn = n_rpc.create_connection(new=True)
        self.notifier = rpc.NECPluginV2AgentNotifierApi(topics.AGENT)
        self.agent_notifiers[const.AGENT_TYPE_DHCP] = (
            dhcp_rpc_agent_api.DhcpAgentNotifyAPI()
        )
        self.agent_notifiers[const.AGENT_TYPE_L3] = (
            router_plugin.L3AgentNotifyAPI()
        )

        # NOTE: callback_sg is referred to from the sg unit test.
        self.callback_sg = securitygroups_rpc.SecurityGroupServerRpcCallback()
        self.endpoints = [
            rpc.NECPluginV2RPCCallbacks(self.safe_reference),
            dhcp_rpc.DhcpRpcCallback(),
            l3_rpc.L3RpcCallback(),
            self.callback_sg,
            agents_db.AgentExtRpcCallback(),
            metadata_rpc.MetadataRpcCallback()]
        for svc_topic in self.service_topics.values():
            self.conn.create_consumer(svc_topic, self.endpoints, fanout=False)
        # Consume from all consumers in threads
        self.conn.consume_in_threads()

    @call_log.log
    def create_network(self, context, network):
        """Create a new network entry on DB, and create it on OFC."""
        tenant_id = self._get_tenant_id_for_create(context, network['network'])
        # set up default security groups
        self._ensure_default_security_group(context, tenant_id)
        network['network']['status'] = self.l2mgr.get_initial_net_status(
            network)
        with context.session.begin(subtransactions=True):
            new_net = super(NECPluginV2Impl, self).create_network(context,
                                                                  network)
            self._process_l3_create(context, new_net, network['network'])

        self.l2mgr.create_network(context, new_net)

        return new_net

    @call_log.log
    def update_network(self, context, id, network):
        """Update network and handle resources associated with the network.

        Update network entry on DB. If 'admin_state_up' was changed, activate
        or deactivate ports and packetfilters associated with the network.
        """

        session = context.session
        with session.begin(subtransactions=True):
            old_net = super(NECPluginV2Impl, self).get_network(context, id)
            new_net = super(NECPluginV2Impl, self).update_network(context, id,
                                                                  network)
            self._process_l3_update(context, new_net, network['network'])

        self.l2mgr.update_network(context, id, old_net, new_net)

        return new_net

    @call_log.log
    def delete_network(self, context, id):
        """Delete network and packet_filters associated with the network.

        Delete network entry from DB and OFC. Then delete packet_filters
        associated with the network. If the network is the last resource
        of the tenant, delete unnessary ofc_tenant.
        """
        ports = self.get_ports(context, filters={'network_id': [id]})

        # check if there are any tenant owned ports in-use;
        # consider ports owned by floating ips as auto_delete as if there are
        # no other tenant owned ports, those floating ips are disassociated
        # and will be auto deleted with self._process_l3_delete()
        only_auto_del = all(p['device_owner'] in
                            db_base_plugin_v2.AUTO_DELETE_PORT_OWNERS or
                            p['device_owner'] == const.DEVICE_OWNER_FLOATINGIP
                            for p in ports)
        if not only_auto_del:
            raise n_exc.NetworkInUse(net_id=id)

        self._process_l3_delete(context, id)

        self.l2mgr.delete_network(context, id, ports)

        super(NECPluginV2Impl, self).delete_network(context, id)

    @call_log.log
    def create_port(self, context, port):
        """Create a new port entry on DB, then try to activate it."""

        port['port']['status'] = self.l2mgr.get_initial_port_status(port)
        port_data = port['port']
        with context.session.begin(subtransactions=True):
            self._ensure_default_security_group_on_port(context, port)
            sgids = self._get_security_groups_on_port(context, port)
            new_port = super(NECPluginV2Impl, self).create_port(context, port)
            self._process_portbindings_create(context, port_data, new_port)
            self._process_port_create_security_group(
                context, new_port, sgids)
            new_port[addr_pair.ADDRESS_PAIRS] = (
                self._process_create_allowed_address_pairs(
                    context, new_port,
                    port_data.get(addr_pair.ADDRESS_PAIRS)))
        self.notify_security_groups_member_updated(context, new_port)
        return self.l2mgr.create_port(context, new_port)

    @call_log.log
    def update_port(self, context, id, port):
        """Update port, and handle packetfilters associated with the port.

        Update network entry on DB. If admin_state_up was changed, activate
        or deactivate the port and packetfilters associated with it.
        """
        need_port_update_notify = False
        with context.session.begin(subtransactions=True):
            old_port = super(NECPluginV2Impl, self).get_port(context, id)
            new_port = super(NECPluginV2Impl, self).update_port(context,
                                                                id, port)
            self._process_portbindings_update(context, port['port'], new_port)
            if addr_pair.ADDRESS_PAIRS in port['port']:
                need_port_update_notify |= (
                    self.update_address_pairs_on_port(context, id, port,
                                                      old_port,
                                                      new_port))
            need_port_update_notify |= self.update_security_group_on_port(
                context, id, port, old_port, new_port)

        need_port_update_notify |= self.is_security_group_member_updated(
            context, old_port, new_port)
        if need_port_update_notify:
            self.notifier.port_update(context, new_port)

        self.l2mgr.update_port(context, old_port, new_port)
        return new_port

    @call_log.log
    def delete_port(self, context, id, l3_port_check=True):
        """Delete port and packet_filters associated with the port."""
        # if needed, check to see if this is a port owned by
        # and l3-router.  If so, we should prevent deletion.
        if l3_port_check:
            self.prevent_l3_port_deletion(context, id)

        port = self.l2mgr.delete_port(context, id)

        with context.session.begin(subtransactions=True):
            router_ids = self.disassociate_floatingips(
                context, id, do_notify=False)
            super(NECPluginV2Impl, self).delete_port(context, id)

        # now that we've left db transaction, we are safe to notify
        self.notify_routers_updated(context, router_ids)
        self.notify_security_groups_member_updated(context, port)
