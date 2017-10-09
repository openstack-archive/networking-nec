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

from oslo_config import cfg

from neutron.extensions import portbindings
from neutron.extensions import portsecurity as psec
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2 import rpc
from neutron_lib import constants
from neutron_lib.plugins import directory
from neutron_lib.services.qos import constants as qos_consts
from oslo_log import log as logging

from networking_nec._i18n import _LW, _LI


LOG = logging.getLogger(__name__)


class NwaML2ServerRpcCallbacks(rpc.RpcCallbacks):

    RPC_VERSION = '1.0'

    def __init__(self, notifier, type_manager, necnwa_router=True):
        super(NwaML2ServerRpcCallbacks, self).__init__(notifier, type_manager)
        self.necnwa_router = cfg.CONF.NWA.use_necnwa_router

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

        plugin = directory.get_plugin()
        port_id = plugin._device_to_port_id(rpc_context, device)
        port_context = plugin.get_bound_port_context(rpc_context,
                                                     port_id,
                                                     host,
                                                     cached_networks)
        if not port_context:
            LOG.debug("Device %(device)s requested by agent "
                      "%(agent_id)s not found in database",
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
                         'vif_type': port_context.vif_type})
            return {'device': device}

        if segment['segmentation_id'] == 0:
            entry = {'device': device}
            LOG.info(_LI('The segmentation_id is not yet finalized, '
                         'it is replaced to return %s'), entry)
            return entry

        if not host or host == port_context.host:
            new_status = (constants.PORT_STATUS_BUILD if port['admin_state_up']
                          else constants.PORT_STATUS_DOWN)
            if (
                    port['status'] != new_status and
                    port['status'] != constants.PORT_STATUS_ACTIVE
            ):
                plugin.update_port_status(rpc_context,
                                          port_id,
                                          new_status,
                                          host,
                                          port_context.network.current)

        network_qos_policy_id = port_context.network._network.get(
            qos_consts.QOS_POLICY_ID)
        entry = {'device': device,
                 'network_id': port['network_id'],
                 'port_id': port['id'],
                 'mac_address': port['mac_address'],
                 'admin_state_up': port['admin_state_up'],
                 'network_type': segment[api.NETWORK_TYPE],
                 'segmentation_id': segment[api.SEGMENTATION_ID],
                 'physical_network': segment[api.PHYSICAL_NETWORK],
                 'fixed_ips': port['fixed_ips'],
                 'device_owner': port['device_owner'],
                 'allowed_address_pairs': port['allowed_address_pairs'],
                 'port_security_enabled': port.get(psec.PORTSECURITY, True),
                 'qos_policy_id': port.get(qos_consts.QOS_POLICY_ID),
                 'network_qos_policy_id': network_qos_policy_id,
                 'profile': port[portbindings.PROFILE]}
        if 'security_groups' in port:
            entry['security_groups'] = port['security_groups']
        LOG.debug("Returning: %s", entry)
        return entry

    def update_device_up(self, rpc_context, **kwargs):
        """Device is up on agent."""
        if self.necnwa_router:
            return
        super(NwaML2ServerRpcCallbacks, self).update_device_up(rpc_context,
                                                               **kwargs)
