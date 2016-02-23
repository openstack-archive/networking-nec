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
from neutron_lib import constants
from oslo_config import cfg
from oslo_log import log as logging
from sqlalchemy.orm import exc as sa_exc

from networking_nec.nwa.common import utils as nwa_com_utils

LOG = logging.getLogger(__name__)


def get_network_info(context):
    name = context.network.current['name']
    network_id = context.network.current['id']
    return name, network_id


def get_physical_network(device_owner, resource_groups,
                         resource_group_name=None):
    for physnet in resource_groups:
        physnets = [physnet['physical_network'] for physnet in resource_groups
                    if (physnet['device_owner'] == device_owner and
                        (not resource_group_name or
                         physnet['ResourceGroupName'] == resource_group_name))]
        if physnets:
            return physnets[0]
    return None


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


def portcontext_to_nwa_info(context, resource_groups,
                            use_original_port=False):
    tenant_id, nwa_tenant_id = nwa_com_utils.get_tenant_info(context)
    network_name, network_id = get_network_info(context)

    port = context.original if use_original_port else context.current
    device_owner = port['device_owner']
    vlan_type = 'PublicVLAN' if is_external_network(context, network_id) \
                else 'BusinessVLAN'

    dbcontext = context._plugin_context

    nwa_info = {
        'tenant_id': tenant_id,
        'nwa_tenant_id': nwa_tenant_id,
        'network': {'id': network_id,
                    'name': network_name,
                    'vlan_type': vlan_type},
        'device': {'owner': device_owner,
                   'id': port['device_id']},
    }

    if port['fixed_ips']:
        subnet_id = port['fixed_ips'][0]['subnet_id']
        subnet = context._plugin.get_subnet(dbcontext, subnet_id)
        nwa_info['subnet'] = {'id': subnet_id,
                              'netaddr': subnet['cidr'].split('/')[0],
                              'mask': subnet['cidr'].split('/')[1]}
        nwa_info['port'] = {'id': port['id'],
                            'ip': port['fixed_ips'][0]['ip_address'],
                            'mac': port['mac_address']}
    else:
        nwa_info['subnet'] = {'id': '',
                              'netaddr': '',
                              'mask': ''}
        nwa_info['port'] = {'id': port['id'],
                            'ip': '',
                            'mac': port['mac_address']}

    resource_group_name = _get_resource_group_name(context, resource_groups,
                                                   use_original_port)
    nwa_info['resource_group_name'] = resource_group_name
    nwa_info['resource_group_name_nw'] = cfg.CONF.NWA.resource_group_name
    nwa_info['physical_network'] = get_physical_network(device_owner,
                                                        resource_groups,
                                                        resource_group_name)

    return nwa_info


# Private methods

def _get_resource_group_name(context, resource_groups,
                             use_original_port=False):
    port = context.original if use_original_port else context.current
    device_owner = port['device_owner']
    for agent in context.host_agents(constants.AGENT_TYPE_OVS):
        if agent['alive']:
            mappings = agent['configurations'].get('bridge_mappings', {})
            for res_grp in resource_groups:
                if not res_grp['ResourceGroupName'] in mappings:
                    continue
                if res_grp['device_owner'] == device_owner:
                    return res_grp['ResourceGroupName']

    if (device_owner == constants.DEVICE_OWNER_ROUTER_INTF or
            device_owner == constants.DEVICE_OWNER_ROUTER_GW):
        for res_grp in resource_groups:
            if res_grp['device_owner'] == device_owner:
                return res_grp['ResourceGroupName']

    return None
