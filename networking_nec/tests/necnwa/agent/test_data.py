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
