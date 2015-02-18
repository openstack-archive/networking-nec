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
from oslo_utils import excutils
from oslo_utils import importutils
from oslo_utils import uuidutils

from neutron.agent import securitygroups_rpc as sg_rpc
from neutron.api import extensions as neutron_extensions
from neutron.api.rpc.agentnotifiers import dhcp_rpc_agent_api
from neutron.api.rpc.handlers import dhcp_rpc
from neutron.api.rpc.handlers import l3_rpc
from neutron.api.rpc.handlers import metadata_rpc
from neutron.api.rpc.handlers import securitygroups_rpc
from neutron.api.v2 import attributes as attrs
from neutron.common import constants as const
from neutron.common import exceptions as n_exc
from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.db import agents_db
from neutron.db import agentschedulers_db
from neutron.db import allowedaddresspairs_db as addr_pair_db
from neutron.db import db_base_plugin_v2
from neutron.db import external_net_db
from neutron.db import portbindings_base
from neutron.db import portbindings_db
from neutron.db import quota_db  # noqa
from neutron.extensions import allowedaddresspairs as addr_pair
from neutron.extensions import portbindings
from neutron.plugins.common import constants as svc_constants
from neutron.plugins.nec.common import config as nec_config
from neutron.plugins.nec import extensions

from networking_nec.i18n import _LE, _LI, _LW
from networking_nec.plugins.openflow.db import api as ndb
from networking_nec.plugins.openflow.db import router as rdb
from networking_nec.plugins.openflow import exceptions as nexc
from networking_nec.plugins.openflow import nec_router
from networking_nec.plugins.openflow import ofc_manager
from networking_nec.plugins.openflow import packet_filter
from networking_nec.plugins.openflow import rpc
from networking_nec.plugins.openflow import utils as necutils

LOG = logging.getLogger(__name__)


