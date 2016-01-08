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

import logging
import re
import os
import unittest
import json

from copy import deepcopy

from oslo.config import cfg
from neutron.common.test_lib import test_config
from neutron.extensions import portbindings
from neutron.common import constants as q_const

from mock import patch, MagicMock
from nose.tools import ok_, eq_, raises
from sqlalchemy.orm import exc as sa_exc
from neutron.common import exceptions as n_exc
from neutron.common import config
from neutron.common import rpc

from neutron.plugins.necnwa.nwalib import client as nwa_cli

from neutron.plugins.necnwa.agent.necnwa_neutron_agent import (
    NECNWAAgentRpcCallback,
    NECNWAProxyCallback,
    NECNWANeutronAgent,
)

from neutron.plugins.necnwa.necnwa_core_plugin import (
    NECNWAPluginTenantBinding
)

from neutron.plugins.necnwa.agent.necnwa_neutron_agent import main as agent_main
from neutron.plugins.necnwa.agent.necnwa_neutron_agent import check_segment

log_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s,%(msecs).03d - %(levelname)s - '
    '%(filename)s:%(lineno)d - %(message)s',
    '%H:%M:%S'
)

log_handler.setFormatter(formatter)
log_handler.setLevel(logging.INFO)

LOG = logging.getLogger()
LOG.addHandler(log_handler)
LOG.setLevel(logging.INFO)

context = MagicMock()

ROOTDIR = '/'
ETCDIR = os.path.join(ROOTDIR, 'etc/neutron')

"""""
test params
"""""
##############################
## NWA Server dummy responce
## CreateTenantNW succeed
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
    "status": "SUCCEED"
}

## CreateVlan succeed
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
    "status": "SUCCEED"
}

## CreateTenantFW succeed
result_tfw = {
    "progress": 100,
    "resultdata": {
        "AutoRecovery": "0",
        "DCResourceReserveID": "1",
        "DCResourceReserveID_Delete": "",
        "ErrorMessage": "",
        "FWFIPAddressList": "192.168.100.1",
        "FwIpAddressList": "192.168.100.1",
        "InJsonFileName": "",
        "LogicalNWName": "LNW_BusinessVLAN_100",
        "OutJsonFileName": "",
        "ResourceGroupName": "OpenStack/DC1/APP",
        "TenantFWInfo": "FortiGate",
        "TenantFWName": "TFW12",
        "TenantID": "DC1_844eb55f21e84a289e9c22098d387e5d",
        "VlanID": "100",
        "VlanLoopCounter": "1"
    },
    "status": "SUCCEED"
}

## CreateGeneralDev succeed
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
    "status": "SUCCEED"
}


## DeleteVlan succeed
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
    "status": "SUCCEED"
}

## DeleteTenantNW succeed
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
    "status": "SUCCEED"
}

## DeleteGeneralDev succeed
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
    "status": "SUCCEED"
}

## DeleteGeneralDev failed
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

## DeleteTenantFW succeed
result_dtf = {
    "progress": 100,
    "resultdata": {
        "DCResourceReserveID": "1",
        "ErrorMessage": "",
        "NWAResult": "No result log\r\n",
        "TenantID": "DC02_c7cd22568cc9464e9818932ab101731e",
        "UNC_LoopCounter": "1",
        "VlanLoopCounter": "0"
    },
    "status": "SUCCEED"
}

##########################

"""
nwa_info
"""

## add_router_interface.
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

## create port with instance
nwa_info_create_gdv = {
    'subnet': {
        'netaddr': '192.168.200.0',
        'mask': '24',
        'id': '94fdaea5-33ae-4411-b6e0-71e4b099d470'
    },
            'network': {'vlan_type': 'BusinessVLAN', 'id': 'a94fd0fc-2282-4092-9485-b0f438b0f6c4', 'name': 'pj1-net100'},
    'resource_group': 'OpenStack/DC1/APP',
    'tenant_id': '844eb55f21e84a289e9c22098d387e5d',
    'nwa_tenant_id': 'DC1_844eb55f21e84a289e9c22098d387e5d',
    'physical_network': 'OpenStack/DC1/APP',
    'device': {'owner': 'compute:DC1_KVM', 'id': '36509c40-58e0-4293-8b16-48b409959b8f'},
    'port': {'ip': '192.168.200.132', 'mac': 'fa:16:3e:a6:1d:00', 'id': 'c61583dd-b52b-4bd7-b586-a6b33780090f'}
}

nwa_info_create_gdv2 = {
    'subnet': {
        'netaddr': '192.168.200.0',
        'mask': '24',
        'id': '94fdaea5-33ae-4411-b6e0-71e4b099d470'
    },
    'network': {'vlan_type': 'BusinessVLAN', 'id': 'a94fd0fc-2282-4092-9485-b0f438b0f6c4', 'name': 'pj1-net100'},
    'resource_group': 'OpenStack/DC1/APP',
    'tenant_id': '844eb55f21e84a289e9c22098d387e5d',
    'nwa_tenant_id': 'DC1_844eb55f21e84a289e9c22098d387e5d',
    'physical_network': 'OpenStack/DC1/APP',
    'device': {'owner': 'compute:DC1_KVM', 'id': '36509c40-58e0-4293-8b16-48b409959b8f'},
    'port': {'ip': '192.168.200.132', 'mac': 'fa:16:3e:a6:1d:00', 'id': 'c61583dd-b52b-4bd7-b586-a6b33780090f'}
}

## delete port with instance
nwa_info_delete_gdv = {
    'subnet': {
        'netaddr': '192.168.200.0',
        'mask': '24',
        'id': '94fdaea5-33ae-4411-b6e0-71e4b099d470'
    },
    'network': {'vlan_type': 'BusinessVLAN', 'id': 'a94fd0fc-2282-4092-9485-b0f438b0f6c4', 'name': 'pj1-net100'},
    'resource_group': 'OpenStack/DC1/APP',
    'tenant_id': '844eb55f21e84a289e9c22098d387e5d',
    'nwa_tenant_id': 'DC1_844eb55f21e84a289e9c22098d387e5d',
    'physical_network': 'OpenStack/DC1/APP',
    'device': {'owner': 'compute:DC1_KVM', 'id': '36509c40-58e0-4293-8b16-48b409959b8f'},
    'port': {'ip': '192.168.200.161', 'mac': 'fa:16:3e:bc:18:00', 'id': '68ef8ee1-277b-4570-cb28-ad514a7699e7'}
}


##########################################
#### nwa tenant binding dummy data.
# One Interface on TFW
nwa_data_tfw_one_inf = {
    "CreateTenantNW": True,
    "CreateTenant": "1",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "device_id",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TenantFWName": "TFW27",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_ip_address": "192.168.100.1",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_mac_address": "fa:16:3e:04:d3:28",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_TenantFWName": "TFW27",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_device_owner": "network:router_interface",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_physical_network": "OpenStack/DC1/APP",
    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_network_id": "546a8551-5c2b-4050-a769-cc3c962fc5cf",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_nwa_network_name": "LNW_BusinessVLAN_120",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet": "192.168.100.0",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet_id": "7dabadaa-06fc-45fb-af0b-33384cf291c4",
    "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_CreateVlan": "",
    "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP": "physical_network",
    "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",
    "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_VlanID": "62"
}

