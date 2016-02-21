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

import re

from neutron.common import topics
from oslo_log import helpers
from oslo_log import log as logging

from networking_nec._i18n import _LI
from networking_nec.plugins.necnwa.agent import proxy_tenant as tenant_util
from networking_nec.plugins.necnwa.common import exceptions as nwa_exc
from networking_nec.plugins.necnwa.l2.rpc import tenant_binding_api

LOG = logging.getLogger(__name__)

KEY_CREATE_TENANT_NW = 'CreateTenantNW'


class NwaL2Network(object):

    def __init__(self, agent_top):
        self._agent_top = agent_top
        self._nwa_tenant_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN)

    @property
    def _proxy_tenant(self):
        return self._agent_top.proxy_tenant

    @property
    def _proxy_l2(self):
        return self._agent_top.proxy_l2

    @helpers.log_method_call
    @tenant_util.catch_exception_and_update_tenant_binding
    def start(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        network_id = nwa_info['network']['id']

        nwa_data = self._nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        # create tenant
        if not nwa_data:
            nwa_data = self._proxy_tenant.create_tenant(context, **kwargs)
            if not self._proxy_tenant.update_tenant_binding(
                    context, tenant_id, nwa_tenant_id,
                    nwa_data, nwa_created=True):
                return None

        # create tenant nw
        if KEY_CREATE_TENANT_NW not in nwa_data:
            # raise AgentProxyException if fail
            self._proxy_l2._create_tenant_nw(context, nwa_data=nwa_data,
                                             **kwargs)

        # create vlan
        nw_vlan_key = 'NW_' + network_id
        if nw_vlan_key not in nwa_data:
            # raise AgentProxyException if fail
            self._proxy_l2._create_vlan(context, nwa_data=nwa_data, **kwargs)

        return nwa_data

    @helpers.log_method_call
    @tenant_util.catch_exception_and_update_tenant_binding
    def terminate(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        network_id = nwa_info['network']['id']
        nwa_data = self._nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )
        # port check on segment.
        if self._proxy_l2.check_vlan(network_id, nwa_data):
            raise nwa_exc.AgentProxyException(value=nwa_data)

        # delete vlan
        # raise AgentProxyException if fail
        nwa_data = self._proxy_l2._delete_vlan(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        # delete vlan end.

        # tenant network check.
        for k in nwa_data:
            if re.match('NW_.*', k):
                raise nwa_exc.AgentProxyException(value=nwa_data)

        # delete tenant network
        LOG.info(_LI("delete_tenant_nw"))
        # raise AgentProxyException if fail
        nwa_data = self._proxy_l2._delete_tenant_nw(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        # delete tenant network end

        # delete tenant
        LOG.info(_LI("delete_tenant"))
        # raise AgentProxyException if fail
        nwa_data = self._proxy_tenant.delete_tenant(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        # delete tenant end.

        # delete nwa_tenant binding.
        LOG.info(_LI("delete_nwa_tenant_binding"))
        return self._nwa_tenant_rpc.delete_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )
