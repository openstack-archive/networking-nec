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

from neutron.common import topics
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec._i18n import _LW
from networking_nec.common import utils
from networking_nec.nwa.common import exceptions as nwa_exc
from networking_nec.nwa.l2.rpc import tenant_binding_api

LOG = logging.getLogger(__name__)


def catch_exception_and_update_tenant_binding(method):

    def wrapper(obj, context, **kwargs):
        try:
            return method(obj, context, **kwargs)
        except nwa_exc.AgentProxyException as e:
            tenant_id = kwargs.get('tenant_id')
            nwa_tenant_id = kwargs.get('nwa_tenant_id')
            nwa_data = e.value
            return obj.proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data)

    return wrapper


class AgentProxyTenant(object):

    def __init__(self, agent_top, client):
        self.agent_top = agent_top
        self.client = client
        self.nwa_tenant_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN)

    @utils.log_method_return_value
    def create_tenant(self, context, **kwargs):
        """create tenant

        @param context: contains user information.
        @param kwargs: nwa_tenant_id
        @return: succeed - dict of status, and information.
        """
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        status_code, __data = self.client.tenant.create_tenant(nwa_tenant_id)
        if status_code in (200, 500):  # success(200), already exists(500)
            return {
                'CreateTenant': True,
                'NWA_tenant_id': nwa_tenant_id
            }
        raise nwa_exc.AgentProxyException(value=status_code)

    @utils.log_method_return_value
    def delete_tenant(self, context, **kwargs):
        """delete tenant.

        @param context: contains user information.
        @param kwargs: nwa_tenant_id
        @return: result(succeed = (True, dict(empty)  other = False, None)
        """
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        rcode, body = self.client.tenant.delete_tenant(nwa_tenant_id)
        if rcode != 200:
            LOG.warning(_LW('unexpected status code %s in delete_tenant'),
                        rcode)
        return body

    @utils.log_method_return_value
    def update_tenant_binding(
            self, context, tenant_id, nwa_tenant_id,
            nwa_data, nwa_created=False
    ):
        """Update Tenant Binding on NECNWAL2Plugin.

        @param context:contains user information.
        @param tenant_id: Openstack Tenant UUID
        @param nwa_tenant_id: NWA Tenand ID
        @param nwa_data: nwa_tenant_binding data.
        @param nwa_created: flag of operation. True = Create, False = Update
        @return: dict of status and msg.
        """
        LOG.debug("nwa_data=%s", jsonutils.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))
        if nwa_created:
            return self.nwa_tenant_rpc.add_nwa_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )

        return self.nwa_tenant_rpc.set_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id, nwa_data
        )
