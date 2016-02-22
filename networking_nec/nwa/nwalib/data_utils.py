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

from networking_nec.nwa.common import constants as nwa_const

VLAN_OWN_GDV = 'GD'
VLAN_OWN_TFW = 'TFW'

NWA_DEVICE_MAP = {
    nwa_const.NWA_DEVICE_GDV: VLAN_OWN_GDV,
    nwa_const.NWA_DEVICE_TFW: VLAN_OWN_TFW,
}


def get_network_key(network_id):
    return 'NW_' + network_id


def get_vlan_key(network_id):
    return 'VLAN_' + network_id


def get_device_key(device_id):
    return 'DEV_' + device_id


def get_tfw_device_name(nwa_data, device_id):
    return nwa_data['DEV_' + device_id + '_TenantFWName']


def get_device_net_key(device_id, network_id):
    return 'DEV_%s_%s' % (device_id, network_id)


def get_vlan_logical_name(nwa_data, network_id):
    return nwa_data['NW_' + network_id + '_nwa_network_name']


def get_vlan_id(network_id, nwa_data, resultdata):
    vlan_key = 'VLAN_' + network_id
    if nwa_data[vlan_key + '_CreateVlan'] == '':
        return resultdata['VlanID']
    else:
        return nwa_data[vlan_key + '_VlanID']


def get_vp_net_vlan_id(nwa_data, network_id, resource_group_name_nw,
                       device_type):
    seg_key = 'VLAN_%s_%s_%s' % (network_id, resource_group_name_nw,
                                 NWA_DEVICE_MAP[device_type])
    return int(nwa_data[seg_key + '_VlanID'], 10)


def set_network_data(nwa_data, network_id, nwa_info, logical_name):
    nw_net = 'NW_' + network_id
    nwa_data[nw_net] = nwa_info['network']['name']
    nwa_data[nw_net + '_network_id'] = network_id
    nwa_data[nw_net + '_subnet_id'] = nwa_info['subnet']['id']
    nwa_data[nw_net + '_subnet'] = nwa_info['subnet']['netaddr']
    nwa_data[nw_net + '_nwa_network_name'] = logical_name


def strip_network_data(nwa_data, network_id):
    nw_net = 'NW_' + network_id
    nwa_data.pop(nw_net)
    nwa_data.pop(nw_net + '_network_id')
    nwa_data.pop(nw_net + '_subnet_id')
    nwa_data.pop(nw_net + '_subnet')
    nwa_data.pop(nw_net + '_nwa_network_name')


def set_vlan_data(nwa_data, network_id, vlan_id):
    vp_net = 'VLAN_' + network_id
    nwa_data[vp_net] = 'physical_network'
    nwa_data[vp_net + '_VlanID'] = vlan_id
    nwa_data[vp_net + '_CreateVlan'] = ''


def strip_vlan_data(nwa_data, network_id):
    vp_net = 'VLAN_' + network_id
    nwa_data.pop(vp_net)
    nwa_data.pop(vp_net + '_VlanID')
    nwa_data.pop(vp_net + '_CreateVlan')


def set_gdv_device_data(nwa_data, device_id, nwa_info):
    dev_key = 'DEV_%s' % device_id
    nwa_data[dev_key] = 'device_id'
    nwa_data[dev_key + '_device_owner'] = nwa_info['device']['owner']


def set_tfw_device_data(nwa_data, device_id, tfw_name, nwa_info):
    dev_key = 'DEV_%s' % device_id
    nwa_data[dev_key] = 'device_id'
    nwa_data[dev_key + '_device_owner'] = nwa_info['device']['owner']
    nwa_data[dev_key + '_TenantFWName'] = tfw_name


def strip_device_data(nwa_data, device_id):
    dev_key = 'DEV_%s' % device_id
    nwa_data.pop(dev_key)
    nwa_data.pop(dev_key + '_device_owner')
    nwa_data.pop(dev_key + '_TenantFWName', None)


def set_gdv_interface_data(nwa_data, device_id, network_id,
                           resource_group_name_nw, nwa_info):
    net_key = 'DEV_%s_%s' % (device_id, network_id)
    nwa_data[net_key] = nwa_info['network']['name']
    nwa_data[net_key + '_ip_address'] = nwa_info['port']['ip']
    nwa_data[net_key + '_mac_address'] = nwa_info['port']['mac']
    nwa_data[net_key + '_' + resource_group_name_nw] = nwa_const.NWA_DEVICE_GDV


def set_tfw_interface_data(nwa_data, device_id, network_id,
                           resource_group_name_nw, tfw_name, nwa_info):
    net_key = 'DEV_%s_%s' % (device_id, network_id)
    nwa_data[net_key] = nwa_info['network']['name']
    nwa_data[net_key + '_ip_address'] = nwa_info['port']['ip']
    nwa_data[net_key + '_mac_address'] = nwa_info['port']['mac']
    nwa_data[net_key + '_TenantFWName'] = tfw_name
    nwa_data[net_key + '_' + resource_group_name_nw] = nwa_const.NWA_DEVICE_TFW


def strip_interface_data(nwa_data, device_id, network_id,
                         resource_group_name_nw):
    net_key = 'DEV_%s_%s' % (device_id, network_id)
    nwa_data.pop(net_key)
    nwa_data.pop(net_key + '_ip_address')
    nwa_data.pop(net_key + '_mac_address')
    nwa_data.pop(net_key + '_TenantFWName', None)
    nwa_data.pop(net_key + '_' + resource_group_name_nw)


def set_vp_net_data(nwa_data, network_id, resource_group_name_nw, device_type,
                    vlan_id):
    seg_key = ('VLAN_%(network_id)s_%(group)s_%(dev_type)s' %
               {'network_id': network_id,
                'group': resource_group_name_nw,
                'dev_type': NWA_DEVICE_MAP[device_type]})
    nwa_data[seg_key] = 'physical_network'
    nwa_data[seg_key + '_VlanID'] = vlan_id


def strip_vp_net_data(nwa_data, network_id, resource_group_name_nw,
                      device_type):
    seg_key = ('VLAN_%(network_id)s_%(group)s_%(dev_type)s' %
               {'network_id': network_id,
                'group': resource_group_name_nw,
                'dev_type': NWA_DEVICE_MAP[device_type]})
    nwa_data.pop(seg_key)
    nwa_data.pop(seg_key + '_VlanID')


def strip_tfw_data_if_exist(nwa_data, device_id, network_id,
                            resource_group_name_nw):
    tfw_key = 'VLAN_%s_%s_TFW_FW_TFW%s' % (network_id,
                                           resource_group_name_nw,
                                           device_id)
    if tfw_key in nwa_data:
        nwa_data.pop(tfw_key)


def set_floatingip_data(nwa_data, floating):
    fip_key = 'NAT_' + floating['id']
    nwa_data[fip_key] = floating['device_id']
    nwa_data[fip_key + '_network_id'] = floating['floating_network_id']
    nwa_data[fip_key + '_floating_ip_address'] = \
        floating['floating_ip_address']
    nwa_data[fip_key + '_fixed_ip_address'] = floating['fixed_ip_address']


def strip_floatingip_data(nwa_data, floating):
    fip_key = 'NAT_' + floating['id']
    nwa_data.pop(fip_key)
    nwa_data.pop(fip_key + '_network_id')
    nwa_data.pop(fip_key + '_floating_ip_address')
    nwa_data.pop(fip_key + '_fixed_ip_address')
