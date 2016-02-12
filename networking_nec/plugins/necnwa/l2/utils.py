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

from neutron.db import external_net_db
from neutron.db import models_v2
from neutron_lib import constants
from neutron_lib import exceptions as n_exc
from oslo_log import log as logging
from oslo_serialization import jsonutils
from sqlalchemy.orm import exc as sa_exc

from networking_nec.plugins.necnwa.common import config
from networking_nec.plugins.necnwa.common import utils as nwa_com_utils

LOG = logging.getLogger(__name__)


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


# TODO(amotoki): Move update_port_status() to core.plugin or core.db_api
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
    except sa_exc.NoResultFound:
        LOG.debug("[DB] PORT not found %s", port_id)
        raise n_exc.PortNotFound(port_id=port_id)


# TODO(amotoki): Move is_external_network() to core.db_api
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

    except sa_exc.NoResultFound:
        return False


def portcontext_to_nwa_info(context, use_original_port=False):
    tenant_id, nwa_tenant_id = nwa_com_utils.get_tenant_info(context)
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


# Private methods

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
