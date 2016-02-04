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

from copy import deepcopy
from mock import MagicMock
from mock import patch

import neutron
NEUTRON_CONF = (neutron.__path__[0] +
                '/../etc/neutron.conf')
from neutron.common import config
from neutron.common import rpc
from neutron.tests import base
from oslo_config import cfg
from oslo_log import log as logging

import networking_nec
NECNWA_INI = (networking_nec.__path__[0] +
              '/../etc/neutron/plugins/nec/necnwa.ini')
import networking_nec.plugins.necnwa.agent.necnwa_neutron_agent as \
    necnwa_neutron_agent
from networking_nec.plugins.necnwa.agent.necnwa_neutron_agent \
    import check_segment
from networking_nec.plugins.necnwa.agent.necnwa_neutron_agent \
    import main as agent_main
from networking_nec.plugins.necnwa.agent.necnwa_neutron_agent \
    import NECNWAAgentRpcCallback
from networking_nec.plugins.necnwa.agent.necnwa_neutron_agent \
    import NECNWANeutronAgent
from networking_nec.plugins.necnwa.agent.necnwa_neutron_agent \
    import NECNWAProxyCallback
from networking_nec.plugins.necnwa.necnwa_core_plugin import (
    NECNWATenantBindingServerRpcApi
)

LOG = logging.getLogger(__name__)

necnwa_neutron_agent.WAIT_AGENT_NOTIFIER = 0

"""""
test params
"""""
# #############################
# NWA Server dummy responce
# CreateTenantNW succeed
result_tnw = {
    "progress": 100,
    "resultdata": {
        "AutoRecovery": "0",
        "BackEndFWInfo": "FortiGate",
        "DCResourceReserveID": "1",
        "DCResourceReserveID_Delete": "",
        "ErrorMessage": "",
        "InJsonFileName": "",
        "ManagementLogicalNWName": "LNW_ManagementVLAN_88",
        "ManagementVlanFwIpAddress": "100.64.0.254",
        "ManagementVlanID": "1",
        "ManagementVlanIPSubnet": "100.64.0.0",
        "ManagementVlanSubnetMask": "255.255.255.0",
        "OutJsonFileName": "",
        "ResourceGroupName": "OpenStack/DC1/APP",
        "TenantFWAccessInfo": "",
        "TenantFWInfo": "",
        "TenantFWName": "",
        "TenantID": "DC1_844eb55f21e84a289e9c22098d387e5d",
        "TenantLogicalNWName": "LNW_TenantVLAN_89",
        "TenantVlanFwIpAddress": "",
        "TenantVlanID": "",
        "TenantVlanIPSubnet": "100.64.1.0",
        "TenantVlanSubnetMask": "255.255.255.0"
    },
    "status": "SUCCESS"
}

# CreateVlan succeed
result_vln = {
    "progress": 100,
    "resultdata": {
        "AutoRecovery": "0",
        "BackEndFWInfo": "",
        "DCResourceReserveID": "1",
        "DCResourceReserveID_Delete": "",
        "ErrorMessage": "",
        "InJsonFileName": "",
        "LogicalNWName": "LNW_BusinessVLAN_100",
        "OutJsonFileName": "",
        "ResourceGroupName": "",
        "RouterInfo": "",
        "TenantFWAccessInfo": "",
        "TenantFWInfo": "",
        "TenantID": "DC1_844eb55f21e84a289e9c22098d387e5d",
        "VlanFwIpAddress": "",
        "VlanID": "",
        "VlanIPSubnet": "192.168.100.0",
        "VlanSubnetMask": "255.255.255.0"
    },
    "status": "SUCCESS"
}

# CreateGeneralDev succeed
result_cgd = {
    "progress": 100,
    "resultdata": {
        "CreateNW_PortType1": "",
        "DCResourceReserveID": "1",
        "ErrorMessage": "",
        "NWAResult": "No result log\r\n",
        "ResourceGroupName": "OpenStack/DC1/APP",
        "TenantID": "DC1_844eb55f21e84a289e9c22098d387e5d",
        "VlanID": "200",
        "VlanLoopCounter": "1"
    },
    "status": "SUCCESS"
}


# DeleteVlan succeed
result_dvl = {
    "progress": 100,
    "resultdata": {
        "DCResourceReserveID": "1",
        "ErrorMessage": "",
        "NWAResult": "No result log\r\n",
        "TenantID": "DC1_844eb55f21e84a289e9c22098d387e5d",
        "UNC_LoopCounter": "1",
        "VlanLoopCounter": "0"
    },
    "status": "SUCCESS"
}

