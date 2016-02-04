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

from sqlalchemy.orm import exc
import traceback

from neutron.common import constants
from neutron.common import exceptions as n_exc
from neutron.db import external_net_db
from neutron.db import models_v2
from neutron.plugins.ml2 import db
from neutron.plugins.ml2 import driver_context
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec._i18n import _LE
from networking_nec.plugins.necnwa.common import config
import networking_nec.plugins.necnwa.constants as nwa_const
from networking_nec.plugins.necnwa.db import api as nwa_db

LOG = logging.getLogger(__name__)


def get_nwa_tenant_id(tenant_id):
    return config.CONF.NWA.region_name + tenant_id


def get_tenant_info(context):
    tenant_id = context.network.current['tenant_id']
    nwa_tenant_id = get_nwa_tenant_id(tenant_id)
    return tenant_id, nwa_tenant_id


def get_network_info(context):
    name = context.network.current['name']
    network_id = context.network.current['id']
    return name, network_id


def get_physical_network(device_owner, resource_group_name=None):
    grp = jsonutils.loads(config.CONF.NWA.resource_group)
    for physnet in grp:
        physnets = [physnet['physical_network'] for physnet in grp
                    if (physnet['device_owner'] == device_owner and
                        (not resource_group_name or
                         physnet['ResourceGroupName'] == resource_group_name))]
        if physnets:
            return physnets[0]
    return None


def update_port_status(context, port_id, status):
    if hasattr(context, 'session'):
        session = context.session
    else:
        session = context.network._plugin_context.session
    try:
        port = session.query(models_v2.Port).filter_by(id=port_id).one()
        LOG.debug("[DB] PORT STATE CHANGE %s -> %s" % (port['status'], status))
        LOG.debug("[DB] PORT ID %s", port_id)
        port['status'] = status
        session.merge(port)
        session.flush()
    except exc.NoResultFound:
        LOG.debug("[DB] PORT not found %s", port_id)
        raise n_exc.PortNotFound(port_id=port_id)


def is_baremetal(device_owner):
    bm_prefix = config.CONF.NWA.ironic_az_prefix.strip()
    if bm_prefix == '':
        return False
    return device_owner.startswith('compute:' + bm_prefix)


def baremetal_resource_group_name(mac_address):
    try:
        for pmap in jsonutils.loads(config.CONF.NWA.port_map):
            if pmap['mac_address'] == mac_address:
                return pmap['ResourceGroupName']
    except Exception:
        LOG.error(_LE('No mac address %s in port_map of plugin.ini'),
                  mac_address)


def _get_resource_group_name(context, use_original_port=False):
    port = context.original if use_original_port else context.current
    device_owner = port['device_owner']
    grp = jsonutils.loads(config.CONF.NWA.resource_group)
    for agent in context.host_agents(constants.AGENT_TYPE_OVS):
        if agent['alive']:
            mappings = agent['configurations'].get('bridge_mappings', {})
            for res_grp in grp:
                if not res_grp['ResourceGroupName'] in mappings:
                    continue
                if res_grp['device_owner'] == device_owner:
                    return res_grp['ResourceGroupName']

    if (device_owner == constants.DEVICE_OWNER_ROUTER_INTF or
            device_owner == constants.DEVICE_OWNER_ROUTER_GW):
        for res_grp in grp:
            if res_grp['device_owner'] == device_owner:
                return res_grp['ResourceGroupName']

    return None


def _release_dynamic_segment(context, session, network_id, physical_network,
                             segmentation_id):
    try:
        del_segment = db.get_dynamic_segment(
            session, network_id, physical_network=physical_network,
            segmentation_id=segmentation_id)

        if del_segment and 'id' in del_segment:
            LOG.debug("release_dynamic_segment segment_id=%s" %
                      del_segment['id'])
            db.delete_network_segment(session, del_segment['id'])
            return True
        else:
            LOG.debug("not found segment_id in del_segment")

        return False
    except Exception as e:
        LOG.exception(str(e))
        return False


def _set_segment_to_tenant_binding(context, jbody):
    try:
        name = traceback.extract_stack()[-1][2]
        LOG.debug("%(name)s", {'name': name})

        tenant_id, nwa_tenant_id = get_tenant_info(context)
        recode = nwa_db.get_nwa_tenant_binding(
            context.network._plugin_context.session, tenant_id, nwa_tenant_id)
        nwa_data = recode.value_json

        network_name, network_id = get_network_info(context)

        device_owner = context._port['device_owner']

        resultdata = jbody.get('resultdata')
        vlan_id = resultdata.get('VlanID')

        physical_network = get_physical_network(device_owner)
        if resultdata.get('ResourceGroupName'):
            physical_network = resultdata['ResourceGroupName']

        seg_key = 'VLAN_%s_%s' % (network_id, physical_network)
        if seg_key not in nwa_data.keys():
            nwa_data[seg_key] = 'physical_network'
            nwa_data[seg_key + '_segmentation_id'] = vlan_id
            nwa_data[seg_key + '_VlanID'] = vlan_id

        nwa_data[seg_key + '_GD'] = 'connected'

        LOG.debug("[DB] set_nwa_tenant_binding=%s",
                  jsonutils.dumps(nwa_data, indent=4, sort_keys=True))

        done = nwa_db.set_nwa_tenant_binding(
            context.network._plugin_context.session, tenant_id,
            nwa_tenant_id, nwa_data
        )
        if done:
            return

    except Exception as e:
        LOG.exception(_LE('%s'), str(e))
    LOG.error(_LE('fail to add the network segment to nwa db.'))


def _set_general_dev_to_tenant_binding(context):
    try:
        name = traceback.extract_stack()[-1][2]
        tenant_id, nwa_tenant_id = get_tenant_info(context)
        LOG.debug("[COM] %(name)s  tenant_id=%(tenant_id)s).",
                  {'name': name, 'tenant_id': tenant_id})

        network_name, network_id = get_network_info(context)
        device_id = context._port['device_id']

        recode = nwa_db.get_nwa_tenant_binding(
            context.network._plugin_context.session, tenant_id, nwa_tenant_id)
        nwa_data = recode.value_json

        dev_key = 'DEV_' + device_id
        nwa_data[dev_key] = 'device_id'
        nwa_data[dev_key + '_device_owner'] = context._port['device_owner']

        dev_net_key = dev_key + '_' + network_id
        nwa_data[dev_net_key] = network_name
        nwa_data[dev_net_key + '_TYPE'] = nwa_const.NWA_DEVICE_GDV
        nwa_data[dev_net_key +
                 '_ip_address'] = context._port['fixed_ips'][0]['ip_address']
        nwa_data[dev_net_key +
                 '_mac_address'] = context._port['mac_address']

        # update segment_id
        LOG.debug("[DB] set_nwa_tenant_binding=%s" %
                  jsonutils.dumps(nwa_data, indent=4, sort_keys=True))

        done = nwa_db.set_nwa_tenant_binding(
            context.network._plugin_context.session, tenant_id,
            nwa_tenant_id, nwa_data)
        if done:
            return

    except Exception as e:
        LOG.exception(_LE('%s'), str(e))
    LOG.error(_LE('fail to set nwa general device to nwa db.'))


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

            nwa_info = portcontext_to_nwa_info(port_context)

            rt_tid = get_tenant_id_by_router(
                session, router_id
            )
            nwa_rt_tid = get_nwa_tenant_id(rt_tid)
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


def get_tenant_id_by_router(session, router_id):
    from neutron.db import l3_db
    rt_tid = None
    with session.begin(subtransactions=True):
        try:
            router = session.query(l3_db.Router).filter_by(id=router_id).one()
            rt_tid = router.tenant_id
        except exc.NoResultFound:
            LOG.debug("router not found %s", router_id)

    LOG.debug("rt_tid=%s", rt_tid)
    return rt_tid


def is_external_network(context, net_id):
    if hasattr(context, 'session'):
        session = context.session
    else:
        session = context.network._plugin_context.session
    try:
        session.query(
            external_net_db.ExternalNetwork).filter_by(
                network_id=net_id
        ).one()
        return True

    except exc.NoResultFound:
        return False


def portcontext_to_nwa_info(context, use_original_port=False):
    tenant_id, nwa_tenant_id = get_tenant_info(context)
    network_name, network_id = get_network_info(context)

    port = context.original if use_original_port else context.current
    device_owner = port['device_owner']
    device_id = port['device_id']
    vlan_type = 'PublicVLAN' if is_external_network(context, network_id) \
                else 'BusinessVLAN'

    port_id = port['id']

    dbcontext = context._plugin_context

    if port['fixed_ips']:
        ipaddr = port['fixed_ips'][0]['ip_address']
        subnet_id = port['fixed_ips'][0]['subnet_id']
        subnet = context._plugin.get_subnet(dbcontext, subnet_id)
        netaddr = subnet['cidr'].split('/')[0]
        mask = subnet['cidr'].split('/')[1]
    else:
        ipaddr = ''
        subnet = ''
        subnet_id = ''
        netaddr = ''
        mask = ''

    macaddr = port['mac_address']

    resource_group_name_nw = config.CONF.NWA.resource_group_name
    resource_group_name = _get_resource_group_name(context, use_original_port)
    physical_network = get_physical_network(device_owner, resource_group_name)

    return {
        'tenant_id': tenant_id,
        'nwa_tenant_id': nwa_tenant_id,
        'network': {'id': network_id,
                    'name': network_name,
                    'vlan_type': vlan_type},
        'subnet': {'id': subnet_id,
                   'netaddr': netaddr,
                   'mask': mask},
        'device': {'owner': device_owner,
                   'id': device_id},
        'port': {'id': port_id,
                 'ip': ipaddr,
                 'mac': macaddr},
        'resource_group_name': resource_group_name,
        'resource_group_name_nw': resource_group_name_nw,
        'physical_network': physical_network
    }
