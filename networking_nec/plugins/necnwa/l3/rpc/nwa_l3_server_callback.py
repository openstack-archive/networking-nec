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

from neutron.extensions import l3
from neutron import manager
from neutron.plugins.common import constants as plugin_constants
from neutron.plugins.ml2 import rpc
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class NwaL3ServerRpcCallback(rpc.RpcCallbacks):

    RPC_VERSION = '1.0'

    @property
    def l3plugin(self):
        if not hasattr(self, '_l3plugin'):
            self._l3plugin = manager.NeutronManager.get_service_plugins()[
                plugin_constants.L3_ROUTER_NAT]
        return self._l3plugin

    def update_floatingip_status(self, context, floatingip_id, status):
        '''Update operational status for a floating IP.'''
        with context.session.begin(subtransactions=True):
            LOG.debug('New status for floating IP {}: {}'.format(
                floatingip_id, status))
            try:
                self.l3plugin.update_floatingip_status(context,
                                                       floatingip_id,
                                                       status)
            except l3.FloatingIPNotFound:
                LOG.debug("Floating IP: %s no longer present.",
                          floatingip_id)