# DeleteTenantNW succeed
result_dnw = {
    "progress": 100,
    "resultdata": {
        "DCResourceReserveID": "1",
        "DevType": "",
        "ErrorMessage": "",
        "GUID": "",
        "LogicalNWName_Del": "LNW_TenantVLAN_89",
        "ManagerName": "",
        "Mode": "",
        "NWAResult": "No result log\r\n",
        "NumOfTenantNWDev": "",
        "ResourceGroupName": "Common/App/Pod3",
        "SSLAuthFlag": "",
        "Section": "",
        "TFWAuthFlag": "",
        "TFWCount": "",
        "TenantID": "DC1_844eb55f21e84a289e9c22098d387e5d",
        "UNC_LoopCounter": "1",
        "VlanID_Del": "5",
        "VlanLoopCounter": "0",
        "VlanType": ""
    },
    "status": "SUCCESS"
}

# DeleteGeneralDev succeed
result_dgd = {
    "progress": 100,
    "resultdata": {
        "DCResourceReserveID": "1",
        "ErrorMessage": "",
        "NWAResult": "No result log\r\n",
        "ResourceGroupName": "OpenStack/DC1/APP",
        "TenantID": "DC1_844eb55f21e84a289e9c22098d387e5d",
        "UNC_LoopCounter": "1",
        "VlanLoopCounter": "0"
    },
    "status": "SUCCESS"
}

# DeleteGeneralDev failed
result_dgd_fail = {
    "progress": 100,
    "resultdata": {
        "DCResourceReserveID": "1",
        "ErrorMessage": "",
        "NWAResult": "No result log\r\n",
        "ResourceGroupName": "OpenStack/DC1/APP",
        "TenantID": "DC1_844eb55f21e84a289e9c22098d387e5d",
        "UNC_LoopCounter": "1",
        "VlanLoopCounter": "0"
    },
    "status": "FAILED"
}

##########################

"""
nwa_info
"""

# add_router_interface.
nwa_info_add_intf = {
    'network': {'id': '546a8551-5c2b-4050-a769-cc3c962fc5cf',
                'name': 'net100',
                'vlan_type': 'BusinessVLAN'},
    'subnet': {'id': '7dabadaa-06fc-45fb-af0b-33384cf291c4',
               'netaddr': '192.168.100.0',
               'mask': '24'},
    'device': {'owner': 'network:router_interface',
               'id': '6b34210c-bd74-47f0-8dc3-3bad9bc333c3'},
    'port': {'id': '5174b4d2-f4dc-4292-9d9e-7862f885abdf',
             'ip': '192.168.100.1',
             'mac': 'fa:16:3e:45:98:7d'},
    'resource_group': 'OpenStack/DC1/APP',
    'physical_network': 'OpenStack/DC1/APP',
    'resource_group_name': 'OpenStack/DC1',
    'resource_group_name_nw': 'OpenStack/DC1',
}

nwa_info_add_intf2 = {
    'network': {'id': 'b2246c56-d465-49c7-a332-f329aa524277',
                'name': 'net101',
                'vlan_type': 'BusinessVLAN'},
    'subnet': {'id': 'ec3d84a5-ce49-48ee-a041-a7b9c9867899',
               'netaddr': '192.168.101.0',
               'mask': '24'},
    'device': {'owner': 'network:router_interface',
               'id': '6b34210c-bd74-47f0-8dc3-3bad9bc333c3'},
    'port': {'id': '254c3a42-b3aa-4083-9b7b-2e4c62b2ffbb',
             'ip': '192.168.101.1',
             'mac': 'fa:16:3e:34:9a:c9'},
    'resource_group': 'OpenStack/DC1/APP',
    'physical_network': 'OpenStack/DC1/APP',
    'resource_group_name': 'OpenStack/DC1',
    'resource_group_name_nw': 'OpenStack/DC1',
}

nwa_info_delete_intf = nwa_info_add_intf

# create port with instance
nwa_info_create_gdv = {
    'subnet': {
        'netaddr': '192.168.200.0',
        'mask': '24',
        'id': '94fdaea5-33ae-4411-b6e0-71e4b099d470'
    },
    'network': {'vlan_type': 'BusinessVLAN',
                'id': 'a94fd0fc-2282-4092-9485-b0f438b0f6c4',
                'name': 'pj1-net100'},
    'resource_group': 'OpenStack/DC1/APP',
    'resource_group_name': 'OpenStack/DC1/APP',
    'resource_group_name_nw': 'OpenStack/DC1/APP',
    'tenant_id': '844eb55f21e84a289e9c22098d387e5d',
    'nwa_tenant_id': 'DC1_844eb55f21e84a289e9c22098d387e5d',
    'physical_network': 'OpenStack/DC1/APP',
    'device': {'owner': 'compute:DC1_KVM',
               'id': '36509c40-58e0-4293-8b16-48b409959b8f'},
    'port': {'ip': '192.168.200.132',
             'mac': 'fa:16:3e:a6:1d:00',
             'id': 'c61583dd-b52b-4bd7-b586-a6b33780090f'}
}

