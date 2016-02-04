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

from neutron.common import constants as q_const
from neutron.db import api as db_api
from neutron.extensions import portbindings
from neutron.extensions import portsecurity as psec
from neutron import manager
from neutron.plugins.ml2 import db as db_ml2
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2 import rpc
from oslo_log import log as logging

from networking_nec._i18n import _LW
from networking_nec.plugins.necnwa.l2 import db_api as necnwa_api

LOG = logging.getLogger(__name__)


class NwaML2ServerRpcCallbacks(rpc.RpcCallbacks):

    RPC_VERSION = '1.0'

    def get_device_details(self, rpc_context, **kwargs):
        """Agent requests device details."""
        agent_id = kwargs.get('agent_id')
        device = kwargs.get('device')
        host = kwargs.get('host')
        # cached networks used for reducing number of network db calls
        # for server internal usage only
        cached_networks = kwargs.get('cached_networks')
        LOG.debug("Device %(device)s details requested by agent "
                  "%(agent_id)s with host %(host)s",
                  {'device': device, 'agent_id': agent_id, 'host': host})

        plugin = manager.NeutronManager.get_plugin()
        port_id = plugin._device_to_port_id(device)
        port_context = plugin.get_bound_port_context(rpc_context,
                                                     port_id,
                                                     host,
                                                     cached_networks)
        if not port_context:
            LOG.warning(_LW("Device %(device)s requested by agent "
                            "%(agent_id)s not found in database"),
                        {'device': device, 'agent_id': agent_id})
            return {'device': device}

        segment = port_context.bottom_bound_segment

        port = port_context.current
        # caching information about networks for future use
        if cached_networks is not None:
            if port['network_id'] not in cached_networks:
                cached_networks[port['network_id']] = (
                    port_context.network.current)
        if not segment:
            LOG.warning(_LW("Device %(device)s requested by agent "
                            "%(agent_id)s on network %(network_id)s not "
                            "bound, vif_type: %(vif_type)s"),
                        {'device': device,
                         'agent_id': agent_id,
                         'network_id': port['network_id'],
                         'vif_type': port[portbindings.VIF_TYPE]})
            return {'device': device}

        elif segment['segmentation_id'] == 0:
            LOG.warning(_LW("Device %(device)s requested by agent "
                            "%(agent_id)s, segment %(segment_id)s has "
                            "network %(network_id)s not no segment from NWA"),
                        {'device': device, 'agent_id': agent_id,
                         'segment_id': segment['id'],
                         'network_id': port['network_id']})
            return {'device': device}

        if (not host or host == port_context.host):
            new_status = (q_const.PORT_STATUS_BUILD if port['admin_state_up']
                          else q_const.PORT_STATUS_DOWN)
            if (
                    port['status'] != new_status and
                    port['status'] != q_const.PORT_STATUS_ACTIVE
            ):
                plugin.update_port_status(rpc_context,
                                          port_id,
                                          new_status,
                                          host)

        entry = {'device': device,
                 'network_id': port['network_id'],
                 'port_id': port_id,
                 'mac_address': port['mac_address'],
                 'admin_state_up': port['admin_state_up'],
                 'network_type': segment[api.NETWORK_TYPE],
                 'segmentation_id': segment[api.SEGMENTATION_ID],
                 'physical_network': segment[api.PHYSICAL_NETWORK],
                 'fixed_ips': port['fixed_ips'],
                 'device_owner': port['device_owner'],
                 'allowed_address_pairs': port['allowed_address_pairs'],
                 'port_security_enabled': port.get(psec.PORTSECURITY, True),
                 'profile': port[portbindings.PROFILE]}
        LOG.debug("Returning: %s", entry)
        return entry

    def _get_device_details(self, rpc_context, **kwargs):
        """Agent requests device details."""
        agent_id = kwargs.get('agent_id')
        device = kwargs.get('device')
        host = kwargs.get('host')
        LOG.debug("Device %(device)s details requested by agent "
                  "%(agent_id)s with host %(host)s",
                  {'device': device, 'agent_id': agent_id, 'host': host})

        plugin = manager.NeutronManager.get_plugin()
        port_id = plugin._device_to_port_id(device)
        port_context = plugin.get_bound_port_context(rpc_context,
                                                     port_id,
                                                     host)
        if not port_context:
            LOG.warning(_LW("Device %(device)s requested by agent "
                            "%(agent_id)s not found in database"),
                        {'device': device, 'agent_id': agent_id})
            return {'device': device}

        port = port_context.current

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            segments = db_ml2.get_network_segments(session, port['network_id'],
                                                   filter_dynamic=True)
            if not segments:
                LOG.warning(_LW("Device %(device)s requested by agent "
                                "%(agent_id)s has network %(network_id)s not "
                                "no segment"),
                            {'device': device, 'agent_id': agent_id,
                             'network_id': port['network_id']})
                return {'device': device}
            elif len(segments) != 1:
                LOG.warning(_LW("Device %(device)s requested by agent "
                                "%(agent_id)s has network %(network_id)s not "
                                "no segment size miss mach"),
                            {'device': device, 'agent_id': agent_id,
                             'network_id': port['network_id']})
                return {'device': device}
            elif segments[0]['segmentation_id'] == 0:
                LOG.warning(_LW("Device %(device)s requested by agent "
                                "%(agent_id)s, segment %(segment_id)s has "
                                "network %(network_id)s not "
                                "no segment from NWA"),
                            {'device': device, 'agent_id': agent_id,
                             'segment_id': segments[0]['id'],
                             'network_id': port['network_id']})
                return {'device': device}

            binding = necnwa_api.ensure_port_binding(session, port_id)

            if not binding.segment_id:
                LOG.warning(_LW("Device %(device)s requested by agent "
                                "%(agent_id)s on network %(network_id)s not "
                                "bound, vif_type: %(vif_type)s"),
                            {'device': device,
                             'agent_id': agent_id,
                             'network_id': port['network_id'],
                             'vif_type': binding.vif_type})
                return {'device': device}

        port = port_context.current

        new_status = (q_const.PORT_STATUS_BUILD if port['admin_state_up']
                      else q_const.PORT_STATUS_DOWN)

        if (
                port['status'] != new_status and
                port['status'] != q_const.PORT_STATUS_ACTIVE
        ):
            plugin.update_port_status(rpc_context,
                                      port_id,
                                      new_status,
                                      host)

        entry = {'device': device,
                 'network_id': port['network_id'],
                 'port_id': port_id,
                 'mac_address': port['mac_address'],
                 'admin_state_up': port['admin_state_up'],
                 'network_type': segments[0]['network_type'],
                 'segmentation_id': segments[0]['segmentation_id'],
                 'physical_network': segments[0]['physical_network'],
                 'fixed_ips': port['fixed_ips'],
                 'device_owner': port['device_owner'],
                 'profile': port[portbindings.PROFILE]}
        LOG.debug("Returning: %s", entry)
        return entry

    def update_device_up(self, rpc_context, **kwargs):
        """Device is up on agent."""

        agent_id = kwargs.get('agent_id')  # noqa
        # device = kwargs.get('device')

        # plugin = manager.NeutronManager.get_plugin()
        # port_id = plugin._device_to_port_id(device)

        return
