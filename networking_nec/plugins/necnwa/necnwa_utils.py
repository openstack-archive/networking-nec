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

from neutron.common import constants

from oslo_log import log

from neutron.db import models_v2
from neutron.db import external_net_db

from neutron.plugins.ml2 import db
from neutron.plugins.ml2 import driver_context

from networking_nec.plugins.necnwa.common import config
from networking_nec.plugins.necnwa.db import api as nwa_db

import traceback
import json

from sqlalchemy.orm import exc
from neutron.common import exceptions as n_exc


LOG = log.getLogger(__name__)

"""
const
"""

NWA_DEVICE_GDV = "GeneralDev"
NWA_DEVICE_TFW = "TenantFW"

"""
Utils
"""


class NWAClientError(n_exc.NeutronException):
    message = _('NWAClient Error %(msg)s')


class NWAUtilsError(n_exc.NeutronException):
    message = _('NWAUtils Error %(msg)s')


class ResourceGroupNameNotFound(n_exc.NotFound):
    message = _("ResourceGroupName %(device_owner)s could not be found")

def get_nwa_tenant_id(tid):
    return config.CONF.NWA.RegionName + tid


def get_tenant_info(context):
    tid = context.network.current['tenant_id']
    nid = config.CONF.NWA.RegionName + tid
    return tid, nid


def get_network_info(context):
    net = context.network.current['name']
    nid = context.network.current['id']
    return net, nid


def get_physical_network(device_owner, resource_group_name=None):
    grp = json.loads(config.CONF.NWA.ResourceGroup)
    for physnet in grp:
        if resource_group_name is not None and \
                physnet['ResourceGroupName'] != resource_group_name:
            continue
        if physnet['device_owner'] == device_owner:
            return physnet['physical_network']
    return None


def update_port_status(context, port_id, status):
    if getattr(context, 'session', None):
        session = context.session
    else:
        session = context.network._plugin_context.session
    try:
        port = session.query(models_v2.Port).filter_by(id=port_id).one()
        LOG.debug("[DB] PORT STATE CHANGE %s -> %s" % (port['status'], status))
        LOG.debug("[DB] PORT ID %s" % (port_id))
        port['status'] = status
        session.merge(port)
        session.flush()
    except exc.NoResultFound:
        LOG.debug("[DB] PORT not found %s" % (port_id))
        raise n_exc.PortNotFound(port_id=port_id)


def is_baremetal(device_owner):
    bm_prefix = config.CONF.NWA.IronicAZPrefix.strip()
    if bm_prefix == '':
        return False
    return device_owner.startswith('compute:' + bm_prefix)


def baremetal_resource_group_name(mac_address):
    try:
        for pmap in json.loads(config.CONF.NWA.PortMap):
            if pmap['mac_address'] == mac_address:
                return pmap['ResourceGroupName']
    except Exception as e:
        LOG.debug(str(e))
        pass
    raise KeyError('No mac address {} in PortMap of plugin.ini'.
                   format(mac_address))


def _get_resource_group_name(context, use_original_port=False):
    port = context.original if use_original_port else context.current
    device_owner = port['device_owner']
    grp = json.loads(config.CONF.NWA.ResourceGroup)

    for agent in context.host_agents(constants.AGENT_TYPE_OVS):
        if agent['alive']:
            mappings = agent['configurations'].get('bridge_mappings', {})
            for res_grp in grp:
                if not res_grp['ResourceGroupName'] in mappings:
                    continue
                if res_grp['device_owner'] == device_owner:
                    return res_grp['ResourceGroupName']

    if ((device_owner == constants.DEVICE_OWNER_ROUTER_INTF or
         device_owner == constants.DEVICE_OWNER_ROUTER_GW)):
        for res_grp in grp:
            if res_grp['device_owner'] == device_owner:
                return res_grp['ResourceGroupName']

    return None


def _release_dynamic_segment(context, session, network_id, physical_network, segmentation_id):
    try:
        del_segment = db.get_dynamic_segment(
            session, network_id, physical_network=physical_network,
            segmentation_id=segmentation_id)

        if del_segment and 'id' in del_segment:
            LOG.debug("release_dynamic_segment segment_id=%s" % del_segment['id'])
            db.delete_network_segment(session, del_segment['id'])
            return True
        else:
            LOG.debug("not found segment_id in del_segment")

        return False
    except Exception as e:
        LOG.error(str(e))
        lines = traceback.format_exc().splitlines()
        for l in lines:
            LOG.error(l)
        return False


def _set_segment_to_tenant_binding(context, jbody):
    try:
        name = traceback.extract_stack()[-1][2]
        LOG.debug(_("%(name)s"), {'name': name})

        tenant_id, nwa_tenant_id = get_tenant_info(context)
        recode = nwa_db.get_nwa_tenant_binding(
            context.network._plugin_context.session, tenant_id, nwa_tenant_id)
        nwa_data = recode.value_json

        network_name, network_id = get_network_info(context)

        device_owner = context._port['device_owner']
        physical_network = get_physical_network(device_owner)
        if jbody['resultdata'].get('ResourceGroupName', None):
            physical_network = jbody['resultdata']['ResourceGroupName']

        seg_key = 'VLAN_' + network_id + '_' + physical_network
        if not seg_key in nwa_data.keys():
            nwa_data['VLAN_' + network_id + '_' + physical_network] = 'physical_network'
            nwa_data['VLAN_' + network_id + '_' + physical_network + '_segmentation_id'] = jbody['resultdata']['VlanID']
            nwa_data['VLAN_' + network_id + '_' + physical_network + '_VlanID'] = jbody['resultdata']['VlanID']

        gd_key = seg_key + '_GD'
        nwa_data[gd_key] = 'connected'

        LOG.debug("[DB] set_nwa_tenant_binding=%s" % json.dumps(nwa_data, indent=4, sort_keys=True))

        ret = nwa_db.set_nwa_tenant_binding(
            context.network._plugin_context.session, tenant_id,
            nwa_tenant_id, nwa_data)

        if not ret is True:
            return

    except Exception as e:
        LOG.error(str(e))
        lines = traceback.format_exc().splitlines()
        for l in lines:
            LOG.error(l)
        return


def _set_general_dev_to_tenant_binding(context):
    try:
        name = traceback.extract_stack()[-1][2]
        tenant_id, nwa_tenant_id = get_tenant_info(context)
        LOG.debug(_("[COM] %(name)s  tenant_id=%(tenant_id)s)."),
                  {'name': name, 'tenant_id': tenant_id})

        network_name, network_id = get_network_info(context)
        device_id = context._port['device_id']

        recode = nwa_db.get_nwa_tenant_binding(
            context.network._plugin_context.session, tenant_id, nwa_tenant_id)
        nwa_data = recode.value_json

        nwa_data['DEV_' + device_id] = 'device_id'
        nwa_data['DEV_' + device_id + '_device_owner'] = context._port['device_owner']
        nwa_data['DEV_' + device_id + '_' + network_id] = network_name
        nwa_data['DEV_' + device_id + '_' + network_id + '_TYPE'] = NWA_DEVICE_GDV
        nwa_data['DEV_' + device_id + '_' + network_id + '_ip_address'] = context._port['fixed_ips'][0]['ip_address']
        nwa_data['DEV_' + device_id + '_' + network_id + '_mac_address'] = context._port['mac_address']

        # update segment_id
        LOG.debug("[DB] set_nwa_tenant_binding=%s" % json.dumps(nwa_data, indent=4, sort_keys=True))

        ret = nwa_db.set_nwa_tenant_binding(
            context.network._plugin_context.session, tenant_id,
            nwa_tenant_id, nwa_data)

        if not ret is True:
            return

    except Exception as e:
        LOG.error(str(e))
        lines = traceback.format_exc().splitlines()
        for l in lines:
            LOG.error(l)
        return


def add_router_interface_by_port(plugin, context, router_id, interface_info):
    if 'port_id' in interface_info:
        try:
            if getattr(context, 'session', None):
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

        except:
            return False

    return True


def get_tenant_id_by_router(session, router_id):
    from neutron.db import l3_db
    rt_tid = None
    with session.begin(subtransactions=True):
        try:
            router = session.query(l3_db.Router).filter_by(id=router_id).one()
            rt_tid = router.tenant_id
        except exc.NoResultFound:
            LOG.debug("router not found %s" % (router_id))

    LOG.debug("rt_tid=%s" % rt_tid)
    return rt_tid


def is_external_network(context, net_id):
    if getattr(context, 'session', None):
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
    vlan_type = 'PublicVLAN' if is_external_network(context, network_id) else 'BusinessVLAN'

    port_id = port['id']

    dbcontext = context._plugin_context

    if (0 < len(port['fixed_ips'])):
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

    resource_group_name_nw = config.CONF.NWA.ResourceGroupName
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