nwa_info_create_gdv2 = {
    'subnet': {
        'netaddr': '192.168.200.0',
        'mask': '24',
        'id': '94fdaea5-33ae-4411-b6e0-71e4b099d470'
    },
    'network': {'vlan_type': 'BusinessVLAN',
                'id': 'a94fd0fc-2282-4092-9485-b0f438b0f6c4',
                'name': 'pj1-net100'},
    'resource_group': 'OpenStack/DC1/APP',
    'resource_group_name': 'OpenStack/DC1/APP',
    'resource_group_name_nw': 'OpenStack/DC1/APP',
    'tenant_id': '844eb55f21e84a289e9c22098d387e5d',
    'nwa_tenant_id': 'DC1_844eb55f21e84a289e9c22098d387e5d',
    'physical_network': 'OpenStack/DC1/APP',
    'device': {'owner': 'compute:DC1_KVM',
               'id': '36509c40-58e0-4293-8b16-48b409959b8f'},
    'port': {'ip': '192.168.200.132',
             'mac': 'fa:16:3e:a6:1d:00',
             'id': 'c61583dd-b52b-4bd7-b586-a6b33780090f'}
}

# # delete port with instance
nwa_info_delete_gdv = {
    'subnet': {
        'netaddr': '192.168.200.0',
        'mask': '24',
        'id': '94fdaea5-33ae-4411-b6e0-71e4b099d470'
    },
    'network': {'vlan_type': 'BusinessVLAN',
                'id': 'a94fd0fc-2282-4092-9485-b0f438b0f6c4',
                'name': 'pj1-net100'},
    'resource_group': 'OpenStack/DC1/APP',
    'resource_group_name': 'OpenStack/DC1/APP',
    'tenant_id': '844eb55f21e84a289e9c22098d387e5d',
    'nwa_tenant_id': 'DC1_844eb55f21e84a289e9c22098d387e5d',
    'physical_network': 'OpenStack/DC1/APP',
    'device': {'owner': 'compute:DC1_KVM',
               'id': '36509c40-58e0-4293-8b16-48b409959b8f'},
    'port': {'ip': '192.168.200.161',
             'mac': 'fa:16:3e:bc:18:00',
             'id': '68ef8ee1-277b-4570-cb28-ad514a7699e7'}
}


##########################################
# ### nwa tenant binding dummy data.
# One GeneralDev on TenantNW.
nwa_data_one_gdev = {
    "CreateTenant": 1,
    "CreateTenantNW": 1,
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f": "device_id",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.132",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:a6:1d:00",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_device_owner": "compute:DC1_KVM",  # noqa
    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",  # noqa
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_CreateVlan": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_VlanID": "4000",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD_VlanID": "4000",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD": "connected",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "38"
}

# Two Segment on TenantNW.
nwa_data_two_gdev = {
    "CreateTenant": 1,
    "CreateTenantNW": 1,
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f": "device_id",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.132",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:a6:1d:00",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_device_owner": "compute:DC1_KVM",  # noqa
    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",  # noqa
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",  # noqa

    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_CreateVlan": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_VlanID": "4000",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD_VlanID": "4000",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD": "connected",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "38",

    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054": "device_id",
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_device_owner": "compute:DC1_KVM",
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_f058200f-8fa9-446e-a9d0-86aed2d25a73": "pj1-net101",  # noqa
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_f058200f-8fa9-446e-a9d0-86aed2d25a73_TYPE": "GeneralDev",  # noqa
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_f058200f-8fa9-446e-a9d0-86aed2d25a73_ip_address": "192.168.100.27",  # noqa
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_f058200f-8fa9-446e-a9d0-86aed2d25a73_mac_address": "fa:16:3e:9b:b0:de",  # noqa
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73": "pj1-net101",
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73_network_id": "f058200f-8fa9-446e-a9d0-86aed2d25a73",  # noqa
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73_nwa_network_name": "LNW_BusinessVLAN_107",  # noqa
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73_subnet": "192.168.100.0",
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73_subnet_id": "292af468-18d7-4212-abc5-d55f4ffff656",  # noqa
    "VLAN_f058200f-8fa9-446e-a9d0-86aed2d25a73_OpenStack/DC1/APP": "physical_network",  # noqa
    "VLAN_f058200f-8fa9-446e-a9d0-86aed2d25a73_OpenStack/DC1/APP_CreateVlan": "CreateVlan",  # noqa
    "VLAN_f058200f-8fa9-446e-a9d0-86aed2d25a73_OpenStack/DC1/APP_VlanID": "45"
}

# Two Port on TenantNW.
nwa_data_two_port_gdev = {
    "CreateTenant": 1,
    "CreateTenantNW": 1,
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f": "device_id",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.132",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:a6:1d:00",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_device_owner": "compute:DC1_KVM",

    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789": "device_id",
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",  # noqa
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",  # noqa
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.133",  # noqa
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:bc:18:00",  # noqa
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_device_owner": "compute:DC1_KVM",

    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",  # noqa
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",  # noqa

    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_CreateVlan": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_VlanID": "4000",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD_VlanID": "4000",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD": "connected",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "38",
}

# Two Port on TenantNW.
nwa_data_gdev_fail6 = {
    "CreateTenant": 1,
    "CreateTenantNW": 1,
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f": "device_id",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.132",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:a6:1d:00",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "",  # noqa
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_device_owner": "compute:DC1_KVM",

    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",  # noqa

    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",  # noqa
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",  # noqa

    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_CreateVlan": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_VlanID": "4000",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD": "connected",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD_VlanID": "37",  # noqa
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "38",
}
##########################################


def init_nwa_client_patch(mock):
    succeed = (200, {
        'status': 'SUCCESS',
        'resultdata': {
            'LogicalNWName': 'LNW_BusinessVLAN_4000',
            'TenantFWName': 'T1',
            'VlanID': '4000',
        }
    })
    mock.create_general_dev.return_value = succeed
    mock.create_tenant.return_value = succeed
    mock.create_tenant_nw.return_value = succeed
    mock.create_vlan.return_value = succeed
    mock.delete_general_dev.return_value = succeed
    mock.delete_tenant.return_value = succeed
    mock.delete_tenant_nw.return_value = succeed
    mock.delete_vlan.return_value = succeed


class TestNECNWAAgentRpcCallback(base.BaseTestCase):

    def setUp(self):
        super(TestNECNWAAgentRpcCallback, self).setUp()
        self.context = MagicMock()
        self.agent = MagicMock()
        self.callback = NECNWAAgentRpcCallback(
            self.context, self.agent
        )

    def test_get_nwa_rpc_server(self):
        rd = self.callback.get_nwa_rpc_servers(self.context, kwargs={})
        self.assertIsInstance(rd, dict)

    def test_create_server(self):
        params = {'tenant_id': 'T1'}
        rd = self.callback.create_server(self.context, kwargs=params)
        self.assertIsNotNone(rd)

    def test_delete_server(self):
        params = {'tenant_id': 'T1'}
        rd = self.callback.delete_server(self.context, kwargs=params)
        self.assertIsNotNone(rd)


class TestNECNWAProxyCallback(base.BaseTestCase):

    def setUp(self):
        super(TestNECNWAProxyCallback, self).setUp()
        self.context = MagicMock()
        self.agent = MagicMock()
        self.callback = NECNWAProxyCallback(self.context, self.agent)

    def test_create_general_dev(self):
        params = {}
        self.callback.create_general_dev(self.context, kwargs=params)

    def test_delete_general_dev(self):
        params = {}
        self.callback.delete_general_dev(self.context, kwargs=params)