class NECPluginV2Impl(db_base_plugin_v2.NeutronDbPluginV2,
                      external_net_db.External_net_db_mixin,
                      nec_router.RouterMixin,
                      rpc.SecurityGroupServerRpcMixin,
                      agentschedulers_db.DhcpAgentSchedulerDbMixin,
                      nec_router.L3AgentSchedulerDbMixin,
                      packet_filter.PacketFilterMixin,
                      portbindings_db.PortBindingMixin,
                      addr_pair_db.AllowedAddressPairsMixin):

    _vendor_extensions = ["packet-filter", "router_provider"]

    def setup_extension_aliases(self, aliases):
        sg_rpc.disable_security_group_extension_by_config(aliases)
        self.remove_packet_filter_extension_if_disabled(aliases)

    def __init__(self):
        super(NECPluginV2Impl, self).__init__()
        self.ofc = ofc_manager.OFCManager(self.safe_reference)
        self.base_binding_dict = self._get_base_binding_dict()
        portbindings_base.register_port_dict_function()

        neutron_extensions.append_api_extensions_path(extensions.__path__)

        self.setup_rpc()
        self.l3_rpc_notifier = nec_router.L3AgentNotifyAPI()

        self.network_scheduler = importutils.import_object(
            cfg.CONF.network_scheduler_driver
        )
        self.router_scheduler = importutils.import_object(
            cfg.CONF.router_scheduler_driver
        )

        nec_router.load_driver(self.safe_reference, self.ofc)
        self.port_handlers = {
            'create': {
                const.DEVICE_OWNER_ROUTER_GW: self.create_router_port,
                const.DEVICE_OWNER_ROUTER_INTF: self.create_router_port,
                'default': self.activate_port_if_ready,
            },
            'delete': {
                const.DEVICE_OWNER_ROUTER_GW: self.delete_router_port,
                const.DEVICE_OWNER_ROUTER_INTF: self.delete_router_port,
                'default': self.deactivate_port,
            }
        }
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
            nec_router.L3AgentNotifyAPI()
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

    def _update_resource_status(self, context, resource, id, status):
        """Update status of specified resource."""
        request = {'status': status}
        obj_getter = getattr(self, '_get_%s' % resource)
        with context.session.begin(subtransactions=True):
            obj_db = obj_getter(context, id)
            obj_db.update(request)

    def _update_resource_status_if_changed(self, context, resource_type,
                                           resource_dict, new_status):
        if resource_dict['status'] != new_status:
            self._update_resource_status(context, resource_type,
                                         resource_dict['id'],
                                         new_status)
            resource_dict['status'] = new_status

    def _check_ofc_tenant_in_use(self, context, tenant_id):
        """Check if the specified tenant is used."""
        # All networks are created on OFC
        filters = {'tenant_id': [tenant_id]}
        if self.get_networks_count(context, filters=filters):
            return True
        if rdb.get_router_count_by_provider(context.session,
                                            nec_router.PROVIDER_OPENFLOW,
                                            tenant_id):
            return True
        return False

    def _cleanup_ofc_tenant(self, context, tenant_id):
        if not self._check_ofc_tenant_in_use(context, tenant_id):
            try:
                if self.ofc.exists_ofc_tenant(context, tenant_id):
                    self.ofc.delete_ofc_tenant(context, tenant_id)
                else:
                    LOG.debug('_cleanup_ofc_tenant: No OFC tenant for %s',
                              tenant_id)
            except (nexc.OFCException, nexc.OFCMappingNotFound) as exc:
                LOG.warn(_LW("delete_ofc_tenant() failed due to %s"), exc)

    def activate_port_if_ready(self, context, port, network=None):
        """Activate port by creating port on OFC if ready.

        Conditions to activate port on OFC are:
            * port admin_state is UP
            * network admin_state is UP
            * portinfo are available (to identify port on OFC)
        """
        if not network:
            network = super(NECPluginV2Impl,
                            self).get_network(context, port['network_id'])

        if not port['admin_state_up']:
            LOG.debug("activate_port_if_ready(): skip, "
                      "port.admin_state_up is False.")
            return port
        elif not network['admin_state_up']:
            LOG.debug("activate_port_if_ready(): skip, "
                      "network.admin_state_up is False.")
            return port
        elif not ndb.get_portinfo(context.session, port['id']):
            LOG.debug("activate_port_if_ready(): skip, "
                      "no portinfo for this port.")
            return port
        elif self.ofc.exists_ofc_port(context, port['id']):
            LOG.debug("activate_port_if_ready(): skip, "
                      "ofc_port already exists.")
            return port

        try:
            self.ofc.create_ofc_port(context, port['id'], port)
            port_status = const.PORT_STATUS_ACTIVE
        except (nexc.OFCException, nexc.OFCMappingNotFound) as exc:
            LOG.error(_LE("create_ofc_port() failed due to %s"), exc)
            port_status = const.PORT_STATUS_ERROR

        if port_status != port['status']:
            self._update_resource_status(context, "port", port['id'],
                                         port_status)
            port['status'] = port_status

        return port

    def deactivate_port(self, context, port, raise_exc=True):
        """Deactivate port by deleting port from OFC if exists."""
        if not self.ofc.exists_ofc_port(context, port['id']):
            LOG.debug("deactivate_port(): skip, ofc_port for port=%s "
                      "does not exist.", port['id'])
            return port

        try:
            self.ofc.delete_ofc_port(context, port['id'], port)
            self._update_resource_status_if_changed(
                context, "port", port, const.PORT_STATUS_DOWN)
            return port
        except (nexc.OFCResourceNotFound, nexc.OFCMappingNotFound):
            # There is a case where multiple delete_port operation are
            # running concurrently. For example, delete_port from
            # release_dhcp_port and deletion of network owned ports in
            # delete_network. In such cases delete_ofc_port may receive
            # 404 error from OFC.
            # Also there is a case where neutron port is deleted
            # between exists_ofc_port and get_ofc_id in delete_ofc_port.
            # In this case OFCMappingNotFound is raised.
            # These two cases are valid situations.
            LOG.info(_LI("deactivate_port(): OFC port for port=%s is "
                         "already removed."), port['id'])
            # The port is already removed, so there is no need
            # to update status in the database.
            port['status'] = const.PORT_STATUS_DOWN
            return port
        except nexc.OFCException as exc:
            with excutils.save_and_reraise_exception() as ctxt:
                LOG.error(_LE("Failed to delete port=%(port)s from OFC: "
                              "%(exc)s"), {'port': port['id'], 'exc': exc})
                self._update_resource_status_if_changed(
                    context, "port", port, const.PORT_STATUS_ERROR)
                if not raise_exc:
                    ctxt.reraise = False
                    return port

    def _net_status(self, network):
        # NOTE: NEC Plugin accept admin_state_up. When it's False, this plugin
        # deactivate all ports on the network to drop all packet and show
        # status='DOWN' to users. But the network is kept defined on OFC.
        if network['network']['admin_state_up']:
            return const.NET_STATUS_ACTIVE
        else:
            return const.NET_STATUS_DOWN

    def create_network(self, context, network):
        """Create a new network entry on DB, and create it on OFC."""
        LOG.debug("NECPluginV2.create_network() called, "
                  "network=%s .", network)
        tenant_id = self._get_tenant_id_for_create(context, network['network'])
        net_name = network['network']['name']
        net_id = uuidutils.generate_uuid()

        #set up default security groups
        self._ensure_default_security_group(context, tenant_id)

        network['network']['id'] = net_id
        network['network']['status'] = self._net_status(network)

        try:
            if not self.ofc.exists_ofc_tenant(context, tenant_id):
                self.ofc.create_ofc_tenant(context, tenant_id)
            self.ofc.create_ofc_network(context, tenant_id, net_id, net_name)
        except (nexc.OFCException, nexc.OFCMappingNotFound) as exc:
            LOG.error(_LE("Failed to create network id=%(id)s on "
                          "OFC: %(exc)s"), {'id': net_id, 'exc': exc})
            network['network']['status'] = const.NET_STATUS_ERROR

        with context.session.begin(subtransactions=True):
            new_net = super(NECPluginV2Impl, self).create_network(context,
                                                                  network)
            self._process_l3_create(context, new_net, network['network'])

        return new_net

    def update_network(self, context, id, network):
        """Update network and handle resources associated with the network.

        Update network entry on DB. If 'admin_state_up' was changed, activate
        or deactivate ports and packetfilters associated with the network.
        """
        LOG.debug("NECPluginV2.update_network() called, "
                  "id=%(id)s network=%(network)s .",
                  {'id': id, 'network': network})

        if 'admin_state_up' in network['network']:
            network['network']['status'] = self._net_status(network)

        session = context.session
        with session.begin(subtransactions=True):
            old_net = super(NECPluginV2Impl, self).get_network(context, id)
            new_net = super(NECPluginV2Impl, self).update_network(context, id,
                                                                  network)
            self._process_l3_update(context, new_net, network['network'])

        changed = (old_net['admin_state_up'] != new_net['admin_state_up'])
        if changed and not new_net['admin_state_up']:
            # disable all active ports of the network
            filters = dict(network_id=[id], status=[const.PORT_STATUS_ACTIVE])
            ports = super(NECPluginV2Impl, self).get_ports(context,
                                                           filters=filters)
            for port in ports:
                # If some error occurs, status of errored port is set to ERROR.
                # This is avoids too many rollback.
                # TODO(amotoki): Raise an exception after all port operations
                # are finished to inform the caller of API of the failure.
                self.deactivate_port(context, port, raise_exc=False)
        elif changed and new_net['admin_state_up']:
            # enable ports of the network
            filters = dict(network_id=[id], status=[const.PORT_STATUS_DOWN],
                           admin_state_up=[True])
            ports = super(NECPluginV2Impl, self).get_ports(context,
                                                           filters=filters)
            for port in ports:
                self.activate_port_if_ready(context, port, new_net)

        return new_net

    def delete_network(self, context, id):
        """Delete network and packet_filters associated with the network.

        Delete network entry from DB and OFC. Then delete packet_filters
        associated with the network. If the network is the last resource
        of the tenant, delete unnessary ofc_tenant.
        """
        LOG.debug("NECPluginV2.delete_network() called, id=%s .", id)
        net_db = self._get_network(context, id)
        tenant_id = net_db['tenant_id']
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

        # Make sure auto-delete ports on OFC are deleted.
        # If an error occurs during port deletion,
        # delete_network will be aborted.
        for port in [p for p in ports if p['device_owner']
                     in db_base_plugin_v2.AUTO_DELETE_PORT_OWNERS]:
            port = self.deactivate_port(context, port)

        # delete all packet_filters of the network from the controller
        for pf in net_db.packetfilters:
            self.delete_packet_filter(context, pf['id'])

        if self.ofc.exists_ofc_network(context, id):
            try:
                self.ofc.delete_ofc_network(context, id, net_db)
            except (nexc.OFCException, nexc.OFCMappingNotFound) as exc:
                with excutils.save_and_reraise_exception():
                    LOG.error(_LE("delete_network() failed due to %s"), exc)
                    self._update_resource_status(
                        context, "network", net_db['id'],
                        const.NET_STATUS_ERROR)

        super(NECPluginV2Impl, self).delete_network(context, id)

        self._cleanup_ofc_tenant(context, tenant_id)

    def _get_base_binding_dict(self):
        sg_enabled = sg_rpc.is_firewall_enabled()
        vif_details = {portbindings.CAP_PORT_FILTER: sg_enabled,
                       portbindings.OVS_HYBRID_PLUG: sg_enabled}
        binding = {portbindings.VIF_TYPE: portbindings.VIF_TYPE_OVS,
                   portbindings.VIF_DETAILS: vif_details}
        return binding

    def _extend_port_dict_binding_portinfo(self, port_res, portinfo):
        if portinfo:
            port_res[portbindings.PROFILE] = {
                'datapath_id': portinfo['datapath_id'],
                'port_no': portinfo['port_no'],
            }
        elif portbindings.PROFILE in port_res:
            del port_res[portbindings.PROFILE]

    def _validate_portinfo(self, profile):
        key_specs = {
            'datapath_id': {'type:string': None, 'required': True},
            'port_no': {'type:non_negative': None, 'required': True,
                        'convert_to': attrs.convert_to_int}
        }
        msg = attrs._validate_dict_or_empty(profile, key_specs=key_specs)
        if msg:
            raise n_exc.InvalidInput(error_message=msg)

        datapath_id = profile.get('datapath_id')
        port_no = profile.get('port_no')
        try:
            dpid = int(datapath_id, 16)
        except ValueError:
            raise nexc.ProfilePortInfoInvalidDataPathId()
        if dpid > 0xffffffffffffffffL:
            raise nexc.ProfilePortInfoInvalidDataPathId()
        # Make sure dpid is a hex string beginning with 0x.
        dpid = hex(dpid)

        if int(port_no) > 65535:
            raise nexc.ProfilePortInfoInvalidPortNo()

        return {'datapath_id': dpid, 'port_no': port_no}

    def _process_portbindings_portinfo_create(self, context, port_data, port):
        """Add portinfo according to bindings:profile in create_port().

        :param context: neutron api request context
        :param port_data: port attributes passed in PUT request
        :param port: port attributes to be returned
        """
        profile = port_data.get(portbindings.PROFILE)
        # If portbindings.PROFILE is None, unspecified or an empty dict
        # it is regarded that portbinding.PROFILE is not set.
        profile_set = attrs.is_attr_set(profile) and profile
        if profile_set:
            portinfo = self._validate_portinfo(profile)
            portinfo['mac'] = port['mac_address']
            ndb.add_portinfo(context.session, port['id'], **portinfo)
        else:
            portinfo = None
        self._extend_port_dict_binding_portinfo(port, portinfo)

    def _process_portbindings_portinfo_update(self, context, port_data, port):
        """Update portinfo according to bindings:profile in update_port().

        :param context: neutron api request context
        :param port_data: port attributes passed in PUT request
        :param port: port attributes to be returned
        :returns: 'ADD', 'MOD', 'DEL' or None
        """
        if portbindings.PROFILE not in port_data:
            return
        profile = port_data.get(portbindings.PROFILE)
        # If binding:profile is None or an empty dict,
        # it means binding:.profile needs to be cleared.
        # TODO(amotoki): Allow Make None in binding:profile in
        # the API layer. See LP bug #1220011.
        profile_set = attrs.is_attr_set(profile) and profile
        cur_portinfo = ndb.get_portinfo(context.session, port['id'])
        if profile_set:
            portinfo = self._validate_portinfo(profile)
            portinfo_changed = 'ADD'
            if cur_portinfo:
                if (necutils.cmp_dpid(portinfo['datapath_id'],
                                      cur_portinfo.datapath_id) and
                    portinfo['port_no'] == cur_portinfo.port_no):
                    return
                ndb.del_portinfo(context.session, port['id'])
                portinfo_changed = 'MOD'
            portinfo['mac'] = port['mac_address']
            ndb.add_portinfo(context.session, port['id'], **portinfo)
        elif cur_portinfo:
            portinfo_changed = 'DEL'
            portinfo = None
            ndb.del_portinfo(context.session, port['id'])
        else:
            portinfo = None
            portinfo_changed = None
        self._extend_port_dict_binding_portinfo(port, portinfo)
        return portinfo_changed

    def extend_port_dict_binding(self, port_res, port_db):
        super(NECPluginV2Impl, self).extend_port_dict_binding(port_res,
                                                              port_db)
        self._extend_port_dict_binding_portinfo(port_res, port_db.portinfo)

    def _process_portbindings_create(self, context, port_data, port):
        super(NECPluginV2Impl, self)._process_portbindings_create_and_update(
            context, port_data, port)
        self._process_portbindings_portinfo_create(context, port_data, port)

    def _process_portbindings_update(self, context, port_data, port):
        super(NECPluginV2Impl, self)._process_portbindings_create_and_update(
            context, port_data, port)
        portinfo_changed = self._process_portbindings_portinfo_update(
            context, port_data, port)
        return portinfo_changed

    def _get_port_handler(self, operation, device_owner):
        handlers = self.port_handlers[operation]
        handler = handlers.get(device_owner)
        if handler:
            return handler
        else:
            return handlers['default']

    def create_port(self, context, port):
        """Create a new port entry on DB, then try to activate it."""
        LOG.debug("NECPluginV2.create_port() called, port=%s .", port)

        port['port']['status'] = const.PORT_STATUS_DOWN

        port_data = port['port']
        with context.session.begin(subtransactions=True):
            self._ensure_default_security_group_on_port(context, port)
            sgids = self._get_security_groups_on_port(context, port)
            port = super(NECPluginV2Impl, self).create_port(context, port)
            self._process_portbindings_create(context, port_data, port)
            self._process_port_create_security_group(
                context, port, sgids)
            port[addr_pair.ADDRESS_PAIRS] = (
                self._process_create_allowed_address_pairs(
                    context, port,
                    port_data.get(addr_pair.ADDRESS_PAIRS)))
        self.notify_security_groups_member_updated(context, port)

        handler = self._get_port_handler('create', port['device_owner'])
        return handler(context, port)

    def _update_ofc_port_if_required(self, context, old_port, new_port,
                                     portinfo_changed):
        def get_ofport_exist(port):
            return (port['admin_state_up'] and
                    bool(port.get(portbindings.PROFILE)))

        # Determine it is required to update OFC port
        need_add = False
        need_del = False
        need_packet_filter_update = False

        old_ofport_exist = get_ofport_exist(old_port)
        new_ofport_exist = get_ofport_exist(new_port)

        if old_port['admin_state_up'] != new_port['admin_state_up']:
            if new_port['admin_state_up']:
                need_add |= new_ofport_exist
            else:
                need_del |= old_ofport_exist

        if portinfo_changed:
            if portinfo_changed in ['DEL', 'MOD']:
                need_del |= old_ofport_exist
            if portinfo_changed in ['ADD', 'MOD']:
                need_add |= new_ofport_exist
            need_packet_filter_update |= True

        # Update OFC port if required
        if need_del:
            self.deactivate_port(context, new_port)
            if need_packet_filter_update:
                self.deactivate_packet_filters_by_port(context, id)
        if need_add:
            if need_packet_filter_update:
                self.activate_packet_filters_by_port(context, id)
            self.activate_port_if_ready(context, new_port)

    def update_port(self, context, id, port):
        """Update port, and handle packetfilters associated with the port.

        Update network entry on DB. If admin_state_up was changed, activate
        or deactivate the port and packetfilters associated with it.
        """
        LOG.debug("NECPluginV2.update_port() called, "
                  "id=%(id)s port=%(port)s .",
                  {'id': id, 'port': port})
        need_port_update_notify = False
        with context.session.begin(subtransactions=True):
            old_port = super(NECPluginV2Impl, self).get_port(context, id)
            new_port = super(NECPluginV2Impl, self).update_port(context,
                                                                id, port)
            portinfo_changed = self._process_portbindings_update(
                context, port['port'], new_port)
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

        self._update_ofc_port_if_required(context, old_port, new_port,
                                          portinfo_changed)
        return new_port

    def delete_port(self, context, id, l3_port_check=True):
        """Delete port and packet_filters associated with the port."""
        LOG.debug("NECPluginV2.delete_port() called, id=%s .", id)
        # ext_sg.SECURITYGROUPS attribute for the port is required
        # since notifier.security_groups_member_updated() need the attribute.
        # Thus we need to call self.get_port() instead of super().get_port()
        port_db = self._get_port(context, id)
        port = self._make_port_dict(port_db)

        handler = self._get_port_handler('delete', port['device_owner'])
        # handler() raises an exception if an error occurs during processing.
        port = handler(context, port)

        # delete all packet_filters of the port from the controller
        for pf in port_db.packetfilters:
            self.delete_packet_filter(context, pf['id'])

        # if needed, check to see if this is a port owned by
        # and l3-router.  If so, we should prevent deletion.
        if l3_port_check:
            self.prevent_l3_port_deletion(context, id)
        with context.session.begin(subtransactions=True):
            router_ids = self.disassociate_floatingips(
                context, id, do_notify=False)
            super(NECPluginV2Impl, self).delete_port(context, id)

        # now that we've left db transaction, we are safe to notify
        self.notify_routers_updated(context, router_ids)
        self.notify_security_groups_member_updated(context, port)


class NECPluginV2(NECPluginV2Impl):

    _supported_extension_aliases = ["agent",
                                    "allowed-address-pairs",
                                    "binding",
                                    "dhcp_agent_scheduler",
                                    "external-net",
                                    "ext-gw-mode",
                                    "extraroute",
                                    "l3_agent_scheduler",
                                    "packet-filter",
                                    "quotas",
                                    "router",
                                    "router_provider",
                                    "security-group",
                                    ]

    @property
    def supported_extension_aliases(self):
        if not hasattr(self, '_aliases'):
            aliases = self._supported_extension_aliases[:]
            self.setup_extension_aliases(aliases)
            self._aliases = aliases
        return self._aliases

    def __init__(self):
        nec_config.register_plugin_opts()
        super(NECPluginV2, self).__init__()
