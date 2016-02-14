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

from oslo_log import log as logging

from networking_nec._i18n import _LI

LOG = logging.getLogger(__name__)

KEY_CREATE_TENANT_NW = 'CreateTenantNW'


class NwaL2Network(object):

    def __init__(self, nwa_tenant_rpc, proxy_tenant, proxy_l2):
        self._nwa_tenant_rpc = nwa_tenant_rpc
        self._proxy_tenant = proxy_tenant
        self._proxy_l2 = proxy_l2

    def start(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        network_id = nwa_info['network']['id']
        LOG.debug("tenant_id=%(tenant_id)s, network_id=%(network_id)s, "
                  "device_owner=%(device_owner)s",
                  {'tenant_id': tenant_id,
                   'network_id': network_id,
                   'device_owner': nwa_info['device']['owner']})

        nwa_data = self._nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        # create tenant
        if not nwa_data:
            rcode, nwa_data = self._proxy_tenant.create_tenant(context,
                                                               **kwargs)
            if not self._proxy_tenant.update_tenant_binding(
                    context, tenant_id, nwa_tenant_id,
                    nwa_data, nwa_created=True):
                return None

        # create tenant nw
        if KEY_CREATE_TENANT_NW not in nwa_data:
            rcode, __ = self._proxy_l2._create_tenant_nw(
                context, nwa_data=nwa_data, **kwargs)
            if not rcode:
                return self._proxy_tenant.update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data,
                    nwa_created=False
                )

        # create vlan
        nw_vlan_key = 'NW_' + network_id
        if nw_vlan_key not in nwa_data:
            rcode, __ = self._proxy_l2._create_vlan(
                context, nwa_data=nwa_data, **kwargs)
            if not rcode:
                return self._proxy_tenant.update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data,
                    nwa_created=False
                )
        return nwa_data

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
            return self._proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )

        # delete vlan
        result, ret_val = self._proxy_l2._delete_vlan(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        if not result:
            # delete vlan error.
            return self._proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete vlan end.

        # tenant network check.
        for k in nwa_data:
            if re.match('NW_.*', k):
                return self._proxy_tenant.update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data
                )

        # delete tenant network
        LOG.info(_LI("delete_tenant_nw"))
        result, ret_val = self._proxy_l2._delete_tenant_nw(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        if not result:
            return self._proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete tenant network end

        # delete tenant
        LOG.info(_LI("delete_tenant"))
        result, ret_val = self._proxy_tenant.delete_tenant(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        if not result:
            return self._proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete tenant end.

        # delete nwa_tenant binding.
        LOG.info(_LI("delete_nwa_tenant_binding"))
        return self._nwa_tenant_rpc.delete_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )
