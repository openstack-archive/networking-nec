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

from neutron.plugins.ml2 import driver_context
from oslo_log import log as logging

from networking_nec._i18n import _LE
from networking_nec.plugins.necnwa.common import utils as nwa_com_utils
from networking_nec.plugins.necnwa.l2 import db_api as nwa_db
from networking_nec.plugins.necnwa.l2 import utils as nwa_l2_utils
from networking_nec.plugins.necnwa.l3 import db_api as nwa_l3_db

LOG = logging.getLogger(__name__)


# TODO(amotoki): Move L2 part which retrieves nwa_info to
# l2.utils.get_port_nwa_info()
def add_router_interface_by_port(plugin, context, router_id, interface_info):
    if 'port_id' in interface_info:
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

            mech_drivers = plugin._core_plugin.mechanism_manager.mech_drivers
            mech_driver = mech_drivers['necnwa']
            nwa_info = nwa_l2_utils.portcontext_to_nwa_info(
                port_context, mech_driver.obj.resource_groups)

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