# Two Interface on TFW
nwa_data_tfw_two_inf = {
    "CreateTenantNW": True,
    "CreateTenant": "1",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "device_id",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TenantFWName": "TFW27",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_ip_address": "192.168.100.1",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_mac_address": "fa:16:3e:04:d3:28",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31": "net101",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_TYPE": "TenantFW",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_TenantFWName": "TFW27",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_ip_address": "192.168.101.1",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_mac_address": "fa:16:3e:34:9a:c9",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_TenantFWName": "TFW27",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_device_owner": "network:router_interface",
    "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_physical_network": "OpenStack/DC1/APP",
    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_network_id": "546a8551-5c2b-4050-a769-cc3c962fc5cf",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_nwa_network_name": "LNW_BusinessVLAN_120",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet": "192.168.100.0",
    "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet_id": "7dabadaa-06fc-45fb-af0b-33384cf291c4",
    "NW_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31": "net101",
    "NW_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_network_id": "7ac3fe26-cb61-48a7-9baa-7dc2d3caef31",
    "NW_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_nwa_network_name": "LNW_BusinessVLAN_119",
    "NW_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_subnet": "192.168.101.0",
    "NW_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_subnet_id": "7f589e20-29d9-4a48-9b6a-ef551a9ca566",
    "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP": "physical_network",
    "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",
    "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_VlanID": "61",
    "VLAN_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_OpenStack/DC1/APP": "physical_network",
    "VLAN_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",
    "VLAN_7ac3fe26-cb61-48a7-9baa-7dc2d3caef31_OpenStack/DC1/APP_VlanID": "62"
}

# One GeneralDev on TenantNW.
nwa_data_one_gdev = {
    "CreateTenant": 1,
    "CreateTenantNW": 1,
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f": "device_id",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.132",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:a6:1d:00",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_device_owner": "compute:DC1_KVM",
    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD": "connected",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "38"
}

# Two Segment on TenantNW.
nwa_data_two_gdev = {
    "CreateTenant": 1,
    "CreateTenantNW": 1,
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f": "device_id",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.132",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:a6:1d:00",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_device_owner": "compute:DC1_KVM",
    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD": "connected",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "38",

    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054": "device_id",
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_device_owner": "compute:DC1_KVM",
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_f058200f-8fa9-446e-a9d0-86aed2d25a73": "pj1-net101",
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_f058200f-8fa9-446e-a9d0-86aed2d25a73_TYPE": "GeneralDev",
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_f058200f-8fa9-446e-a9d0-86aed2d25a73_ip_address": "192.168.100.27",
    "DEV_1547cdd1-5fcc-437e-b2fb-30b0021a0054_f058200f-8fa9-446e-a9d0-86aed2d25a73_mac_address": "fa:16:3e:9b:b0:de",
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73": "pj1-net101",
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73_network_id": "f058200f-8fa9-446e-a9d0-86aed2d25a73",
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73_nwa_network_name": "LNW_BusinessVLAN_107",
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73_subnet": "192.168.100.0",
    "NW_f058200f-8fa9-446e-a9d0-86aed2d25a73_subnet_id": "292af468-18d7-4212-abc5-d55f4ffff656",
    "VLAN_f058200f-8fa9-446e-a9d0-86aed2d25a73_OpenStack/DC1/APP": "physical_network",
    "VLAN_f058200f-8fa9-446e-a9d0-86aed2d25a73_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
    "VLAN_f058200f-8fa9-446e-a9d0-86aed2d25a73_OpenStack/DC1/APP_VlanID": "45"
}

# Two Port on TenantNW.
nwa_data_two_port_gdev = {
    "CreateTenant": 1,
    "CreateTenantNW": 1,
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f": "device_id",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.132",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:a6:1d:00",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_device_owner": "compute:DC1_KVM",

    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789": "device_id",
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.133",
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:bc:18:00",
    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_device_owner": "compute:DC1_KVM",

    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD": "connected",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "38",
}

# Two Port on TenantNW.
nwa_data_gdev_fail6 = {
    "CreateTenant": 1,
    "CreateTenantNW": 1,
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f": "device_id",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.132",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:a6:1d:00",
    "DEV_36509c40-58e0-4293-8b16-48b409959b8f_device_owner": "compute:DC1_KVM",

    "DEV_2180ae23-ad33-4a89-8eef-f2f28e62e789_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "GeneralDev",

    "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_100",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
    "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_GD": "connected",
    "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "38",
}
##########################################



def etcdir(*p):
    return os.path.join(ETCDIR, *p)

def setup():
    pass

class TestNECNWAAgentRpcCallback:

    def setUp(self):
        context = MagicMock()
        agent = MagicMock()
        self.callback = NECNWAAgentRpcCallback(context, agent) 

    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWAAgentRpcCallback')
    def test_get_nwa_rpc_server(self, cb):
        self.callback.get_nwa_rpc_servers(context, kwargs={})

    def test_create_server(self):
        params = {'tenant_id': '844eb55f21e84a289e9c22098d387e5d'}
        self.callback.create_server(context, kwargs=params)

    def test_delete_server(self):
        params = {'tenant_id': '844eb55f21e84a289e9c22098d387e5d'}
        self.callback.delete_server(context, kwargs=params)

class TestNECNWAProxyCallback:

    def setUp(self):
        context = MagicMock()
        agent = MagicMock()
        self.callback = NECNWAProxyCallback(context, agent) 

    def test_create_general_dev(self):
        params = {}
        self.callback.create_general_dev(context, kwargs=params)

    def test_delete_general_dev(self):
        params = {}
        self.callback.delete_general_dev(context, kwargs=params)

    def test_create_tenant_fw(self):
        params = {}
        self.callback.create_tenant_fw(context, kwargs=params)

    def test_delete_tenant_fw(self):
        params = {}
        self.callback.delete_tenant_fw(context, kwargs=params)

    def test_setting_nat(self):
        params = {}
        self.callback.setting_nat(context, kwargs=params)

    def test_delete_nat(self):
        params = {}
        self.callback.delete_nat(context, kwargs=params)