class TestNECNWANeutronAgentAsNwaClient(base.BaseTestCase):

    @patch('oslo_service.loopingcall.FixedIntervalLoopingCall')
    @patch('neutron.common.rpc.Connection.consume_in_threads')
    @patch('neutron.common.rpc.create_connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1, f2, f3, f4, f5):
        super(TestNECNWANeutronAgentAsNwaClient, self).setUp()
        self._patch_nwa_client()
        self._config_parse()
        self.context = MagicMock()
        self.agent = NECNWANeutronAgent(10)
        self.agent.nwa_core_rpc = NECNWATenantBindingServerRpcApi("dummy")
        rpc.init(cfg.ConfigOpts())

    def _patch_nwa_client(self):
        path = 'networking_nec.plugins.necnwa.nwalib.client.NwaClient'
        patcher = patch(path)
        self.addCleanup(patcher.stop)
        cli = patcher.start()
        self.nwacli = MagicMock()
        cli.return_value = self.nwacli
        init_nwa_client_patch(self.nwacli)

    def _config_parse(self, conf=None, args=None):
        """Create the default configurations."""
        if args is None:
            args = []
        # args += ['--config-file', NEUTRON_CONF]
        args += ['--config-file', NECNWA_INI]

        if conf is None:
            config.init(args=args)
        else:
            conf(args)

    @patch('neutron.common.rpc.Connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi')  # noqa
    def test__setup_rpc(self, f1, f2, f3):
        self.agent.setup_rpc()
        self.assertIsNotNone(self.agent.host)
        self.assertIsNotNone(self.agent.agent_id)
        self.assertIsNotNone(self.agent.context)
        self.assertIsNotNone(self.agent.nwa_core_rpc)
        self.assertIsNotNone(self.agent.state_rpc)
        self.assertIsNotNone(self.agent.callback_nwa)
        self.assertIsNotNone(self.agent.callback_proxy)

    @patch('oslo_messaging.server.MessageHandlingServer')
    def test_create_tenant_rpc_server(self, f1):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        rd = self.agent.create_tenant_rpc_server(tenant_id)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['result'], 'SUCCESS')
        self.assertEqual(rd['tenant_id'], tenant_id)

    @patch('oslo_messaging.rpc.server.get_rpc_server')
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent')
    @patch('neutron.common.rpc.Connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi')  # noqa
    def test_create_tenant_rpc_server_fail(self, f1, f2, f3, f4, f5):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.agent.rpc_servers[tenant_id] = {
            'server': None,
            'topic': "%s-%s" % (self.agent.topic, tenant_id)
        }
        rd = self.agent.create_tenant_rpc_server(tenant_id)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['result'], 'FAILED')

    @patch('oslo_messaging.rpc.server.get_rpc_server')
    def test_delete_tenant_rpc_server(self, f1):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.agent.rpc_servers = {
            tenant_id: {
                'server': f1,
                'topic': "%s-%s" % (self.agent.topic, tenant_id)
            }
        }
        rd = self.agent.delete_tenant_rpc_server(tenant_id)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['result'], 'SUCCESS')
        self.assertEqual(rd['tenant_id'], tenant_id)

    def test_delete_tenant_rpc_server_fail(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.agent.rpc_servers = dict()
        rd = self.agent.delete_tenant_rpc_server(tenant_id)
        self.assertIsInstance(rd, dict)
        self.assertEqual(rd['result'], 'FAILED')

    def test__report_state(self):
        self.assertIsNone(self.agent._report_state())

    def test_loop_handler(self):
        self.assertIsNone(self.agent.loop_handler())

    @patch('time.sleep')
    def test_daemon_loop(self, f1):
        f1.side_effect = ValueError('dummy exception')
        self.assertRaises(
            ValueError,
            self.agent.daemon_loop
        )

    def test__create_tenant_succeed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'

        self.nwacli.create_tenant.return_value = 200, {}

        rcode, body = self.agent._create_tenant(
            self.context,
            nwa_tenant_id=nwa_tenant_id
        )

        self.assertTrue(rcode)
        self.assertIsInstance(body, dict)

    def test__create_tenant_failed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        self.nwacli.create_tenant.return_value = 400, {}
        rcode, body = self.agent._create_tenant(
            self.context,
            nwa_tenant_id=nwa_tenant_id
        )
        self.assertTrue(rcode)
        self.assertIsInstance(body, dict)

    def test__delete_tenant(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        result, nwa_data = self.agent._delete_tenant(
            self.context,
            nwa_tenant_id=nwa_tenant_id
        )

        self.assertTrue(result)
        self.assertIsInstance(nwa_data, dict)

    def test__delete_tenant_failed(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        self.nwacli.delete_tenant.return_value = 500, dict()
        result, nwa_data = self.agent._delete_tenant(
            self.context,
            nwa_tenant_id=nwa_tenant_id
        )
        self.assertIsInstance(nwa_data, dict)
        self.assertTrue(result)

    def test__create_tenant_nw_fail(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        resource_group_name = 'OpenStack/DC1/APP'
        nwa_data1 = {}
        nwa_info = {
            'resource_group_name': resource_group_name,
            'resource_group_name_nw': resource_group_name,
        }
        self.nwacli.create_tenant_nw.return_value = 500, dict()
        result, nwa_data2 = self.agent._create_tenant_nw(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            resource_group_name=resource_group_name,
            nwa_data=nwa_data1,
            nwa_info=nwa_info,
        )
        self.assertEqual(nwa_data1, nwa_data2)
        self.assertFalse(result)

    def test__create_vlan_succeed1(self):
        global nwa_info_add_intf, result_vln
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {}
        nwa_info = deepcopy(nwa_info_add_intf)
        ret_vln = deepcopy(result_vln)
        ret_vln['resultdata']['VlanID'] = '300'
        self.nwacli.create_vlan.return_value = (200, ret_vln)
        result, nwa_data = self.agent._create_vlan(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    def test__create_vlan_fail1(self):
        global nwa_info_add_intf
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {'NW_546a8551-5c2b-4050-a769-cc3c962fc5cf': 'net100'}
        nwa_info = deepcopy(nwa_info_add_intf)
        self.nwacli.create_vlan.return_value = 500, dict()
        result, nwa_data = self.agent._create_vlan(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    def test__delete_vlan_succeed1(self):
        global nwa_info_add_intf, result_dvl
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        # resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {
            "CreateTenantNW": True,
            "CreateTenant": "1",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "device_id",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TenantFWName": "TFW27",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_ip_address": "192.168.100.1",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_mac_address": "fa:16:3e:04:d3:28",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_device_owner": "network:router_interface",  # noqa
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_physical_network": "OpenStack/DC1/APP",  # noqa
            "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_network_id": "546a8551-5c2b-4050-a769-cc3c962fc5cf",  # noqa
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_nwa_network_name": "LNW_BusinessVLAN_120",  # noqa
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet": "192.168.100.0",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet_id": "7dabadaa-06fc-45fb-af0b-33384cf291c4",  # noqa
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf": "physical_network",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_VlanID": "4000",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_CreateVlan": "",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_CreateVlan": "CreateVlan",  # noqa
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP": "physical_network",  # noqa
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",  # noqa
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_VlanID": "62"  # noqa
        }

        nwa_info = deepcopy(nwa_info_add_intf)
        self.nwacli.create_vlan.return_value = (200, deepcopy(result_dvl))
        result, nwa_data = self.agent._delete_vlan(
            self.context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_create_general_dev_succeed1(self, utb, stb, gtb):
        global result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(result_tnw))
        self.nwacli.create_vlan.     return_value = (200, deepcopy(result_vln))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_create_general_dev_succeed2(self, utb, stb, gtb):
        global result_tnw, result_vln, result_cgd
        global nwa_data_one_gdev
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv2)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(result_tnw))
        self.nwacli.create_vlan.     return_value = (200, deepcopy(result_vln))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_create_general_dev_fail1(self, utb, stb, gtb):
        global result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(result_tnw))
        self.nwacli.create_vlan.     return_value = (200, deepcopy(result_vln))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_create_general_dev_fail2(self, utb, stb, gtb):
        global result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(result_tnw))
        self.nwacli.create_vlan.     return_value = (500, deepcopy(result_vln))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_create_general_dev_fail3(self, utb, stb, gtb):
        global result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (500, deepcopy(result_tnw))
        self.nwacli.create_vlan.     return_value = (200, deepcopy(result_vln))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_create_general_dev_fail4(self, utb, stb, gtb):
        global result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        self.nwacli.create_tenant.   return_value = (501, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(result_tnw))
        self.nwacli.create_vlan.     return_value = (200, deepcopy(result_vln))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_succeed1(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global pnwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)
        nwa_data = deepcopy(nwa_data_one_gdev)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = nwa_data

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_succeed2(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = deepcopy(nwa_data_two_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_succeed3(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = deepcopy(nwa_data_two_port_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_fail1(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_fail2(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)
        nwa_data = deepcopy(nwa_data_one_gdev)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = nwa_data

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_fail3(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (500, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_fail4(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (500, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_fail5(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (500, deepcopy(result_dvl))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_fail6(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv, nwa_data_gdev_fail6
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = deepcopy(nwa_data_gdev_fail6)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_delete_general_dev_fail7(self, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw
        global nwa_info_delete_gdv, nwa_data_gdev_fail6
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        self.nwacli.delete_tenant.return_value = (200, dict())
        self.nwacli.delete_tenant_nw.return_value = (200, deepcopy(result_dnw))
        self.nwacli.delete_vlan.return_value = (200, deepcopy(result_dvl))
        gtb.return_value = dict()

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    def test__dummy_ok(self):
        context = MagicMock()
        rcode = MagicMock()
        jbody = MagicMock()
        args = MagicMock()
        kwargs = MagicMock()

        self.agent._dummy_ok(context, rcode, jbody, args, kwargs)

    def test__dummy_ng(self):
        context = MagicMock()
        rcode = MagicMock()
        jbody = MagicMock()
        args = MagicMock()
        kwargs = MagicMock()

        self.agent._dummy_ng(context, rcode, jbody, args, kwargs)

    def test__update_tenant_binding_true(self):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d',
        nwa_data = dict()
        self.agent._update_tenant_binding(
            context,
            tenant_id,
            nwa_tenant_id,
            nwa_data,
            True
        )

    def test__update_tenant_binding_false(self):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d',
        nwa_data = dict()
        self.agent._update_tenant_binding(
            context,
            tenant_id,
            nwa_tenant_id,
            nwa_data,
            False
        )

    #####
    # appendix.

    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    def test_create_general_dev_ex1(self, utb, stb, gtb):
        global result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = "844eb55f21e84a289e9c22098d387e5d"
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = {
            "device": {
                "id": "171fff51-ac4c-444e-99a2-8957ca0fad6e",
                "owner": "compute:DC1_KVM"
            },
            "network": {
                "id": "0ed65870-9acb-48ce-8c0b-e803d527a9d2",
                "name": "net100",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC02_844eb55f21e84a289e9c22098d387e5d",
            "physical_network": "OpenStack/DC1/APP",
            "port": {
                "id": "81f78799-fd82-48ce-98c3-3df91fb4768c",
                "ip": "192.168.100.102",
                "mac": "fa:16:3e:1b:27:f9"
            },
            "resource_group": "OpenStack/DC1/APP",
            "resource_group_name": "OpenStack/DC1/APP",
            "resource_group_name_nw": "OpenStack/DC1/APP",
            "subnet": {
                "id": "df2a7b8a-e027-49ab-bf84-ade82a3c096c",
                "mask": "24",
                "netaddr": "192.168.100.0"
            },
            "tenant_id": "844eb55f21e84a289e9c22098d387e5d"
        }

        self.nwacli.create_tenant.   return_value = (200, dict())
        self.nwacli.create_tenant_nw.return_value = (200, deepcopy(result_tnw))
        self.nwacli.create_vlan.     return_value = (200, deepcopy(result_vln))
        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99": "device_id",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2": "net100",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_TYPE": "TenantFW",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_TenantFWName": "TFW8",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_ip_address": "192.168.100.1",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_mac_address": "fa:16:3e:97:4f:d4",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_TenantFWName": "TFW8",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_device_owner": "network:router_interface",  # noqa
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_physical_network": "OpenStack/DC1/APP",  # noqa
            "NWA_tenant_id": "DC02_844eb55f21e84a289e9c22098d387e5d",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2": "net100",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_network_id": "0ed65870-9acb-48ce-8c0b-e803d527a9d2",  # noqa
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_nwa_network_name": "LNW_BusinessVLAN_108",  # noqa
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_subnet": "192.168.100.0",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_subnet_id": "df2a7b8a-e027-49ab-bf84-ade82a3c096c",  # noqa
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP": "physical_network",  # noqa
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_CreateVlan": "CreateVlan",  # noqa
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_FW_TFW4b18c7ba-1370-410e-af4c-8578fbb3ab99": "connected",  # noqa
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_VlanID": "53"  # noqa
        }

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


def test_check_segment():
    network_id = 'a94fd0fc-2282-4092-9485-b0f438b0f6c4'
    nwa_data = {
        "CreateTenantNW": "1",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1": "device_id",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_TenantFWName": "TFW3",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "TenantFW",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TenantFWName": "TFW3",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.1",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:17:41:b4",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_device_owner": "network:router_interface",  # noqa
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_physical_network": "OpenStack/DC1/APP",  # noqa
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",  # noqa
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_103",  # noqa
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",  # noqa
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_CreateVlan": "",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_VlanID": "4000",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",  # noqa
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "CreateVlan",  # noqa
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_FW_TFW843bc108-2f17-4be4-b9cb-44e00abe78d1": "connected",  # noqa
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "37"  # noqa
    }
    check_segment(network_id, nwa_data)


@patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent')  # noqa
@patch('neutron.common.config')
@patch('sys.argv')
def test_main(f1, f2, f3):
    agent_main()


class TestNECNWANeutronAgentRpc(base.BaseTestCase):

    @patch('oslo_service.loopingcall.FixedIntervalLoopingCall')
    @patch('neutron.common.rpc.Connection.consume_in_threads')
    @patch('neutron.common.rpc.create_connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1, f2, f3, f4, f5):
        super(TestNECNWANeutronAgentRpc, self).setUp()
        self._patch_nwa_client()
        self._config_parse()
        self.agent = NECNWANeutronAgent(10)
        self.agent.nwa_core_rpc = NECNWATenantBindingServerRpcApi("dummy")

    def _patch_nwa_client(self):
        path = 'networking_nec.plugins.necnwa.nwalib.client.NwaClient'
        patcher = patch(path)
        self.addCleanup(patcher.stop)
        cli = patcher.start()
        self.nwacli = MagicMock()
        cli.return_value = self.nwacli
        init_nwa_client_patch(self.nwacli)

    def _config_parse(self, conf=None, args=None):
        """Create the default configurations."""
        if args is None:
            args = []
        # args += ['--config-file', NEUTRON_CONF]
        args += ['--config-file', NECNWA_INI]

        if conf is None:
            config.init(args=args)
        else:
            conf(args)

    # ### GeneralDev: None
    # ### add Openstack/DC/HA1
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_create_general_dev_succeed1(self, stb, utb, gtb):
        global result_tnw, result_vln, result_tfw, nwa_info_add_intf
        context = MagicMock()
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}
        gtb.return_value = None
        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
                "owner": "network:dhcp"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "519c51b8-9328-455a-8ae7-b204754eacea",
                "ip": "192.168.0.1",
                "mac": "fa:16:3e:76:ab:0e"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }
        rc = self.agent.create_general_dev(context,
                                           tenant_id=tenant_id,
                                           nwa_tenant_id=nwa_tenant_id,
                                           nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1
    # ### add Openstack/DC/HA1
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_create_general_dev_succeed21(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "18972752-f0f4-4cf7-b185-971ff6539d21",
                "owner": "compute:DC01_KVM02_ZONE02"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "faa923cc-3bfc-44d1-a66a-31b75b5aad7a",
                "ip": "192.168.0.3",
                "mac": "fa:16:3e:5c:3f:c2"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }
        rc = self.agent.create_general_dev(context,
                                           tenant_id=tenant_id,
                                           nwa_tenant_id=nwa_tenant_id,
                                           nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1
    # ### add Openstack/DC/HA2
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_create_general_dev_succeed3(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "18972752-f0f4-4cf7-b185-971ff6539d21",
                "owner": "compute:DC01_KVM02_ZONE02"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA2",
            "port": {
                "id": "faa923cc-3bfc-44d1-a66a-31b75b5aad7a",
                "ip": "192.168.0.3",
                "mac": "fa:16:3e:5c:3f:c2"
            },
            "resource_group_name": "OpenStack/DC/HA2",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        rc = self.agent.create_general_dev(context,
                                           tenant_id=tenant_id,
                                           nwa_tenant_id=nwa_tenant_id,
                                           nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1 x1
    # ### del Openstack/DC/HA1
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_delete_general_dev_succeed1(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "52",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
                "owner": "network:dhcp"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "519c51b8-9328-455a-8ae7-b204754eacea",
                "ip": "192.168.0.1",
                "mac": "fa:16:3e:76:ab:0e"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        rc = self.agent.delete_general_dev(context,
                                           tenant_id=tenant_id,
                                           nwa_tenant_id=nwa_tenant_id,
                                           nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1 x2
    # ### del Openstack/DC/HA1
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_delete_general_dev_succeed2(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21": "device_id",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.3",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:5c:3f:c2",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_device_owner": "compute:DC01_KVM02_ZONE02",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
                "owner": "network:dhcp"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "519c51b8-9328-455a-8ae7-b204754eacea",
                "ip": "192.168.0.1",
                "mac": "fa:16:3e:76:ab:0e"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        rc = self.agent.delete_general_dev(context,
                                           tenant_id=tenant_id,
                                           nwa_tenant_id=nwa_tenant_id,
                                           nwa_info=nwa_info)
        self.assertTrue(rc)

    # ### GeneralDev: Openstack/DC/HA1 x1, Openstack/DC/HA2 x1
    # ### del Openstack/DC/HA1
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.get_nwa_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')  # noqa
    @patch('networking_nec.plugins.necnwa.necnwa_core_plugin.NECNWATenantBindingServerRpcApi.set_nwa_tenant_binding')  # noqa
    def test_delete_general_dev_succeed3(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"

        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCESS'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21": "device_id",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2": "GeneralDev",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.3",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:5c:3f:c2",  # noqa
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_device_owner": "compute:DC01_KVM02_ZONE02",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",  # noqa  # noqa
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",  # noqa
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",  # noqa
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2_GD": "physical_network",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2_GD_VlanID": "53",  # noqa
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "4000"
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",  # noqa
                "owner": "network:dhcp"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/HA1",
            "port": {
                "id": "519c51b8-9328-455a-8ae7-b204754eacea",
                "ip": "192.168.0.1",
                "mac": "fa:16:3e:76:ab:0e"
            },
            "resource_group_name": "OpenStack/DC/HA1",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }
        rc = self.agent.delete_general_dev(context,
                                           tenant_id=tenant_id,
                                           nwa_tenant_id=nwa_tenant_id,
                                           nwa_info=nwa_info)
        self.assertTrue(rc)
