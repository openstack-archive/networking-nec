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
from neutron.common import constants as q_const
from neutron.common import exceptions as exc
from neutron.common import rpc as q_rpc
from neutron.common import topics
from neutron.db import db_base_plugin_v2
from neutron.db import extraroute_db
from neutron.db import l3_agentschedulers_db
from neutron.db import l3_db
from neutron.db import l3_gwmode_db
from neutron.plugins.common import constants
from neutron.plugins.ml2 import driver_context
from oslo_log import helpers
from oslo_log import log as logging

from networking_nec._i18n import _LI, _LW, _LE
from networking_nec.plugins.necnwa.common import utils as nwa_com_utils
from networking_nec.plugins.necnwa.l2 import db_api as nwa_db
from networking_nec.plugins.necnwa.l2 import utils as nwa_l2_utils
from networking_nec.plugins.necnwa.l3 import db_api as nwa_l3_db

LOG = logging.getLogger(__name__)


class NECNWAL3Plugin(db_base_plugin_v2.NeutronDbPluginV2,
                     extraroute_db.ExtraRoute_db_mixin,
                     l3_gwmode_db.L3_NAT_db_mixin,
                     l3_agentschedulers_db.L3AgentSchedulerDbMixin):

    supported_extension_aliases = ["router", "ext-gw-mode",
                                   "extraroute"]

    def __init__(self):
        super(NECNWAL3Plugin, self).__init__()

        self.setup_rpc()
        self.nwa_proxies = dict()

    def setup_rpc(self):
        # RPC support
        self.topic = topics.L3PLUGIN
        self.conn = q_rpc.create_connection(new=True)
        self.agent_notifiers[q_const.AGENT_TYPE_L3] = \
            l3_rpc_agent_api.L3AgentNotifyAPI()
        self.endpoints = [l3_rpc.L3RpcCallback()]
        self.conn.create_consumer(self.topic, self.endpoints,
                                  fanout=False)
        self.conn.consume_in_threads()

    def get_plugin_type(self):
        return constants.L3_ROUTER_NAT

    def get_plugin_description(self):
        """Returns string description of the plugin."""
        return "NEC NWA Plugin based routing"

    def create_floatingip(self, context, floatingip):
        return super(NECNWAL3Plugin, self).create_floatingip(
            self, context, floatingip,
            initial_status=q_const.FLOATINGIP_STATUS_DOWN
        )

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
        LOG.info(_LI('delete_nat fl_data={}').format(fl_data))

        proxy = self._core_plugin.get_nwa_proxy(tenant_id)
        proxy.delete_nat(
            context, tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            floating=fl_data
        )

    @helpers.log_method_call
    def disassociate_floatingips(self, context, port_id, do_notify=True):
        try:
            floating_ips = context.session.query(l3_db.FloatingIP).filter(
                or_(l3_db.FloatingIP.fixed_port_id == port_id,
                    l3_db.FloatingIP.floating_port_id == port_id)
            )
            for fip in floating_ips:
                self._delete_nat(context, fip)
        except sa.orm.exc.NoResultFound:
            LOG.warning(_LW('floatingip not found {}').format(port_id))

        router_ids = super(NECNWAL3Plugin, self).disassociate_floatingips(
            self, context, port_id, do_notify)
        return router_ids

    @helpers.log_method_call
    def update_floatingip(self, context, id_, floatingip):
        port_id_specified = 'port_id' in floatingip['floatingip']
        port_id = floatingip['floatingip'].get('port_id')
        if not port_id_specified:
            LOG.warning(_LW("port_id not found."))

        try:
            if port_id_specified and not port_id:
                floating = context.session.query(l3_db.FloatingIP).filter_by(
                    id=id).one()
                self._delete_nat(context, floating)
        except sa.orm.exc.NoResultFound:
            raise exc.PortNotFound(port_id=port_id)

        ret = super(NECNWAL3Plugin, self).update_floatingip(
            context, id, floatingip)

        try:
            if port_id_specified and port_id:
                floating = context.session.query(l3_db.FloatingIP).filter_by(
                    id=id).one()
                tenant_id = nwa_l3_db.get_tenant_id_by_router(
                    context.session,
                    floating['router_id']
                )
                nwa_tenant_id = nwa_com_utils.get_nwa_tenant_id(tenant_id)

                fl_data = {
                    'floating_ip_address': floating['floating_ip_address'],
                    'fixed_ip_address': floating['fixed_ip_address'],
                    'id': id, 'device_id': floating['router_id'],
                    'floating_network_id': floating['floating_network_id'],
                    'tenant_id': floating['tenant_id'],
                    'floating_port_id': floating['floating_port_id']
                }
                LOG.info(_LI('setting_nat fl_data is %s'), fl_data)
                proxy = self._core_plugin.get_nwa_proxy(tenant_id)
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

    def _add_router_interface_by_port(plugin, context, router_id,
                                      interface_info):
        try:
            if hasattr(context, 'session'):
                session = context.session
            else:
                session = context.network._plugin_context.session

            port = plugin._core_plugin._get_port(context,
                                                 interface_info['port_id'])
            network = plugin._core_plugin.get_network(context,
                                                      port['network_id'])

            binding = nwa_db.ensure_port_binding(session, port['id'])
            port_context = driver_context.PortContext(plugin._core_plugin,
                                                      context, port,
                                                      network, binding, None)

            nwa_info = nwa_l2_utils.portcontext_to_nwa_info(port_context)

            rt_tid = nwa_l3_db.get_tenant_id_by_router(
                session, router_id
            )
            nwa_rt_tid = nwa_com_utils.get_nwa_tenant_id(rt_tid)
            nwa_info['tenant_id'] = rt_tid
            nwa_info['nwa_tenant_id'] = nwa_rt_tid
            proxy = plugin._core_plugin.get_nwa_proxy(rt_tid)
            proxy.create_tenant_fw(
                port_context.network._plugin_context,
                rt_tid,
                nwa_rt_tid,
                nwa_info
            )

        except Exception as e:
            LOG.exception(_LE("create tenant firewall %s"), str(e))