class TestNECNWANeutronAgent(unittest.TestCase):

    @patch('neutron.openstack.common.loopingcall.FixedIntervalLoopingCall')
    @patch('neutron.common.rpc.Connection.consume_in_threads')
    @patch('neutron.common.rpc.create_connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1, f2, f3, f4, f5):
        self.config_parse()
        self.agent = NECNWANeutronAgent(10)
        self.agent.nwa_core_rpc = NECNWAPluginTenantBinding("dummy")

    def config_parse(self, conf=None, args=None):
        """Create the default configurations."""
        if args is None:
            args = []
        args += ['--config-file', etcdir('neutron.conf')]
        args += ['--config-file', etcdir('plugin.ini')]

        if conf is None:
            config.init(args=args)
        else:
            conf(args)

    @patch('neutron.common.rpc.Connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding')
    def test__setup_rpc(self, f1, f2, f3):
        self.agent.setup_rpc()

    @patch('oslo.messaging.get_rpc_server')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent')
    @patch('neutron.common.rpc.Connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding')
    def test_create_tenant_rpc_server(self, f1, f2, f3, f4, f5):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        rpc.TRANSPORT = object
        self.agent.create_tenant_rpc_server(tenant_id)

    @patch('oslo.messaging.get_rpc_server')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent')
    @patch('neutron.common.rpc.Connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding')
    def test_create_tenant_rpc_server_fail(self, f1, f2, f3, f4, f5):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        rpc.TRANSPORT = object
        self.agent.rpc_servers[tenant_id] = {
            'server': None,
            'topic': "%s-%s" % (self.agent.topic, tenant_id)
        }
        self.agent.create_tenant_rpc_server(tenant_id)

    @patch('oslo.messaging.get_rpc_server')
    def test_delete_tenant_rpc_server(self, f1):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.agent.rpc_servers = {
            tenant_id: {
                'server': f1,
                'topic': "%s-%s" % (self.agent.topic, tenant_id)
            }
        }
        self.agent.delete_tenant_rpc_server(tenant_id)

    def test_delete_tenant_rpc_server_fail(self):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        self.agent.rpc_servers = dict()
        self.agent.delete_tenant_rpc_server(tenant_id)

    def test__report_state(self):
        self.agent._report_state()

    def test__report_state_excpt(self):
        self.agent.agent_state = []
        try:
            self.agent._report_state()
        except:
            pass

    def test_loop_handler(self):
        self.agent.loop_handler()

    @patch('time.sleep')
    def test_daemon_loop(self, f1):
        f1.side_effect = Exception('dummy exception')
        try:
            self.agent.daemon_loop()
        except:
            pass

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test__create_tenant_succeed(self, ctn):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'

        ctn.return_value = 200, {}

        rcode, body = self.agent._create_tenant(
            context,
            nwa_tenant_id=nwa_tenant_id
        )

        eq_(rcode, True)
        self.assertIsInstance(body, dict)


    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test__create_tenant_failed(self, ctn):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'

        ctn.return_value = 400, {}

        rcode, body = self.agent._create_tenant(
            context,
            nwa_tenant_id=nwa_tenant_id
        )

        eq_(rcode, False)
        self.assertIsInstance(body, dict)

    def test__delete_tenant(self):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        result, nwa_data = self.agent._delete_tenant(
            context,
            nwa_tenant_id=nwa_tenant_id
        )

        eq_(result, True)
        self.assertIsInstance(nwa_data, dict)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test__delete_tenant_failed(self, dtn):
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        dtn.return_value = 500, dict()
        result, nwa_data = self.agent._delete_tenant(
            context,
            nwa_tenant_id=nwa_tenant_id
        )

        self.assertIsInstance(nwa_data, dict)
        eq_(result, False)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    def test__create_tenant_nw_fail(self, ctn):
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {}
        ctn.return_value = 500, dict()
        result, nwa_data = self.agent._create_tenant_nw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            resource_group_name=resource_group_name,
            nwa_data=nwa_data
        )

        self.assertIsInstance(nwa_data, dict)
        eq_(result, False)

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    def test__create_vlan_succeed1(self, vln):
        global nwa_info_add_intf, result_vln
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {}
        nwa_info = deepcopy(nwa_info_add_intf)
        ret_vln = deepcopy(result_vln)
        ret_vln['resultdata']['VlanID'] = '300'
        vln.return_value = (200, ret_vln)
        result, nwa_data = self.agent._create_vlan(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    def test__create_vlan_fail1(self, vln):
        global nwa_info_add_intf
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {'NW_546a8551-5c2b-4050-a769-cc3c962fc5cf': 'net100'}
        nwa_info = deepcopy(nwa_info_add_intf)
        vln.return_value = 500, dict()
        result, nwa_data = self.agent._create_vlan(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    def test__delete_vlan_succeed1(self, vln):
        global nwa_info_add_intf, result_dvl
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + '844eb55f21e84a289e9c22098d387e5d'
        resource_group_name = 'OpenStack/DC1/APP'
        nwa_data = {
            "CreateTenantNW": True,
            "CreateTenant": "1",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "device_id",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_ip_address": "192.168.100.1",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_mac_address": "fa:16:3e:04:d3:28",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_device_owner": "network:router_interface",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_physical_network": "OpenStack/DC1/APP",
            "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_network_id": "546a8551-5c2b-4050-a769-cc3c962fc5cf",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_nwa_network_name": "LNW_BusinessVLAN_120",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet": "192.168.100.0",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet_id": "7dabadaa-06fc-45fb-af0b-33384cf291c4",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP": "physical_network",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_VlanID": "62"
        }

        nwa_info = deepcopy(nwa_info_add_intf)
        vln.return_value = (200, deepcopy(result_dvl))
        result, nwa_data = self.agent._delete_vlan(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info,
            nwa_data=nwa_data
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_succeed1(self, stb, ct, f2, f3, f4, f5, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_info = deepcopy(nwa_info_add_intf)

        ct.return_value = (200, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        f2.return_value = (200, deepcopy(result_tnw))
        f3.return_value = (200, deepcopy(result_vln))
        f4.return_value = (200, deepcopy(result_tfw))
        f5.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        # empty data.
        gtb.return_value = dict()

        result = self.agent.create_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

        self.assertIsInstance(result, dict)
        eq_(result['status'], 'SUCCEED')

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_fail1(self, stb, ct, f2, f3, f4, f5, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_info = deepcopy(nwa_info_add_intf)

        ct.return_value = (501, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        f2.return_value = (200, deepcopy(result_tnw))
        f3.return_value = (200, deepcopy(result_vln))
        f4.return_value = (200, deepcopy(result_tfw))
        f5.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        # empty data.
        gtb.return_value = dict()

        result = self.agent.create_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

        #self.assertIsInstance(result, None)

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_fail2(self, stb, ct, f2, f3, f4, f5, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_info = deepcopy(nwa_info_add_intf)

        ct.return_value = (200, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        f2.return_value = (500, deepcopy(result_tnw))
        f3.return_value = (200, deepcopy(result_vln))
        f4.return_value = (200, deepcopy(result_tfw))
        f5.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        # empty data.
        gtb.return_value = dict()

        result = self.agent.create_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

        self.assertIsInstance(result, dict)

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_fail3(self, stb, ct, f2, f3, f4, f5, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_info = deepcopy(nwa_info_add_intf)

        ct.return_value = (200, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        f2.return_value = (200, deepcopy(result_tnw))
        f3.return_value = (500, deepcopy(result_vln))
        f4.return_value = (200, deepcopy(result_tfw))
        f5.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        # empty data.
        gtb.return_value = dict()

        result = self.agent.create_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

        self.assertIsInstance(result, dict)

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_fail4(self, stb, ct, ctn, cvl, ctf, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_info = deepcopy(nwa_info_add_intf)

        ct.return_value = (200, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        ctf.return_value = (500, deepcopy(result_tfw))
        utb.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        # empty data.
        gtb.return_value = dict()

        result = self.agent.create_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

        self.assertIsInstance(result, dict)

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.update_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_update_tenant_fw_succeed1(self, stb, ct, ctn, cvl, utf, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_info = deepcopy(nwa_info_add_intf2)

        ct.return_value = (200, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        utf.return_value = (200, deepcopy(result_tfw))
        utb.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        # empty data.
        gtb.return_value = deepcopy(nwa_data_tfw_one_inf)

        result = self.agent.create_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

        self.assertIsInstance(result, dict)
        eq_(result['status'], 'SUCCEED')


    # UpdateTenantFW disconnect.
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.update_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_update_tenant_fw_disconnect_succeed1(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_two_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dtf.return_value = (200, deepcopy(result_dtf))
        gtb.return_value = nwa_data

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.update_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_update_tenant_fw_disconnect_fail1(self, dt, dtn, dvl, utf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_two_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        utf.return_value = (500, deepcopy(result_dtf))
        gtb.return_value = nwa_data

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.update_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_update_tenant_fw_disconnect_fail2(self, dt, dtn, dvl, utf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_two_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        utf.return_value = (500, deepcopy(result_dtf))
        gtb.return_value = dict()

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.update_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_update_tenant_fw_fail1(self, stb, ct, ctn, cvl, utf, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_info = deepcopy(nwa_info_add_intf2)

        ct.return_value = (200, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        utf.return_value = (500, deepcopy(result_tfw))
        utb.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        # empty data.
        gtb.return_value = deepcopy(nwa_data_tfw_one_inf)

        result = self.agent.create_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

        self.assertIsInstance(result, dict)

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.update_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_update_tenant_fw_fail2(self, stb, ct, ctn, cvl, utf, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_844eb55f21e84a289e9c22098d387e5d'
        nwa_info = deepcopy(nwa_info_add_intf)

        ct.return_value = (200, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        utf.return_value = (200, deepcopy(result_tfw))
        utb.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        gtb.return_value = {
            "CreateTenantNW": True,
            "CreateTenant": "1",
            #"DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "device_id",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_ip_address": "192.168.100.1",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_mac_address": "fa:16:3e:04:d3:28",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_device_owner": "network:router_interface",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_physical_network": "OpenStack/DC1/APP",
            "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_network_id": "546a8551-5c2b-4050-a769-cc3c962fc5cf",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_nwa_network_name": "LNW_BusinessVLAN_120",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet": "192.168.100.0",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet_id": "7dabadaa-06fc-45fb-af0b-33384cf291c4",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP": "physical_network",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_VlanID": "62"
        }

        # empty data.
        gtb.return_value = deepcopy(nwa_data_tfw_one_inf)

        result = self.agent.create_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

        self.assertIsInstance(result, dict)

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_tenant_fw_succeed1(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_one_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dtf.return_value = (200, deepcopy(result_dtf))
        gtb.return_value = nwa_data

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_tenant_fw_fail1(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_one_inf)

        dt.return_value = (500, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dtf.return_value = (200, deepcopy(result_dtf))
        gtb.return_value = nwa_data

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_tenant_fw_fail2(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_one_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (500, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dtf.return_value = (200, deepcopy(result_dtf))
        gtb.return_value = nwa_data

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_tenant_fw_fail3(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_one_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (500, deepcopy(result_dvl))
        dtf.return_value = (200, deepcopy(result_dtf))
        gtb.return_value = nwa_data

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_tenant_fw_fail4(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_one_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dtf.return_value = (500, deepcopy(result_dtf))
        gtb.return_value = nwa_data

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_tenant_fw_fail5(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_two_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dtf.return_value = (200, deepcopy(result_dtf))
        gtb.return_value = {
            "CreateTenantNW": True,
            "CreateTenant": "1",
            "DEV_6b34210c-INVALID-DEVICE-ID_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "device_id",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_ip_address": "192.168.100.1",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_mac_address": "fa:16:3e:04:d3:28",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_device_owner": "network:router_interface",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_physical_network": "OpenStack/DC1/APP",
            "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_network_id": "546a8551-5c2b-4050-a769-cc3c962fc5cf",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_nwa_network_name": "LNW_BusinessVLAN_120",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet": "192.168.100.0",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet_id": "7dabadaa-06fc-45fb-af0b-33384cf291c4",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP": "physical_network",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_VlanID": "61",
        }

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_tenant_fw_fail6(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_intf)
        nwa_data = deepcopy(nwa_data_tfw_two_inf)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dtf.return_value = (200, deepcopy(result_dtf))
        gtb.return_value = {
            "CreateTenantNW": True,
            "CreateTenant": "1",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "device_id",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TYPE": "TenantFW",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_ip_address": "192.168.100.1",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_546a8551-5c2b-4050-a769-cc3c962fc5cf_mac_address": "fa:16:3e:04:d3:28",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_TenantFWName": "TFW27",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_device_owner": "network:router_interface",
            "DEV_6b34210c-bd74-47f0-8dc3-3bad9bc333c3_physical_network": "OpenStack/DC1/APP",
            "NWA_tenant_id": "DC1_844eb55f21e84a289e9c22098d387e5d",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf": "net100",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_network_id": "546a8551-5c2b-4050-a769-cc3c962fc5cf",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_nwa_network_name": "LNW_BusinessVLAN_120",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet": "192.168.100.0",
            "NW_546a8551-5c2b-4050-a769-cc3c962fc5cf_subnet_id": "7dabadaa-06fc-45fb-af0b-33384cf291c4",

            "NW_INVALID_NET_ID_network_id": "7ac3fe26-cb61-48a7-9baa-7dc2d3caef31",

            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP": "physical_network",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_FW_TFW6b34210c-bd74-47f0-8dc3-3bad9bc333c3": "connected",
            "VLAN_546a8551-5c2b-4050-a769-cc3c962fc5cf_OpenStack/DC1/APP_VlanID": "61",
        }

        self.agent.delete_tenant_fw(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


    def test_update_tenant_fw(self):
        pass

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test_create_general_dev_succeed1(self, ct, ctn, cvl, cgd, utb, stb, gtb):
        global nwa_info_create_gdv, result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        ct.return_value = (200, dict())
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        cgd.return_value = (200, deepcopy(result_cgd))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test_create_general_dev_succeed2(self, ct, ctn, cvl, cgd, utb, stb, gtb):
        global nwa_info_create_gdv2, result_tnw, result_vln, result_cgd, nwa_data_one_gdev
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv2)

        ct.return_value = (200, dict())
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        cgd.return_value = (200, deepcopy(result_cgd))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test_create_general_dev_fail1(self, ct, ctn, cvl, cgd, utb, stb, gtb):
        global nwa_info_create_gdv, result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        ct.return_value = (200, dict())
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        cgd.return_value = (500, deepcopy(result_cgd))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test_create_general_dev_fail2(self, ct, ctn, cvl, cgd, utb, stb, gtb):
        global nwa_info_create_gdv, result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        ct.return_value = (200, dict())
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (500, deepcopy(result_vln))
        cgd.return_value = (200, deepcopy(result_cgd))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test_create_general_dev_fail3(self, ct, ctn, cvl, cgd, utb, stb, gtb):
        global nwa_info_create_gdv, result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        ct.return_value = (200, dict())
        ctn.return_value = (500, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        cgd.return_value = (200, deepcopy(result_cgd))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test_create_general_dev_fail4(self, ct, ctn, cvl, cgd, utb, stb, gtb):
        global nwa_info_create_gdv, result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_create_gdv)

        ct.return_value = (501, dict())
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        cgd.return_value = (200, deepcopy(result_cgd))
        gtb.return_value = dict()

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_succeed1(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)
        nwa_data = deepcopy(nwa_data_one_gdev)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd))
        gtb.return_value = nwa_data

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_succeed2(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd))
        gtb.return_value = deepcopy(nwa_data_two_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_succeed3(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd))
        gtb.return_value = deepcopy(nwa_data_two_port_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_fail1(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd_fail))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_fail2(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)
        nwa_data = deepcopy(nwa_data_one_gdev)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (500, deepcopy(result_dgd_fail))
        gtb.return_value = nwa_data

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_fail3(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        dt.return_value = (500, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_fail4(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        dt.return_value = (200, dict())
        dtn.return_value = (500, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_fail5(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (500, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd))
        gtb.return_value = deepcopy(nwa_data_one_gdev)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_fail6(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv, nwa_data_gdev_fail6
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd))
        gtb.return_value = deepcopy(nwa_data_gdev_fail6)

        self.agent.delete_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_general_dev_fail7(self, dt, dtn, dvl, dgd, utb, stb, gtb):
        global nwa_data_one_gdev, result_dgd, result_dvl, result_dnw, nwa_info_delete_gdv, nwa_data_gdev_fail6
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info = deepcopy(nwa_info_delete_gdv)

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dgd.return_value = (200, deepcopy(result_dgd))
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

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_nat')
    def test__delete_nat(self, f1):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id
        }
        nwa_data = {
            'DEV_' + device_id + '_TenantFWName': 'TFW3',
            'NW_' + network_id + '_nwa_network_name': 'LNW_BusinessVLAN_101',
            'NAT_' + floating_id: 'd5375e34-0e68-4543-86c2-a447ff3fef44',
            'NAT_' + floating_id + '_fixed_ip_address': '192.168.101.104',
            'NAT_' + floating_id + '_floating_ip_address': '172.16.100.4',
            'NAT_' + floating_id + '_network_id': network_id
        }

        dn_value = {
            'status': 'SUCCEED',
            'NAT_' + '68fa278e-cdf9-4751-839f-68f36e470251': device_id
        }

        f1.return_value = (200, dn_value)

        self.agent._delete_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data,
            floating=floating
        )

    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._setting_nat')
    def test_setting_nat(self, f1, f2, f3):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id
        }

        f1.return_value = (True, dict())
        f3.return_value = {}
        
        self.agent.setting_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            floating=floating
        )

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._setting_nat')
    def test_setting_nat_fail1(self, f1, f2):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id
        }

        f1.return_value = (False, dict())
        
        self.agent.setting_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            floating=floating
        )

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.setting_nat')
    def test__setting_nat(self, f1):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id,
            'tenant_id': tenant_id
        }
        nwa_data = {
            'DEV_' + device_id + '_TenantFWName': 'TFW3',
            'NW_' + network_id + '_nwa_network_name': 'LNW_BusinessVLAN_101',
        }

        ret_val = {'status': 'SUCCEED'}
        f1.return_value = (200, ret_val)

        self.agent._setting_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data,
            floating=floating
        )

    # CASE: retrun error number from nwa client library.
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.setting_nat')
    def test__setting_nat_fail1(self, f1):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id,
            'tenant_id': tenant_id
        }
        nwa_data = {
            'DEV_' + device_id + '_TenantFWName': 'TFW3',
            'NW_' + network_id + '_nwa_network_name': 'LNW_BusinessVLAN_101',
        }

        f1.return_value = (500, dict())

        self.agent._setting_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data,
            floating=floating
        )

    # CASE: retrun status FAILED from nwa client library.
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.setting_nat')
    def test__setting_nat_fail2(self, f1):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id,
            'tenant_id': tenant_id
        }
        nwa_data = {
            'DEV_' + device_id + '_TenantFWName': 'TFW3',
            'NW_' + network_id + '_nwa_network_name': 'LNW_BusinessVLAN_101',
        }

        ret_val = {'status': 'FAILED'}
        f1.return_value = (200, ret_val)

        self.agent._setting_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data,
            floating=floating
        )

    # CASE: already in use NAT key.
    def test__setting_nat_fail3(self):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id,
            'tenant_id': tenant_id
        }
        nwa_data = {
            'DEV_' + device_id + '_TenantFWName': 'TFW3',
            'NW_' + network_id + '_nwa_network_name': 'LNW_BusinessVLAN_101',
            'NAT_' + floating_id: device_id
        }

        self.agent._setting_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data,
            floating=floating
        )

    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._delete_nat')
    def test_delete_nat(self, f1, f2, f3):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        f1.return_value = (True, dict())
        f3.return_value = {}
        
        self.agent.delete_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id
        )

    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._delete_nat')
    def test_delete_nat_fail(self, f1, f2, f3):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id

        f1.return_value = (False, dict())
        f3.return_value = {}
        
        self.agent.delete_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id
        )

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_nat')
    def test__delete_nat_fail1(self, f1):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id
        }
        nwa_data = {
            'DEV_' + device_id + '_TenantFWName': 'TFW3',
            'NW_' + network_id + '_nwa_network_name': 'LNW_BusinessVLAN_101',
            'NAT_' + floating_id: 'd5375e34-0e68-4543-86c2-a447ff3fef44',
            'NAT_' + floating_id + '_fixed_ip_address': '192.168.101.104',
            'NAT_' + floating_id + '_floating_ip_address': '172.16.100.4',
            'NAT_' + floating_id + '_network_id': network_id
        }

        f1.return_value = (500, dict())

        self.agent._delete_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data,
            floating=floating
        )

    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_nat')
    def test__delete_nat_fail2(self, f1):
        context = MagicMock()
        tenant_id = '844eb55f21e84a289e9c22098d387e5d'
        nwa_tenant_id = 'DC1_' + tenant_id
        network_id = '68fa278e-cdf9-4751-839f-68f36e470251'
        device_id = 'd5375e34-0e68-4543-86c2-a447ff3fef44'
        floating_id = 'f0a05355-0986-4548-aa88-a70d70dfc122'

        floating = {
            'id': 'f0a05355-0986-4548-aa88-a70d70dfc122',
            'floating_network_id': network_id,
            'floating_ip_address': '172.16.100.4',
            'fixed_ip_address': '192.168.101.104',
            'device_id': device_id
        }
        nwa_data = {
            'DEV_' + device_id + '_TenantFWName': 'TFW3',
            'NW_' + network_id + '_nwa_network_name': 'LNW_BusinessVLAN_101',
            'NAT_' + floating_id: 'd5375e34-0e68-4543-86c2-a447ff3fef44',
            'NAT_' + floating_id + '_fixed_ip_address': '192.168.101.104',
            'NAT_' + floating_id + '_floating_ip_address': '172.16.100.4',
            'NAT_' + floating_id + '_network_id': network_id
        }

        f1.return_value = (200, {'status': 'FAILED'})

        self.agent._delete_nat(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data,
            floating=floating
        )

    #####
    # appendix.
        
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_general_dev')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    def test_create_general_dev_ex1(self, ct, ctn, cvl, cgd, utb, stb, gtb):
        global nwa_info_create_gdv, result_tnw, result_vln, result_cgd
        context = MagicMock()
        tenant_id = "844eb55f21e84a289e9c22098d387e5d"
        nwa_tenant_id = 'DC1_' + tenant_id

        nwa_info =  {
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
            "subnet": {
                "id": "df2a7b8a-e027-49ab-bf84-ade82a3c096c",
                "mask": "24",
                "netaddr": "192.168.100.0"
            },
            "tenant_id": "844eb55f21e84a289e9c22098d387e5d"
        }

        ct.return_value = (200, dict())
        ctn.return_value = (200, deepcopy(result_tnw))
        cvl.return_value = (200, deepcopy(result_vln))
        cgd.return_value = (200, deepcopy(result_cgd))
        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99": "device_id",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2": "net100",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_TYPE": "TenantFW",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_TenantFWName": "TFW8",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_ip_address": "192.168.100.1",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_0ed65870-9acb-48ce-8c0b-e803d527a9d2_mac_address": "fa:16:3e:97:4f:d4",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_TenantFWName": "TFW8",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_device_owner": "network:router_interface",
            "DEV_4b18c7ba-1370-410e-af4c-8578fbb3ab99_physical_network": "OpenStack/DC1/APP",
            "NWA_tenant_id": "DC02_844eb55f21e84a289e9c22098d387e5d",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2": "net100",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_network_id": "0ed65870-9acb-48ce-8c0b-e803d527a9d2",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_nwa_network_name": "LNW_BusinessVLAN_108",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_subnet": "192.168.100.0",
            "NW_0ed65870-9acb-48ce-8c0b-e803d527a9d2_subnet_id": "df2a7b8a-e027-49ab-bf84-ade82a3c096c",
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP": "physical_network",
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_FW_TFW4b18c7ba-1370-410e-af4c-8578fbb3ab99": "connected",
            "VLAN_0ed65870-9acb-48ce-8c0b-e803d527a9d2_OpenStack/DC1/APP_VlanID": "53"
        }

        self.agent.create_general_dev(
            context,
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_info=nwa_info
        )


    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.delete_tenant')
    def test_delete_tenant_fw_5656(self, dt, dtn, dvl, dtf, utb, stb, gtb):
        global nwa_data_one_gdev, result_dtf, result_dvl, result_dnw, nwa_info_delete_intf
        context = MagicMock()
        tenant_id = 'ade9e7b01c4e440297f0f8d8b9c1e65a'
        nwa_tenant_id = 'DC02_' + tenant_id

        nwa_info = {
            "device": {
                "id": "e493fd76-cd29-4dc5-acfc-33c7465be8eb",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "66d551f0-ebdf-4916-984f-529004e7050e",
                "name": "net101",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC02_ade9e7b01c4e440297f0f8d8b9c1e65a",
            "physical_network": "OpenStack/DC1/APP",
            "port": {
                "id": "38e3f024-b987-407d-af7b-d2302f46b819",
                "ip": "192.168.101.1",
                "mac": "fa:16:3e:03:42:ed"
            },
            "resource_group": "OpenStack/DC1/APP",
            "subnet": {
                "id": "faadb03c-bba1-41f3-adc6-ef9bf5face48",
                "mask": "24",
                "netaddr": "192.168.101.0"
            },
            "tenant_id": "ade9e7b01c4e440297f0f8d8b9c1e65a"
        }

        dt.return_value = (200, dict())
        dtn.return_value = (200, deepcopy(result_dnw))
        dvl.return_value = (200, deepcopy(result_dvl))
        dtf.return_value = (200, deepcopy(result_dtf))
        gtb.return_value = {
            "CreateTenant": "1",
            "CreateTenantNW": "1",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb": "device_id",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_66d551f0-ebdf-4916-984f-529004e7050e": "net101",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_66d551f0-ebdf-4916-984f-529004e7050e_TYPE": "TenantFW",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_66d551f0-ebdf-4916-984f-529004e7050e_TenantFWName": "TFW2",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_66d551f0-ebdf-4916-984f-529004e7050e_ip_address": "192.168.101.1",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_66d551f0-ebdf-4916-984f-529004e7050e_mac_address": "fa:16:3e:03:42:ed",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_85ec99c0-5223-455d-8f6a-8db57162cc1e": "net100",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_85ec99c0-5223-455d-8f6a-8db57162cc1e_TYPE": "TenantFW",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_85ec99c0-5223-455d-8f6a-8db57162cc1e_TenantFWName": "TFW2",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_85ec99c0-5223-455d-8f6a-8db57162cc1e_ip_address": "192.168.100.1",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_85ec99c0-5223-455d-8f6a-8db57162cc1e_mac_address": "fa:16:3e:ca:11:91",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_TenantFWName": "TFW2",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_device_owner": "network:router_interface",
            "DEV_e493fd76-cd29-4dc5-acfc-33c7465be8eb_physical_network": "OpenStack/DC1/APP",
            "NWA_tenant_id": "DC02_ade9e7b01c4e440297f0f8d8b9c1e65a",
            "NW_66d551f0-ebdf-4916-984f-529004e7050e": "net101",
            "NW_66d551f0-ebdf-4916-984f-529004e7050e_network_id": "66d551f0-ebdf-4916-984f-529004e7050e",
            "NW_66d551f0-ebdf-4916-984f-529004e7050e_nwa_network_name": "LNW_BusinessVLAN_103",
            "NW_66d551f0-ebdf-4916-984f-529004e7050e_subnet": "192.168.101.0",
            "NW_66d551f0-ebdf-4916-984f-529004e7050e_subnet_id": "faadb03c-bba1-41f3-adc6-ef9bf5face48",
            "NW_85ec99c0-5223-455d-8f6a-8db57162cc1e": "net100",
            "NW_85ec99c0-5223-455d-8f6a-8db57162cc1e_network_id": "85ec99c0-5223-455d-8f6a-8db57162cc1e",
            "NW_85ec99c0-5223-455d-8f6a-8db57162cc1e_nwa_network_name": "LNW_BusinessVLAN_102",
            "NW_85ec99c0-5223-455d-8f6a-8db57162cc1e_subnet": "192.168.100.0",
            "NW_85ec99c0-5223-455d-8f6a-8db57162cc1e_subnet_id": "6e1267f9-946b-41a6-a4dc-536e1b16f41c",
            "VLAN_66d551f0-ebdf-4916-984f-529004e7050e_OpenStack/DC1/APP": "physical_network",
            "VLAN_66d551f0-ebdf-4916-984f-529004e7050e_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
            "VLAN_66d551f0-ebdf-4916-984f-529004e7050e_OpenStack/DC1/APP_FW_TFWe493fd76-cd29-4dc5-acfc-33c7465be8eb": "connected",
            "VLAN_66d551f0-ebdf-4916-984f-529004e7050e_OpenStack/DC1/APP_VlanID": "38",
            "VLAN_85ec99c0-5223-455d-8f6a-8db57162cc1e_OpenStack/DC1/APP": "physical_network",
            "VLAN_85ec99c0-5223-455d-8f6a-8db57162cc1e_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
            "VLAN_85ec99c0-5223-455d-8f6a-8db57162cc1e_OpenStack/DC1/APP_FW_TFWe493fd76-cd29-4dc5-acfc-33c7465be8eb": "connected",
            "VLAN_85ec99c0-5223-455d-8f6a-8db57162cc1e_OpenStack/DC1/APP_VlanID": "36"
        }

        self.agent.delete_tenant_fw(
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
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TYPE": "TenantFW",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_TenantFWName": "TFW3",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_ip_address": "192.168.200.1",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_a94fd0fc-2282-4092-9485-b0f438b0f6c4_mac_address": "fa:16:3e:17:41:b4",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_device_owner": "network:router_interface",
        "DEV_843bc108-2f17-4be4-b9cb-44e00abe78d1_physical_network": "OpenStack/DC1/APP",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4": "pj1-net100",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_network_id": "a94fd0fc-2282-4092-9485-b0f438b0f6c4",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_nwa_network_name": "LNW_BusinessVLAN_103",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet": "192.168.200.0",
        "NW_a94fd0fc-2282-4092-9485-b0f438b0f6c4_subnet_id": "94fdaea5-33ae-4411-b6e0-71e4b099d470",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP": "physical_network",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_CreateVlan": "CreateVlan",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_FW_TFW843bc108-2f17-4be4-b9cb-44e00abe78d1": "connected",
        "VLAN_a94fd0fc-2282-4092-9485-b0f438b0f6c4_OpenStack/DC1/APP_VlanID": "37"
    }
    check_segment(network_id, nwa_data)

@patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent')
@patch('neutron.common.config')
@patch('sys.argv')
def test_main(f1, f2, f3):
    agent_main()

# 2015.10.19
class TestNECNWANeutronAgent2(unittest.TestCase):

    @patch('neutron.openstack.common.loopingcall.FixedIntervalLoopingCall')
    @patch('neutron.common.rpc.Connection.consume_in_threads')
    @patch('neutron.common.rpc.create_connection')
    @patch('neutron.agent.rpc.PluginReportStateAPI')
    @patch('neutron.common.rpc.get_client')
    def setUp(self, f1, f2, f3, f4, f5):
        self.config_parse()
        self.agent = NECNWANeutronAgent(10)
        self.agent.nwa_core_rpc = NECNWAPluginTenantBinding("dummy")

    def config_parse(self, conf=None, args=None):
        """Create the default configurations."""
        if args is None:
            args = []
        args += ['--config-file', etcdir('neutron.conf')]
        args += ['--config-file', etcdir('plugin.ini')]

        if conf is None:
            config.init(args=args)
        else:
            conf(args)

    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_fw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_vlan')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant_nw')
    @patch('neutron.plugins.necnwa.nwalib.client.NwaClient.create_tenant')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def _test_create_tenant_fw_succeed1(self, stb, ct, f2, f3, f4, f5, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_info ={
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "a7d0ba64-4bfb-44f7-9d36-85d3a565af68",
                "ip": "192.168.0.254",
                "mac": "fa:16:3e:fb:c0:a2"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        ct.return_value = (200, {'TenantName': u'DC1_844eb55f21e84a289e9c22098d387e5d'})
        f2.return_value = (200, deepcopy(result_tnw))
        f3.return_value = (200, deepcopy(result_vln))
        f4.return_value = (200, deepcopy(result_tfw))
        f5.return_value = {'status': 'SUCCEED'}
        stb.return_value = dict()

        # empty data.

        nwa_data = {
            "CreateTenant": "1",
            "CreateTenantNW": "1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_TYPE": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_TenantFWName": "TFW104",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_ip_address": "172.16.0.1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_mac_address": "fa:16:3e:84:04:c6",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW104",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_gateway",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_physical_network": "OpenStack/DC/APP",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TYPE": "GeneralDev",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_618",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_network_id": "3463df4c-9323-439d-b6af-2bc90df34f97",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_nwa_network_name": "LNW_PublicVLAN_619",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet": "172.16.0.0",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet_id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "connected",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_VlanID": "2",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_CreateVlan": "",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_FW_TFWd97e9b9b-8bf5-417f-a908-1d304b40aa73": "connected",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_VlanID": "3"
        }

        gtb.return_value = nwa_data

        rcode, body = self.agent._update_tenant_fw_connect(
            context,
            nwa_data=nwa_data, nwa_info=nwa_info,tenant_id=tenant_id, nwa_tenant_id=nwa_tenant_id
        )
        
        print ("body=%s" % json.dumps(
            body,
            indent=4,
            sort_keys=True
        ))

        rcode, body = self.agent._update_tenant_fw_disconnect(
            context,
            nwa_data=nwa_data, nwa_info=nwa_info,tenant_id=tenant_id, nwa_tenant_id=nwa_tenant_id
        )

        print ("body=%s" % json.dumps(
            body,
            indent=4,
            sort_keys=True
        ))


        # Delete TnantFW
        nwa_info2 = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_gateway"
            },
            "network": {
                "id": "3463df4c-9323-439d-b6af-2bc90df34f97",
                "name": "pub01",
                "vlan_type": "PublicVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "30c93e9c-77a4-44e1-bb1b-a67a829b6de2",
                "ip": "172.16.0.1",
                "mac": "fa:16:3e:84:04:c6"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
                "mask": "24",
                "netaddr": "172.16.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        rcode, body = self.agent._delete_tenant_fw(
            context,
            nwa_data=nwa_data, nwa_info=nwa_info2,tenant_id=tenant_id, nwa_tenant_id=nwa_tenant_id
        )

        print ("body=%s" % json.dumps(
            body,
            indent=4,
            sort_keys=True
        ))

        # Delete Vlan
        if not check_segment(nwa_info2['network']['id'], nwa_data):
            rcode, body = self.agent._delete_vlan(
                context,
                nwa_data=nwa_data, nwa_info=nwa_info2,tenant_id=tenant_id, nwa_tenant_id=nwa_tenant_id
            )
            print ("body=%s" % json.dumps(
                body,
                indent=4,
                sort_keys=True
            ))

    #### GeneralDev: None
    #### add Openstack/DC/HA1
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_general_dev_succeed1(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = None

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
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

        result = self.agent.create_general_dev(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)


    #### GeneralDev: Openstack/DC/HA1
    #### add Openstack/DC/HA1
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_general_dev_succeed2(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": ""
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

        result = self.agent.create_general_dev(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)


    #### GeneralDev: Openstack/DC/HA1
    #### add Openstack/DC/HA2
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_general_dev_succeed3(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": ""
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

        result = self.agent.create_general_dev(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)


    #### GeneralDev: Openstack/DC/HA1 x1
    #### del Openstack/DC/HA1
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_general_dev_succeed1(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "52",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
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

        result = self.agent.delete_general_dev(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)

    #### GeneralDev: Openstack/DC/HA1 x2
    #### del Openstack/DC/HA1
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_general_dev_succeed2(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21": "device_id",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.3",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:5c:3f:c2",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_device_owner": "compute:DC01_KVM02_ZONE02",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
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

        result = self.agent.delete_general_dev(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)

    #### GeneralDev: Openstack/DC/HA1 x1, Openstack/DC/HA2 x1
    #### del Openstack/DC/HA1
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_general_dev_succeed3(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21": "device_id",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2": "GeneralDev",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.3",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:5c:3f:c2",
            "DEV_18972752-f0f4-4cf7-b185-971ff6539d21_device_owner": "compute:DC01_KVM02_ZONE02",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "device_id",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1": "GeneralDev",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.1",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:76:ab:0e",
            "DEV_dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_device_owner": "network:dhcp",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA1_GD_VlanID": "49",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2_GD": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/HA2_GD_VlanID": "53",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "dhcp754b775b-af0d-5760-b6fc-64c290f9fc0b-0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
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

        result = self.agent.delete_general_dev(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: None
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### add Openstack/DC/APP gw
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_succeed1(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = None

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_gateway"
            },
            "network": {
                "id": "3463df4c-9323-439d-b6af-2bc90df34f97",
                "name": "pub01",
                "vlan_type": "PublicVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "30c93e9c-77a4-44e1-bb1b-a67a829b6de2",
                "ip": "172.16.0.1",
                "mac": "fa:16:3e:84:04:c6"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
                "mask": "24",
                "netaddr": "172.16.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.create_tenant_fw(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: None
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### add Openstack/DC/APP inf
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_succeed2(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = None

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "a7d0ba64-4bfb-44f7-9d36-85d3a565af68",
                "ip": "192.168.0.254",
                "mac": "fa:16:3e:fb:c0:a2"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.create_tenant_fw(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)


    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP gw,
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### add Openstack/DC/APP inf
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_succeed3(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_ip_address": "172.16.0.1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_mac_address": "fa:16:3e:84:04:c6",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_gateway",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_network_id": "3463df4c-9323-439d-b6af-2bc90df34f97",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet": "172.16.0.0",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet_id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_CreateVlan": "",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "a7d0ba64-4bfb-44f7-9d36-85d3a565af68",
                "ip": "192.168.0.254",
                "mac": "fa:16:3e:fb:c0:a2"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.create_tenant_fw(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP inf,
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### add Openstack/DC/APP gw
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_succeed4(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:fb:c0:a2",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_interface",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_gateway"
            },
            "network": {
                "id": "3463df4c-9323-439d-b6af-2bc90df34f97",
                "name": "pub01",
                "vlan_type": "PublicVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "30c93e9c-77a4-44e1-bb1b-a67a829b6de2",
                "ip": "172.16.0.1",
                "mac": "fa:16:3e:84:04:c6"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
                "mask": "24",
                "netaddr": "172.16.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.create_tenant_fw(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP inf(net01),
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### add Openstack/DC/APP inf(net02)
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_succeed5(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:fb:c0:a2",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_interface",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "4db537ed-5c39-4d2e-94b3-6b6ed62fcec2",
                "name": "net02",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "53f6befc-5ded-4354-9237-5ca15cef9519",
                "ip": "192.168.1.254",
                "mac": "fa:16:3e:c2:22:e1"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "d4c7e63e-e877-4c41-aae3-85cbc8e679e1",
                "mask": "24",
                "netaddr": "192.168.1.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.create_tenant_fw(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP inf(net01), Openstack/DC/APP inf(net02)
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### add Openstack/DC/APP gw
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_create_tenant_fw_succeed6(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:fb:c0:a2",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "net02",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_ip_address": "192.168.1.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_mac_address": "fa:16:3e:c2:22:e1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_interface",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "net02",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_network_id": "4db537ed-5c39-4d2e-94b3-6b6ed62fcec2",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_nwa_network_name": "LNW_BusinessVLAN_109",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_subnet": "192.168.1.0",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_subnet_id": "d4c7e63e-e877-4c41-aae3-85cbc8e679e1",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "physical_network",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_CreateVlan": "",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP_TFW_VlanID": "85",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_VlanID": "85"
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_gateway"
            },
            "network": {
                "id": "3463df4c-9323-439d-b6af-2bc90df34f97",
                "name": "pub01",
                "vlan_type": "PublicVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "30c93e9c-77a4-44e1-bb1b-a67a829b6de2",
                "ip": "172.16.0.1",
                "mac": "fa:16:3e:84:04:c6"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
                "mask": "24",
                "netaddr": "172.16.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.create_tenant_fw(context,
                                               tenant_id=tenant_id,
                                               nwa_tenant_id=nwa_tenant_id,
                                               nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP gw,
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### delete Openstack/DC/APP gw
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_tenant_fw_succeed1(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_TenantFWName": "TFW7",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_ip_address": "172.16.0.1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_mac_address": "fa:16:3e:84:04:c6",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW7",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_gateway",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_network_id": "3463df4c-9323-439d-b6af-2bc90df34f97",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_nwa_network_name": "LNW_PublicVLAN_101",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet": "172.16.0.0",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet_id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_CreateVlan": "",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW_VlanID": "73",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_VlanID": "73"
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_gateway"
            },
            "network": {
                "id": "3463df4c-9323-439d-b6af-2bc90df34f97",
                "name": "pub01",
                "vlan_type": "PublicVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "30c93e9c-77a4-44e1-bb1b-a67a829b6de2",
                "ip": "172.16.0.1",
                "mac": "fa:16:3e:84:04:c6"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
                "mask": "24",
                "netaddr": "172.16.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.delete_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP inf,
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### delete Openstack/DC/APP inf
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_tenant_fw_succeed2(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:fb:c0:a2",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_interface",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "a7d0ba64-4bfb-44f7-9d36-85d3a565af68",
                "ip": "192.168.0.254",
                "mac": "fa:16:3e:fb:c0:a2"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.delete_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP inf, Openstack/DC/APP gw,
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### delete Openstack/DC/APP inf
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_tenant_fw_succeed3(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:fb:c0:a2",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_ip_address": "172.16.0.1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_mac_address": "fa:16:3e:84:04:c6",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_gateway",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_106",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_network_id": "3463df4c-9323-439d-b6af-2bc90df34f97",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet": "172.16.0.0",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet_id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW_VlanID": "76",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "76",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_CreateVlan": "",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "a7d0ba64-4bfb-44f7-9d36-85d3a565af68",
                "ip": "192.168.0.254",
                "mac": "fa:16:3e:fb:c0:a2"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.delete_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP inf, Openstack/DC/APP gw,
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### delete Openstack/DC/APP gw
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_tenant_fw_succeed4(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:fb:c0:a2",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_ip_address": "172.16.0.1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_mac_address": "fa:16:3e:84:04:c6",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_gateway",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_106",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_network_id": "3463df4c-9323-439d-b6af-2bc90df34f97",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet": "172.16.0.0",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet_id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW_VlanID": "76",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "76",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_CreateVlan": "",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_VlanID": ""
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_gateway"
            },
            "network": {
                "id": "3463df4c-9323-439d-b6af-2bc90df34f97",
                "name": "pub01",
                "vlan_type": "PublicVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "30c93e9c-77a4-44e1-bb1b-a67a829b6de2",
                "ip": "172.16.0.1",
                "mac": "fa:16:3e:84:04:c6"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
                "mask": "24",
                "netaddr": "172.16.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.delete_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)

    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP inf(net01), Openstack/DC/APP inf(net02)
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### delete Openstack/DC/APP inf(net01)
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_tenant_fw_succeed5(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:fb:c0:a2",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "net02",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_ip_address": "192.168.1.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_mac_address": "fa:16:3e:c2:22:e1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_interface",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "net02",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_network_id": "4db537ed-5c39-4d2e-94b3-6b6ed62fcec2",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_nwa_network_name": "LNW_BusinessVLAN_109",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_subnet": "192.168.1.0",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_subnet_id": "d4c7e63e-e877-4c41-aae3-85cbc8e679e1",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "physical_network",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_CreateVlan": "",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP_TFW_VlanID": "85",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_VlanID": "85"
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "a7d0ba64-4bfb-44f7-9d36-85d3a565af68",
                "ip": "192.168.0.254",
                "mac": "fa:16:3e:fb:c0:a2"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.delete_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)


    #### GeneralDev: None
    #### TenantFW: Openstack/DC/APP inf(net01), Openstack/DC/APP inf(net02), Openstack/DC/APP gw
    #### Router: Rt1(d97e9b9b-8bf5-417f-a908-1d304b40aa73)
    #### delete Openstack/DC/APP inf(net01)
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.get_nwa_tenant_binding')
    @patch('neutron.plugins.necnwa.agent.necnwa_neutron_agent.NECNWANeutronAgent._update_tenant_binding')
    @patch('neutron.plugins.necnwa.necnwa_core_plugin.NECNWAPluginTenantBinding.set_nwa_tenant_binding')
    def test_delete_tenant_fw_succeed6(self, stb, utb, gtb):

        global result_tnw, result_vln, result_tfw, nwa_info_add_intf

        nwa_tenant_id = "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2"
        tenant_id = "5d9c51b1d6a34133bb735d4988b309c2"
        
        context = MagicMock()

        stb.return_value = dict()
        utb.return_value = {'status': 'SUCCEED'}

        gtb.return_value = {
            "CreateTenant": 1,
            "CreateTenantNW": 1,
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73": "device_id",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_ip_address": "192.168.0.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_mac_address": "fa:16:3e:fb:c0:a2",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_ip_address": "172.16.0.1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_3463df4c-9323-439d-b6af-2bc90df34f97_mac_address": "fa:16:3e:84:04:c6",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "net02",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP": "TenantFW",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_ip_address": "192.168.1.254",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_mac_address": "fa:16:3e:c2:22:e1",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_TenantFWName": "TFW12",
            "DEV_d97e9b9b-8bf5-417f-a908-1d304b40aa73_device_owner": "network:router_interface",
            "NWA_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "net01",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_network_id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_nwa_network_name": "LNW_BusinessVLAN_100",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet": "192.168.0.0",
            "NW_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_subnet_id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97": "pub01",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_network_id": "3463df4c-9323-439d-b6af-2bc90df34f97",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_nwa_network_name": "LNW_PublicVLAN_104",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet": "172.16.0.0",
            "NW_3463df4c-9323-439d-b6af-2bc90df34f97_subnet_id": "414c38d3-bf14-43ad-95f2-84f19f82aedb",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "net02",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_network_id": "4db537ed-5c39-4d2e-94b3-6b6ed62fcec2",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_nwa_network_name": "LNW_BusinessVLAN_109",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_subnet": "192.168.1.0",
            "NW_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_subnet_id": "d4c7e63e-e877-4c41-aae3-85cbc8e679e1",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_CreateVlan": "",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_OpenStack/DC/APP_TFW_VlanID": "100",
            "VLAN_0f17fa8f-40fe-43bd-8573-1a1e1bfb699d_VlanID": "",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_CreateVlan": "",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_OpenStack/DC/APP_TFW_VlanID": "95",
            "VLAN_3463df4c-9323-439d-b6af-2bc90df34f97_VlanID": "95",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2": "physical_network",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_CreateVlan": "",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP_TFW": "physical_network",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_OpenStack/DC/APP_TFW_VlanID": "85",
            "VLAN_4db537ed-5c39-4d2e-94b3-6b6ed62fcec2_VlanID": "85"
        }

        nwa_info = {
            "device": {
                "id": "d97e9b9b-8bf5-417f-a908-1d304b40aa73",
                "owner": "network:router_interface"
            },
            "network": {
                "id": "0f17fa8f-40fe-43bd-8573-1a1e1bfb699d",
                "name": "net01",
                "vlan_type": "BusinessVLAN"
            },
            "nwa_tenant_id": "DC_KILO3_5d9c51b1d6a34133bb735d4988b309c2",
            "physical_network": "OpenStack/DC/APP",
            "port": {
                "id": "a7d0ba64-4bfb-44f7-9d36-85d3a565af68",
                "ip": "192.168.0.254",
                "mac": "fa:16:3e:fb:c0:a2"
            },
            "resource_group_name": "OpenStack/DC/APP",
            "resource_group_name_nw": "OpenStack/DC/APP",
            "subnet": {
                "id": "3ba921f6-0788-40c8-b273-286b777d8cfe",
                "mask": "24",
                "netaddr": "192.168.0.0"
            },
            "tenant_id": "5d9c51b1d6a34133bb735d4988b309c2"
        }

        result = self.agent.delete_tenant_fw(context,
                                             tenant_id=tenant_id,
                                             nwa_tenant_id=nwa_tenant_id,
                                             nwa_info=nwa_info)
