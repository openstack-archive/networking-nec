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

import sqlalchemy as sa
from sqlalchemy import or_

from neutron.api.rpc.agentnotifiers import l3_rpc_agent_api
from neutron.api.rpc.handlers import l3_rpc
from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.db import common_db_mixin
from neutron.db import extraroute_db
from neutron.db import l3_agentschedulers_db
from neutron.db import l3_db
from neutron.db import l3_gwmode_db
from neutron.plugins.common import constants
from neutron.plugins.ml2 import driver_context
from neutron.services import service_base
from neutron_lib import constants as n_const
from neutron_lib import exceptions as exc
from oslo_config import cfg
from oslo_log import helpers
from oslo_log import log as logging

from networking_nec._i18n import _LI, _LW, _LE
from networking_nec.nwa.common import utils as nwa_com_utils
from networking_nec.nwa.l2 import db_api as nwa_db
from networking_nec.nwa.l2 import utils as nwa_l2_utils
from networking_nec.nwa.l3 import db_api as nwa_l3_db
from networking_nec.nwa.l3.rpc import nwa_l3_proxy_api
from networking_nec.nwa.l3.rpc import nwa_l3_server_callback

LOG = logging.getLogger(__name__)


class NECNWAL3Plugin(service_base.ServicePluginBase,
                     common_db_mixin.CommonDbMixin,
                     extraroute_db.ExtraRoute_db_mixin,
                     l3_gwmode_db.L3_NAT_db_mixin,
                     l3_agentschedulers_db.L3AgentSchedulerDbMixin):

    supported_extension_aliases = ["router", "ext-gw-mode",
                                   "extraroute"]

    def __init__(self):
        super(NECNWAL3Plugin, self).__init__()
        l3_db.subscribe()
        self.start_rpc_listeners()
        self.nwa_proxies = {}
        self.resource_groups = nwa_com_utils.load_json_from_file(
            'resource_group', cfg.CONF.NWA.resource_group_file,
            cfg.CONF.NWA.resource_group, default_value=[])

    @helpers.log_method_call
    def start_rpc_listeners(self):
        # RPC support
        self.topic = topics.L3PLUGIN
        self.conn = n_rpc.create_connection()
        self.agent_notifiers.update(
            {n_const.AGENT_TYPE_L3: l3_rpc_agent_api.L3AgentNotifyAPI()})
        self.endpoints = [l3_rpc.L3RpcCallback(),
                          nwa_l3_server_callback.NwaL3ServerRpcCallback()]
        self.conn.create_consumer(self.topic, self.endpoints,
                                  fanout=False)
        return self.conn.consume_in_threads()

    def get_plugin_type(self):
        return constants.L3_ROUTER_NAT

    def get_plugin_description(self):
        """Returns string description of the plugin."""
        return "NEC NWA Plugin based routing"

    @helpers.log_method_call
    def create_floatingip(self, context, floatingip,
                          initial_status=n_const.FLOATINGIP_STATUS_DOWN):
        return super(NECNWAL3Plugin, self).create_floatingip(
            context, floatingip, initial_status)

    def _delete_nat(self, context, fip):
        if not fip['router_id'] or not fip['fixed_ip_address']:
            LOG.debug('already deleted %s', fip)
            return
        tenant_id = nwa_l3_db.get_tenant_id_by_router(
            context.session, fip['router_id']
        )
        nwa_tenant_id = nwa_com_utils.get_nwa_tenant_id(tenant_id)

        fl_data = {
            'floating_ip_address': fip['floating_ip_address'],
            'fixed_ip_address': fip['fixed_ip_address'],
            'id': fip['id'],
            'device_id': fip['router_id'],
            'floating_network_id': fip['floating_network_id'],
            'tenant_id': fip['tenant_id']
        }
        LOG.info(_LI('delete_nat fl_data=%s'), fl_data)

        proxy = self._get_nwa_proxy(self, tenant_id)
        proxy.delete_nat(
            context, tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            floating=fl_data
        )

    # pylint: disable=arguments-differ
    @helpers.log_method_call
    def disassociate_floatingips(self, context, port_id, do_notify=True):
        floating_ips = context.session.query(l3_db.FloatingIP).filter(
            or_(l3_db.FloatingIP.fixed_port_id == port_id,
                l3_db.FloatingIP.floating_port_id == port_id)
        )
        if not floating_ips:
            LOG.warning(_LW('floatingip not found %s'), port_id)
        for fip in floating_ips:
            self._delete_nat(context, fip)
        router_ids = super(NECNWAL3Plugin, self).disassociate_floatingips(
            context, port_id, do_notify)
        return router_ids

    @helpers.log_method_call
    def update_floatingip(self, context, fpid, floatingip):
        port_id_specified = 'port_id' in floatingip['floatingip']
        if not port_id_specified:
            LOG.error(_LE("port_id key is not found in %s"), floatingip)
            raise exc.PortNotFound(port_id=None)

        port_id = floatingip['floatingip'].get('port_id')
        try:
            if port_id_specified and not port_id:
                floating = context.session.query(l3_db.FloatingIP).filter_by(
                    id=fpid).one()
                self._delete_nat(context, floating)
        except sa.orm.exc.NoResultFound:
            raise exc.PortNotFound(port_id=port_id)

        ret = super(NECNWAL3Plugin, self).update_floatingip(
            context, fpid, floatingip)

        try:
            if port_id_specified and port_id:
                floating = context.session.query(l3_db.FloatingIP).filter_by(
                    id=fpid).one()
                tenant_id = nwa_l3_db.get_tenant_id_by_router(
                    context.session,
                    floating['router_id']
                )
                nwa_tenant_id = nwa_com_utils.get_nwa_tenant_id(tenant_id)

                fl_data = {
                    'floating_ip_address': floating['floating_ip_address'],
                    'fixed_ip_address': floating['fixed_ip_address'],
                    'id': fpid, 'device_id': floating['router_id'],
                    'floating_network_id': floating['floating_network_id'],
                    'tenant_id': floating['tenant_id'],
                    'floating_port_id': floating['floating_port_id']
                }
                LOG.info(_LI('setting_nat fl_data is %s'), fl_data)
                proxy = self._get_nwa_proxy(self, tenant_id)
                proxy.setting_nat(
                    context, tenant_id=tenant_id,
                    nwa_tenant_id=nwa_tenant_id,
                    floating=fl_data
                )

        except sa.orm.exc.NoResultFound:
            raise exc.PortNotFound(port_id=port_id)

        return ret

    def add_router_interface(self, context, router_id, interface_info):
        ret = super(NECNWAL3Plugin, self).add_router_interface(
            context,
            router_id,
            interface_info
        )
        if 'port_id' in interface_info:
            self._add_router_interface_by_port(
                self, context, router_id, interface_info
            )
        return ret

    def _add_router_interface_by_port(self, plugin, context, router_id,
                                      interface_info):
        try:
            session = context.session
            port = plugin._core_plugin._get_port(context,
                                                 interface_info['port_id'])
            network = plugin._core_plugin.get_network(context,
                                                      port['network_id'])

            binding = nwa_db.ensure_port_binding(session, port['id'])
            port_context = driver_context.PortContext(plugin._core_plugin,
                                                      context, port,
                                                      network, binding, None)

            nwa_info = nwa_l2_utils.portcontext_to_nwa_info(
                port_context, self.resource_groups)
            rt_tid = nwa_l3_db.get_tenant_id_by_router(
                session, router_id
            )
            nwa_rt_tid = nwa_com_utils.get_nwa_tenant_id(rt_tid)
            nwa_info['tenant_id'] = rt_tid
            nwa_info['nwa_tenant_id'] = nwa_rt_tid
            proxy = self._get_nwa_proxy(plugin, rt_tid)
            proxy.create_tenant_fw(
                port_context.network._plugin_context,
                rt_tid,
                nwa_rt_tid,
                nwa_info
            )

        except Exception as e:
            LOG.exception(_LE("create tenant firewall %s"), e)

    def _get_nwa_proxy(self, plugin, tenant_id):
        proxy = plugin._core_plugin.get_nwa_proxy(tenant_id)
        return nwa_l3_proxy_api.NwaL3ProxyApi(proxy.client)
