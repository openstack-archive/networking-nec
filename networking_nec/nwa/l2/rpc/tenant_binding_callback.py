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

from neutron.db import api as db_api
from neutron import manager
from oslo_log import helpers
from oslo_log import log as logging
import oslo_messaging
from oslo_serialization import jsonutils

from networking_nec._i18n import _LI
from networking_nec.nwa.l2 import db_api as necnwa_api

LOG = logging.getLogger(__name__)


class TenantBindingServerRpcCallback(object):

    target = oslo_messaging.Target(version='1.0')

    @helpers.log_method_call
    def get_nwa_tenant_binding(self, rpc_context, **kwargs):
        """get nwa_tenant_binding from neutorn db.

        @param rpc_context: rpc context.
        @param kwargs: tenant_id, nwa_tenant_id
        @return: success = dict of nwa_tenant_binding, error = dict of empty.
        """
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            recode = necnwa_api.get_nwa_tenant_binding(
                session, tenant_id, nwa_tenant_id
            )
            if recode is not None:
                LOG.debug(
                    "nwa_data=%s", jsonutils.dumps(
                        recode.value_json, indent=4, sort_keys=True)
                )
                return recode.value_json

        return {}

    @helpers.log_method_call
    def add_nwa_tenant_binding(self, rpc_context, **kwargs):
        """get nwa_tenant_binding from neutorn db.

        @param rpc_context: rpc context.
        @param kwargs: tenant_id, nwa_tenant_id
        @return: dict of status
        """

        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            if necnwa_api.add_nwa_tenant_binding(
                    session,
                    tenant_id,
                    nwa_tenant_id,
                    nwa_data
            ):
                return {'status': 'SUCCESS'}

        return {'status': 'FAILED'}

    @helpers.log_method_call
    def set_nwa_tenant_binding(self, rpc_context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')
        LOG.debug(
            "nwa_data=%s", jsonutils.dumps(nwa_data, indent=4, sort_keys=True)
        )

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            if necnwa_api.set_nwa_tenant_binding(
                    session,
                    tenant_id,
                    nwa_tenant_id,
                    nwa_data
            ):
                return {'status': 'SUCCESS'}

        return {'status': 'FAILED'}

    @helpers.log_method_call
    def delete_nwa_tenant_binding(self, rpc_context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            if necnwa_api.del_nwa_tenant_binding(
                    session,
                    tenant_id,
                    nwa_tenant_id
            ):
                return {'status': 'SUCCESS'}

        return {'status': 'FAILED'}

    def update_tenant_rpc_servers(self, rpc_context, **kwargs):
        session = db_api.get_session()

        with session.begin(subtransactions=True):
            q_tids = [q.tenant_id
                      for q in necnwa_api.get_nwa_tenant_queues(session)]
        plugin = manager.NeutronManager.get_plugin()
        tenant_ids = [server['tenant_id'] for server in kwargs['servers']]
        ret = []
        for tenant_id in set(q_tids) - set(tenant_ids):
            LOG.info(_LI("RPCServer only db tid=%s, send create_server"),
                     tenant_id)
            plugin.nwa_rpc.create_server(rpc_context, tenant_id)
            ret.append({'tenant_id': tenant_id})
        for tenant_id in set(tenant_ids) - set(q_tids):
            LOG.info(_LI("RPCServer only agent tid=%s, send delete_server"),
                     tenant_id)
            plugin.nwa_rpc.delete_server(rpc_context, tenant_id)
        return {'servers': ret}
