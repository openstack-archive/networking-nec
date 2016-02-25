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

import mock
from mock import patch
from neutron.tests import base
from oslo_config import cfg
import testscenarios

from networking_nec.nwa.nwalib import client

TENANT_ID = 'OpenT9004'

# create general dev
DC_RESOURCE_GROUP_POD1 = 'OpenStack/DC1/Common/Pod1Grp/Pod1'
DC_RESOURCE_GROUP_POD2 = 'OpenStack/DC1/Common/Pod2Grp/Pod2'

# create tenant nw
DC_RESOURCE_GROUP_APP1 = 'OpenStack/DC1/Common/App1Grp/App1'


class TestNwaClientBase(base.BaseTestCase):

    def setUp(self):
        super(TestNwaClientBase, self).setUp()
        host = '127.0.0.1'
        port = '12081'
        access_key_id = 'PzGIIoLbL7ttHFkDHqLguFz/7+VsVJbDmV0iLWAkJ0g='
        secret_access_key = 'nbvX65iujFoYomXTKROF9GKUN6L2rAM/sI+cvNdW7sw='

        self.nwa = client.NwaClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key
        )
        self.nwa.workflow_first_wait = 0


class TestNwaClient(TestNwaClientBase):

    def setUp(self):
        super(TestNwaClient, self).setUp()

        wki = patch('networking_nec.nwa.nwalib.nwa_restclient.'
                    'NwaRestClient.workflowinstance').start()
        wki.return_value = (200, {'status': 'SUCCESS'})

        self.post = patch('networking_nec.nwa.nwalib.restclient.'
                          'RestClient.post').start()
        self.post.__name__ = 'post'
        self.post.return_value = (200, {'status': 'SUCCESS',
                                        'executionid': "01"})

    def test_delete_nat(self):
        vlan_name = 'LNW_BusinessVLAN_100'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.5'
        global_ip = '10.0.1.5'
        fw_name = 'TFW77'
        rd, rj = self.nwa.delete_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_setting_nat(self):
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.6'
        global_ip = '10.0.1.6'
        fw_name = 'TFW78'
        rd, rj = self.nwa.setting_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_update_tenant_fw(self):
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        vlan_devaddr = '192.168.6.254'
        fw_name = 'TFW79'
        rd, rj = self.nwa.update_tenant_fw(
            TENANT_ID,
            fw_name, vlan_devaddr,
            vlan_name, vlan_type
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_setting_fw_policy(self):
        props = {'Property': 1}
        fw_name = 'TFW8'

        rd, rj = self.nwa.setting_fw_policy(TENANT_ID, fw_name, props)
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')


class TestNwaClientScenario(testscenarios.WithScenarios, TestNwaClientBase):

    scenarios = [
        ('test 1',
         {'operations': [
             ('delete', 'vlan-A'),
             ('delete', 'vlan-B'),
             ('delete', 'vlan-C'),
             ('delete', 'vlan-D'),
             ('delete', 'vlan-A')
         ]}),
        ('test 2',
         {'operations': [
             ('delete', 'vlan-1'),
             ('delete', 'vlan-2'),
             ('delete', 'vlan-3'),
             ('delete', 'vlan-1')
         ]}),
        # delete to "create"
        ('test 3',
         {'operations': [
             ('create', 'vlan-A'),
             ('delete', 'vlan-A'),
             ('create', 'vlan-A')]}),
        # don't delete if name is not same.
        ('test 4',
         {'operations': [
             ('create', 'vlan-1'),
             ('delete', 'vlan-2'),
             ('create', 'vlan-1')
         ]}),
        ('test 5',
         {'operations': [
             ('create', 'vlan-B'),
             ('delete', 'vlan-B'),
             ('create', 'vlan-C')
         ]}),
        ('test 6',
         {'operations': [
             ('create', 'vlan-X'),
             ('delete', 'vlan-X'),
             ('create', 'vlan-X'),
             ('delete', 'vlan-X')
         ]}),
        ('test 7',
         {'operations': [
             ('create', 'vlan-1'),
             ('create', 'vlan-2'),
             ('delete', 'vlan-1'),
             ('delete', 'vlan-2'),
             ('create', 'vlan-1'),
             ('delete', 'vlan-1')
         ]}),
        ('test 8',
         {'operations': [
             ('create', 'vlan-E'),
             ('delete', 'vlan-E'),
             ('delete', 'vlan-E'),
             ('delete', 'vlan-E')
         ]}),
    ]

    @patch('networking_nec.nwa.nwalib.nwa_restclient.NwaRestClient.'
           'workflowinstance')
    @patch('networking_nec.nwa.nwalib.restclient.RestClient.post')
    def test_general_dev(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        post.reset_mock()
        dcresgrp_name = 'Common/App/Pod3'
        for operation, vlan_name in self.operations:
            if operation == 'create':
                rd, rj = self.nwa.create_general_dev(
                    TENANT_ID, dcresgrp_name, vlan_name)
            else:
                rd, rj = self.nwa.delete_general_dev(
                    TENANT_ID, dcresgrp_name, vlan_name)
            self.assertEqual(rd, 200)
            self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, len(self.operations))


class TestUtNwaClient(base.BaseTestCase):
    '''Unit test for NwaClient '''

    def setUp(self):
        super(TestUtNwaClient, self).setUp()
        cfg.CONF.set_override('server_url', 'http://127.0.0.1:8080',
                              group='NWA')
        self.nwa = client.NwaClient(load_workflow_list=False)
        self.tenant_id = 'OpenT9004'
        self.call_wf = patch('networking_nec.nwa.nwalib.nwa_restclient.'
                             'NwaRestClient.call_workflow').start()

    def test_create_tenant_nw(self):
        self.nwa.create_tenant_nw(
            self.tenant_id,
            DC_RESOURCE_GROUP_APP1
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'CreateTenantNW',
            {'TenantID': self.tenant_id,
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_APP1,
             'CreateNW_OperationType': 'CreateTenantNW'})

    def test_delete_tenant_nw(self):
        self.nwa.delete_tenant_nw(self.tenant_id)
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'DeleteTenantNW',
            {'TenantID': self.tenant_id})

    def test_create_vlan(self):
        vlan_type = 'BusinessVLAN'
        ipaddr = '10.0.0.0'
        mask = 24
        open_nid = 'UUID'

        self.nwa.create_vlan(
            self.tenant_id, ipaddr, mask, vlan_type, open_nid
        )

        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'CreateVLAN',
            {'TenantID': self.tenant_id,
             'CreateNW_IPSubnetMask1': mask,
             'CreateNW_IPSubnetAddress1': ipaddr,
             'CreateNW_VlanType1': vlan_type,
             'CreateNW_VlanLogicalID1': open_nid})

    def test_delete_vlan(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        self.nwa.delete_vlan(
            self.tenant_id, vlan_name, vlan_type
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'DeleteVLAN',
            {'TenantID': self.tenant_id,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type})

    def test_create_tenant_fw(self):
        vlan_devaddr = '10.0.0.254'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        self.nwa.create_tenant_fw(
            self.tenant_id, DC_RESOURCE_GROUP_APP1,
            vlan_devaddr, vlan_name, vlan_type
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'CreateTenantFW',
            {'TenantID': self.tenant_id,
             'CreateNW_DeviceType1': 'TFW',
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_APP1,
             'CreateNW_Vlan_DeviceAddress1': vlan_devaddr,
             'CreateNW_VlanLogicalName1': vlan_name,
             'CreateNW_VlanType1': vlan_type})

    def test_update_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        self.nwa.update_tenant_fw(
            self.tenant_id,
            device_name, mock.sentinel.vlan_devaddr,
            vlan_name, vlan_type, 'connect'
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'UpdateTenantFW',
            {'TenantID': self.tenant_id,
             'ReconfigNW_DeviceName1': device_name,
             'ReconfigNW_DeviceType1': device_type,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_Vlan_DeviceAddress1': mock.sentinel.vlan_devaddr,
             'ReconfigNW_VlanType1': vlan_type,
             'ReconfigNW_Vlan_ConnectDevice1': 'connect'})

    def test_delete_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        self.nwa.delete_tenant_fw(
            self.tenant_id,
            device_name, device_type,
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'DeleteTenantFW',
            {'TenantID': self.tenant_id,
             'DeleteNW_DeviceName1': device_name,
             'DeleteNW_DeviceType1': device_type})

    def test_setting_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        self.nwa.setting_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'SettingNAT',
            {'TenantID': self.tenant_id,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_VlanType1': vlan_type,
             'ReconfigNW_DeviceType1': 'TFW',
             'ReconfigNW_DeviceName1': fw_name,
             'LocalIP': local_ip,
             'GlobalIP': global_ip})

    def test_setting_fw_policy(self):
        fw_name = 'TFW8'
        props = {'properties': [1]}
        self.nwa.setting_fw_policy_async(
            self.tenant_id, fw_name, props
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'SettingFWPolicy',
            {'TenantID': self.tenant_id,
             'DCResourceType': 'TFW_Policy',
             'DCResourceOperation': 'Setting',
             'DeviceInfo': {'Type': 'TFW', 'DeviceName': fw_name},
             'Property': props})

    def test_delete_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'

        self.nwa.delete_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )

        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'DeleteNAT',
            {'TenantID': self.tenant_id,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type,
             'DeleteNW_DeviceType1': 'TFW',
             'DeleteNW_DeviceName1': fw_name,
             'LocalIP': local_ip,
             'GlobalIP': global_ip})

    def test_create_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        self.nwa.create_general_dev(
            self.tenant_id, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-1'
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'CreateGeneralDev',
            {'TenantID': self.tenant_id,
             'CreateNW_DeviceType1': 'GeneralDev',
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_POD1,
             'CreateNW_VlanLogicalName1': vlan_name,
             'CreateNW_VlanType1': vlan_type,
             'CreateNW_PortType1': port_type,
             'CreateNW_VlanLogicalID1': 'vlan-logical-id-1'})

    def test_delete_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        self.nwa.delete_general_dev(
            self.tenant_id, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-2'
        )
        self.call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            'DeleteGeneralDev',
            {'TenantID': self.tenant_id,
             'DeleteNW_DeviceType1': 'GeneralDev',
             'DeleteNW_DCResourceGroupName': DC_RESOURCE_GROUP_POD1,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type,
             'DeleteNW_PortType1': port_type,
             'DeleteNW_VlanLogicalID1': 'vlan-logical-id-2'})


class TestSendQueueIsNotEmpty(base.BaseTestCase):
    def test_send_queue_is_not_empty(self):
        rb = client.send_queue_is_not_empty()
        self.assertFalse(rb)
