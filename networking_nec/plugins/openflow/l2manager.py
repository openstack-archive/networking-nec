# Copyright 2015 NEC Corporation.  All rights reserved.
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

"""This module implements logic to manage logical networks and ports
on an OpenFlow controller.
"""

from oslo_log import log as logging
from oslo_utils import excutils

from neutron.common import constants as const
from neutron.db import db_base_plugin_v2
from neutron.extensions import portbindings

from networking_nec.i18n import _LE, _LI, _LW
from networking_nec.plugins.openflow.db import api as ndb
from networking_nec.plugins.openflow.db import router as rdb
from networking_nec.plugins.openflow import exceptions as nexc
from networking_nec.plugins.openflow import router as router_plugin
from networking_nec.plugins.openflow import utils

LOG = logging.getLogger(__name__)


class L2Manager(object):

    def __init__(self, plugin):
        self._plugin = plugin

        self.port_handlers = {
            'create': {
                const.DEVICE_OWNER_ROUTER_GW: self.plugin.create_router_port,
                const.DEVICE_OWNER_ROUTER_INTF: self.plugin.create_router_port,
                'default': self.activate_port_if_ready,
            },
            'delete': {
                const.DEVICE_OWNER_ROUTER_GW: self.plugin.delete_router_port,
                const.DEVICE_OWNER_ROUTER_INTF: self.plugin.delete_router_port,
                'default': self.deactivate_port,
            }
        }

    @property
    def plugin(self):
        return self._plugin

    @property
    def ofc(self):
        return self._plugin.ofc

    def _check_ofc_tenant_in_use(self, context, tenant_id, deleting=None):
        """Check if the specified tenant is used."""
        # All networks are created on OFC
        filters = {'tenant_id': [tenant_id]}
        net_count = self.plugin.get_networks_count(context, filters=filters)
        if deleting == 'network':
            net_count -= 1
        if net_count:
            return True

        router_count = rdb.get_router_count_by_provider(
            context.session, router_plugin.PROVIDER_OPENFLOW, tenant_id)
        if deleting == 'router':
            router_count -= 1
        if router_count:
            return True

        return False

    def _cleanup_ofc_tenant(self, context, tenant_id, deleting):
        if not self._check_ofc_tenant_in_use(context, tenant_id, deleting):
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
            network = self.plugin.get_network(context, port['network_id'])

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
            utils.update_resource_status(context, "port", port['id'],
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
            utils.update_resource_status_if_changed(
                context, "port", port, const.PORT_STATUS_DOWN,
                ignore_error=True)
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
                utils.update_resource_status_if_changed(
                    context, "port", port, const.PORT_STATUS_ERROR,
                    ignore_error=True)
                if not raise_exc:
                    ctxt.reraise = False
                    return port

    def _net_status(self, network):
        # NOTE: NEC Plugin accept admin_state_up. When it's False, this plugin
        # deactivate all ports on the network to drop all packet and show
        # status='DOWN' to users. But the network is kept defined on OFC.
        if network['admin_state_up']:
            return const.NET_STATUS_ACTIVE
        else:
            return const.NET_STATUS_DOWN

    def get_initial_net_status(self, network):
        return self._net_status(network['network'])
        # TODO(amotoki): Set the network initial status to BUILD and
        # update it to ACTIVE/ERROR after creating a network on OFC.
        # return const.NET_STATUS_BUILD

    def get_initial_port_status(self, port):
        # NOTE(amotoki): Not sure the initial port status should be
        # BUILD or DOWN. Both works with the current nova/neutron.
        return const.PORT_STATUS_DOWN

    def create_network(self, context, network):
        tenant_id = network['tenant_id']
        net_id = network['id']
        net_name = network['name']
        try:
            if not self.ofc.exists_ofc_tenant(context, tenant_id):
                self.ofc.create_ofc_tenant(context, tenant_id)
            self.ofc.create_ofc_network(context, tenant_id, net_id, net_name)
            utils.update_resource_status_if_changed(
                context, "network", network, self._net_status(network))
        except (nexc.OFCException, nexc.OFCMappingNotFound) as exc:
            LOG.error(_LE("Failed to create network id=%(id)s on "
                          "OFC: %(exc)s"), {'id': net_id, 'exc': exc})
            utils.update_resource_status_if_changed(
                context, "network", network, const.NET_STATUS_ERROR)

    def update_network(self, context, id, old_net, new_net):
        changed = (old_net['admin_state_up'] != new_net['admin_state_up'])
        if changed:
            new_status = self._net_status(new_net)
            utils.update_resource_status_if_changed(
                context, "network", new_net, new_status)
        if changed and not new_net['admin_state_up']:
            # disable all active ports of the network
            filters = dict(network_id=[id], status=[const.PORT_STATUS_ACTIVE])
            ports = self.plugin.get_ports(context, filters=filters)
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
            ports = self.plugin.get_ports(context, filters=filters)
            for port in ports:
                self.activate_port_if_ready(context, port, new_net)

    def delete_network(self, context, id, ports=None):
        net_db = self.plugin._get_network(context, id)
        tenant_id = net_db['tenant_id']

        if ports is None:
            ports = self.plugin.get_ports(context,
                                          filters={'network_id': [id]})

        # Make sure auto-delete ports on OFC are deleted.
        # If an error occurs during port deletion,
        # delete_network will be aborted.
        for port in [p for p in ports if p['device_owner']
                     in db_base_plugin_v2.AUTO_DELETE_PORT_OWNERS]:
            port = self.deactivate_port(context, port)

        # delete all packet_filters of the network from the controller
        for pf in net_db.packetfilters:
            self.plugin.delete_packet_filter(context, pf['id'])

        if self.ofc.exists_ofc_network(context, id):
            try:
                self.ofc.delete_ofc_network(context, id, net_db)
            except (nexc.OFCException, nexc.OFCMappingNotFound) as exc:
                with excutils.save_and_reraise_exception():
                    LOG.error(_LE("delete_network() failed due to %s"), exc)
                    utils.update_resource_status(
                        context, "network", net_db['id'],
                        const.NET_STATUS_ERROR)

        self._cleanup_ofc_tenant(context, tenant_id, deleting='network')

    def _get_port_handler(self, operation, device_owner):
        handlers = self.port_handlers[operation]
        handler = handlers.get(device_owner)
        if handler:
            return handler
        else:
            return handlers['default']

    def create_port(self, context, port):
        handler = self._get_port_handler('create', port['device_owner'])
        return handler(context, port)

    @staticmethod
    def get_portinfo(port):
        profile = port.get(portbindings.PROFILE)
        if not profile:
            return
        return {'datapath_id': profile['datapath_id'],
                'port_no': profile['port_no']}

    @staticmethod
    def is_portinfo_changed(old_port, new_port):
        """Check portinfo is changed or not.

        :param old_port: old port information
        :param new_port: new port information
        :returns: 'ADD', 'MOD', 'DEL' or None
        """
        old_portinfo = L2Manager.get_portinfo(old_port)
        new_portinfo = L2Manager.get_portinfo(new_port)

        # portinfo has been validated, so we can assume
        # portinfo is either None or a valid dict.
        if not old_portinfo and not new_portinfo:
            return
        elif old_portinfo and not new_portinfo:
            return 'DEL'
        elif not old_portinfo and new_portinfo:
            return 'ADD'
        else:
            if (utils.cmp_dpid(old_portinfo['datapath_id'],
                               new_portinfo['datapath_id']) and
                    old_portinfo['port_no'] == new_portinfo['port_no']):
                return
            else:
                return 'MOD'

    @staticmethod
    def get_ofport_exist(port):
        return (port['admin_state_up'] and
                bool(port.get(portbindings.PROFILE)))

    def _update_ofc_port_if_required(self, context, old_port, new_port):
        # Determine it is required to update OFC port
        need_add = False
        need_del = False
        need_packet_filter_update = False

        old_ofport_exist = self.get_ofport_exist(old_port)
        new_ofport_exist = self.get_ofport_exist(new_port)
        portinfo_changed = self.is_portinfo_changed(old_port, new_port)

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
                self.plugin.deactivate_packet_filters_by_port(context, id)
        if need_add:
            if need_packet_filter_update:
                self.plugin.activate_packet_filters_by_port(context, id)
            self.activate_port_if_ready(context, new_port)

    def update_port(self, context, old_port, new_port):
        self._update_ofc_port_if_required(context, old_port, new_port)
        return new_port

    def delete_port(self, context, id):
        # ext_sg.SECURITYGROUPS attribute for the port is required
        # since notifier.security_groups_member_updated() need the attribute.
        # Thus we need to call self.get_port() instead of super().get_port()
        port_db = self.plugin._get_port(context, id)
        port = self.plugin._make_port_dict(port_db)

        handler = self._get_port_handler('delete', port['device_owner'])
        # handler() raises an exception if an error occurs during processing.
        port = handler(context, port)

        # delete all packet_filters of the port from the controller
        for pf in port_db['packetfilters']:
            self.plugin.delete_packet_filter(context, pf['id'])

        return port
