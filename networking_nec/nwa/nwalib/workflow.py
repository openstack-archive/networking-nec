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

import re

import six


class NwaWorkflow(object):
    '''Workflow definition of NWA. '''
    _path_prefix = '/umf/workflow/'
    _nameid_initialized = False
    _nameid = {
        'CreateTenantNW': '40030001',
        'DeleteTenantNW': '40030016',
        'CreateVLAN': '40030002',
        'DeleteVLAN': '40030018',
        'CreateGeneralDev': '40030021',
        'DeleteGeneralDev': '40030022',
        'CreateTenantFW': '40030019',
        'UpdateTenantFW': '40030009',
        'DeleteTenantFW': '40030020',
        'SettingNAT': '40030005',
        'DeleteNAT': '40030011',
        'SettingFWPolicy': '40030081',
        'SettingLBPolicy': '40030091',
        'CreateTenantLB': '40030092',
        'UpdateTenantLB': '40030093',
        'DeleteTenantLB': '40030094',
    }
    _errno = {
        '1': 'Unknown parent node',
        '2': 'Already exists',
        '3': 'Resources are insufficient',
        '4': 'Unknown node',
        '5': 'Can not access the file',
        '6': 'Unknown parameters',
        '7': 'Undefined parameters',
        '8': 'Permission error',
        '9': 'It is not possible to remove because it is in use',
        '10': 'An error occurred while deleting the node',
        '11': 'Execution environment is invalid',
        '31': 'Specified IP subnet does not exist',
        '32': 'Specified IP address does not exist',
        '33': 'Can not allocate IP subnet to be paid out',
        '34': 'IP subnet will not exceed the threshold',
        '101': 'An unknown error has occurred',
        '102': 'An internal error has occurred',
        '103': 'Failed to connect to CMDB',
        '104': 'Out of memory',
        '105': 'An error occurred in the select process to the CMDB',
        '106': 'An error occurred in the update process to the CMDB',
        '107': 'An error occurred in the insert process to the CMDB',
        '108': 'Input parameter is invalid',
        '109': 'An error occurred in the file processing',
        '110': 'An error occurred in the delete process to the CMDB',
        '201': 'There is no free VLAN ID',
        '202': 'Exceeded the threshold of VLAN',
        '203': 'Exceeded the threshold ot Tenant equipment',
        '204': 'Resource group is not specified in the input',
        '205': 'Tenant-ID is not specified in the input',
        '206': 'Tenant-Network is already created',
        '207': 'There is no available devices',
        '208': 'IP address depletion for assignment of LB',
        '209': 'The device in the cluster group is 0 or 2 or more',
        '210': 'The device in the cluster group is 0',
        '211': 'There is no specified resource group',
        '212': 'There is no character "/" in the resource group name',
        '213': 'Tenant-FW is not specified one',
        '214': 'Tenant-FW is specified two or more',
        '215': 'Can not be extended because there is no PFS',
        '216': 'Logical NW name is not specified',
        '217': 'There is no Registered SSL-VPN equipment',
        '218': 'Tenant network is not yet created',
        '219': 'There is no free LoadBalancer',
        '220': 'Can not get the physical server uuid',
        '221': 'There is no deletion of VLAN',
        '222': 'Tenant ID in use is still exists',
        '223': 'Tenant-FW not found',
        '224': 'There is no specified device name',
        '225': 'Can not get the information of tenant vlan',
        '226': 'There is no specified logical NW',
        '227': 'Can not get the device information of the tenant in use',
        '228': 'For updated is in use, it could not be updated',
        '229': 'For deletion is in use, it could not be deleted',
        '230': 'Exceeded the threshold',
        '231': 'Exceeded the allocation possible number',
        '232': 'Exceeded the allocation range',
        '233': 'Authentication setting is incorrect',
        '234': 'Usable IP address range setting of is invalid',
        '235': 'IP address specified is invalid',
        '236': 'There is no available for allocation Tenant FW',
        '237': 'IP address depletion for assignment of FW',
        '238': 'IP address is invalid',
        '239': 'Can not set the number of records to zero',
        '240': 'The specification does not include a payout already IP subnet',
        '241': 'Not specified LogicalPort under the same controller or domain',
        '242': 'IP address depletion for assignment of SSL',
        '243': 'IP address is invalid',
        '244': 'The type of controller is invalid',
        '245': 'Device or VDOM name is invalid specified',
        '246': 'Exceeds the upper limit of naming convention',
        '251': 'In the same tenant, scenario there are still concurrent or '
               'reservation ID',
        '252': '(unused)',
        '253': 'The preceding scenario, can not be reserved',
        '254': 'Can not get the reserved id because of the preceding scenario',
        '298': 'Resources are insufficient',
        '299': 'Unknown error',
    }

    @staticmethod
    def init(name):
        pass                                    # pragma: no cover

    @staticmethod
    def path(name):
        """Returns path of workflow.

        :param name: The name of workflow.
        """
        return '%s%s/execute' % (NwaWorkflow._path_prefix,
                                 NwaWorkflow._nameid[name])

    @staticmethod
    def name(path):
        """Returns name of workflow.

        :param name: The name of workflow.
        """
        wid = path[len(NwaWorkflow._path_prefix):-len('/execute')]
        for (name, _id) in NwaWorkflow._nameid.items():
            if _id == wid:
                return name
        return None

    @staticmethod
    def strerror(errno):
        """Returns error name of errno.

        :param errno: The number of error.
        """
        return NwaWorkflow._errno.get(errno)

    @staticmethod
    def get_errno_from_resultdata(data):
        resultdata = data.get('resultdata')
        if resultdata:
            errmsg = resultdata.get('ErrorMessage')
            if isinstance(errmsg, six.string_types):
                m = re.search(r'ErrorNumber=(\d+)', errmsg)
                if m:
                    return m.group(1)
                m = re.search(r'ReservationErrorCode = (\d+)', errmsg, re.M)
                if m:
                    return m.group(1)
        return None

    @staticmethod
    def update_nameid(new_nameid):
        if NwaWorkflow._nameid_initialized:
            return
        if new_nameid:
            NwaWorkflow._nameid = new_nameid
            NwaWorkflow._nameid_initialized = True
