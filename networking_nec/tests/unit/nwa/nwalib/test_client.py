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
from mock import MagicMock
from mock import patch
from neutron.tests import base
import testscenarios

from networking_nec.nwa.nwalib import client
from networking_nec.nwa.nwalib import exceptions as nwa_exc
from networking_nec.nwa.nwalib import workflow

# the below code is required to load test scenarios.
# If a test class has 'scenarios' attribute,
# tests are multiplied depending on their 'scenarios' attribute.
# This can be assigned to 'load_tests' in any test module to make this
# automatically work across tests in the module.
# For more details, see testscenarios document.
load_tests = testscenarios.load_tests_apply_scenarios

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

    def get_vlan_info(self):
        self.business_vlan = self.public_vlan = None
        self.business_vlan_name = self.public_vlan_name = None
        rj = self.nwa.get_reserved_dc_resource(TENANT_ID)
        for node in rj.get('GroupNode'):
            node_type = node.get('Type')
            if node_type == 'BusinessVLAN':
                self.business_vlan = node
                self.business_vlan_name = node['VLAN'][0]['LogicalName']
            elif node_type == 'PublicVLAN':
                self.public_vlan = node
                self.public_vlan_name = node['VLAN'][0]['LogicalName']

    def test_workflow_kick_and_wait_raise(self):
        call_ne = MagicMock(side_effect=nwa_exc.NwaException(200, 'm1', None))
        call_ne.__name__ = 'POST'
        self.assertRaises(
            nwa_exc.NwaException,
            self.nwa.workflow_kick_and_wait, call_ne, None, None
        )

    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('networking_nec.nwa.nwalib.client.NwaClient.workflowinstance')
    def test_workflow_kick_and_wait(self, wki, lock):
        call = MagicMock()
        call.__name__ = 'POST'
        call.return_value = 200, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

        call.return_value = 200, {'executionid': 1}
        wki.return_value = 201, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 201)
        self.assertIsNone(rd)

        call.return_value = 200, {'executionid': '1'}
        wki.return_value = 202, None
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 202)
        self.assertIsNone(rd)

        wki.return_value = 201, {'status': 'RUNNING'}
        self.nwa.workflow_retry_count = 1
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 201)
        self.assertIsNone(rd)

        wki.side_effect = Exception
        hst, rd = self.nwa.workflow_kick_and_wait(call, None, None)
        self.assertEqual(hst, 200)
        self.assertIsNone(rd)

    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('networking_nec.nwa.nwalib.client.NwaClient.workflow_kick_and_wait')
    def test_call_workflow(self, wkaw, lock):
        call = MagicMock()
        call.__name__ = 'POST'

        wkaw.return_value = 200, '0'
        hst, rd = self.nwa.call_workflow('0', call, 'url_0', 'body_0')
        self.assertEqual(hst, 200)
        self.assertEqual(rd, '0')

        wkaw.return_value = 201, '1'
        hst, rd = self.nwa.call_workflow('1', call, 'url_1', 'body_1')
        self.assertEqual(hst, 201)
        self.assertEqual(rd, '1')

    def test_get_reserved_dc_resource(self):
        self.nwa.get_reserved_dc_resource(TENANT_ID)

    def test_get_tenant_resource(self):
        self.nwa.get_tenant_resource(TENANT_ID)

    def test_get_dc_resource_groups(self):
        self.nwa.get_dc_resource_groups('OpenStack/DC1/Common/Pod2Grp/Pod2')

    @patch('networking_nec.nwa.nwalib.client.NwaClient.get')
    def test_get_workflow_list(self, get):
        get.return_value = 209, None
        hst, rd = self.nwa.get_workflow_list()
        self.assertEqual(hst, 209)
        self.assertIsNone(rd)

        get.side_effect = Exception
        hst, rd = self.nwa.get_workflow_list()
        self.assertIsNone(hst)
        self.assertIsNone(rd)

    def test_stop_workflowinstance(self):
        self.nwa.stop_workflowinstance('id-0')

    def test_update_workflow_list(self):
        self.nwa.update_workflow_list()

    def test_wait_workflow_done(self):
        self.nwa.wait_workflow_done(MagicMock())

    def create_vlan(self):
        vlan_type = 'PublicVLAN'
        ipaddr = '172.16.0.0'
        mask = '28'
        rt = self.nwa.create_vlan(
            TENANT_ID,
            vlan_type, ipaddr, mask
        )
        return rt

    def delete_nat(self):
        vlan_name = 'LNW_BusinessVLAN_100'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.5'
        global_ip = '10.0.1.5'
        fw_name = 'TFW77'
        rt = self.nwa.delete_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        return rt

    def setting_nat(self):
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.6'
        global_ip = '10.0.1.6'
        fw_name = 'TFW78'
        rt = self.nwa.setting_nat(
            TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        return rt

    def update_tenant_fw(self):
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        vlan_devaddr = '192.168.6.254'
        fw_name = 'TFW79'
        rt = self.nwa.update_tenant_fw(
            TENANT_ID,
            fw_name, vlan_devaddr,
            vlan_name, vlan_type
        )
        return rt

    @patch('networking_nec.nwa.nwalib.client.NwaClient.workflowinstance')
    @patch('networking_nec.nwa.nwalib.restclient.RestClient.post')
    def test_delete_nat(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.delete_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.nwa.nwalib.client.NwaClient.workflowinstance')
    @patch('networking_nec.nwa.nwalib.restclient.RestClient.post')
    def test_setting_nat(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.setting_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.nwa.nwalib.client.NwaClient.workflowinstance')
    @patch('networking_nec.nwa.nwalib.restclient.RestClient.post')
    def test_update_tenant_fw(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.update_tenant_fw()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.nwa.nwalib.client.NwaClient.workflowinstance')
    @patch('networking_nec.nwa.nwalib.restclient.RestClient.post')
    def test_setting_fw_policy(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        props = {'Property': 1}
        fw_name = 'TFW8'

        rd, rj = self.nwa.setting_fw_policy(TENANT_ID, fw_name, props)
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')


class TestNwaClientScenario(TestNwaClientBase):

    def create_general_dev(self, vlan_name):
        dcresgrp_name = 'Common/App/Pod3'
        rd, rj = self.nwa.create_general_dev(
            TENANT_ID,
            dcresgrp_name, vlan_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        return rd, rj

    def delete_general_dev(self, vlan_name):
        dcresgrp_name = 'Common/App/Pod3'
        rd, rj = self.nwa.delete_general_dev(
            TENANT_ID,
            dcresgrp_name, vlan_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        return rd, rj

    scenarios = [
        ('test 1', {'count': 5, 'vlan_names': ['dA', 'dB', 'dC', 'dD', 'dA']}),
        ('test 2', {'count': 4, 'vlan_names': ['d1', 'd2', 'd3', 'd1']}),
        # delete to "create"
        ('test 3', {'count': 3, 'vlan_names': ['cA', 'dA', 'cA']}),
        # don't delete if name is not same.
        ('test 4', {'count': 3, 'vlan_names': ['c1', 'd2', 'c1']}),
        ('test 5', {'count': 3, 'vlan_names': ['cB', 'dB', 'cC']}),
        ('test 6', {'count': 4, 'vlan_names': ['cX', 'dX', 'cX', 'dX']}),
        ('test 7', {'count': 6,
                    'vlan_names': ['c1', 'c2', 'd1', 'd2', 'c1', 'd1']}),
        ('test 8', {'count': 4, 'vlan_names': ['cE', 'dE', 'dE', 'dE']}),
    ]

    @patch('networking_nec.nwa.nwalib.client.NwaClient.workflowinstance')
    @patch('networking_nec.nwa.nwalib.restclient.RestClient.post')
    def test_general_dev(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        post.reset_mock()
        for vlan_name in self.vlan_names:
            name = vlan_name[1:]
            if vlan_name.startswith('c'):
                self.assertEqual(self.create_general_dev(name)[0], 200)
            else:
                self.assertEqual(self.delete_general_dev(name)[0], 200)
        self.assertEqual(post.call_count, self.count)


class TestUtNwaClient(base.BaseTestCase):
    '''Unit test for NwaClient '''

    def setUp(self):
        super(TestUtNwaClient, self).setUp()
        self.nwa = client.NwaClient(load_workflow_list=False)
        self.tenant_id = 'OpenT9004'

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_create_tenant_nw(self, call_wf):
        self.nwa.create_tenant_nw(
            self.tenant_id,
            DC_RESOURCE_GROUP_APP1
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('CreateTenantNW'),
            {'TenantID': self.tenant_id,
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_APP1,
             'CreateNW_OperationType': 'CreateTenantNW'})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_delete_tenant_nw(self, call_wf):
        self.nwa.delete_tenant_nw(self.tenant_id)
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('DeleteTenantNW'),
            {'TenantID': self.tenant_id})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_create_vlan(self, call_wf):
        vlan_type = 'BusinessVLAN'
        ipaddr = '10.0.0.0'
        mask = 24
        open_nid = 'UUID'

        self.nwa.create_vlan(
            self.tenant_id, ipaddr, mask, vlan_type, open_nid
        )

        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('CreateVLAN'),
            {'TenantID': self.tenant_id,
             'CreateNW_IPSubnetMask1': mask,
             'CreateNW_IPSubnetAddress1': ipaddr,
             'CreateNW_VlanType1': vlan_type,
             'CreateNW_VlanLogicalID1': open_nid})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_delete_vlan(self, call_wf):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        self.nwa.delete_vlan(
            self.tenant_id, vlan_name, vlan_type
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('DeleteVLAN'),
            {'TenantID': self.tenant_id,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_create_tenant_fw(self, call_wf):
        vlan_devaddr = '10.0.0.254'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        self.nwa.create_tenant_fw(
            self.tenant_id, DC_RESOURCE_GROUP_APP1,
            vlan_devaddr, vlan_name, vlan_type
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('CreateTenantFW'),
            {'TenantID': self.tenant_id,
             'CreateNW_DeviceType1': 'TFW',
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_APP1,
             'CreateNW_Vlan_DeviceAddress1': vlan_devaddr,
             'CreateNW_VlanLogicalName1': vlan_name,
             'CreateNW_VlanType1': vlan_type})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_update_tenant_fw(self, call_wf):
        device_name = 'TFW0'
        device_type = 'TFW'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        self.nwa.update_tenant_fw(
            self.tenant_id,
            device_name, mock.sentinel.vlan_devaddr,
            vlan_name, vlan_type, 'connect'
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('UpdateTenantFW'),
            {'TenantID': self.tenant_id,
             'ReconfigNW_DeviceName1': device_name,
             'ReconfigNW_DeviceType1': device_type,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_Vlan_DeviceAddress1': mock.sentinel.vlan_devaddr,
             'ReconfigNW_VlanType1': vlan_type,
             'ReconfigNW_Vlan_ConnectDevice1': 'connect'})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_delete_tenant_fw(self, call_wf):
        device_name = 'TFW0'
        device_type = 'TFW'
        self.nwa.delete_tenant_fw(
            self.tenant_id,
            device_name, device_type,
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('DeleteTenantFW'),
            {'TenantID': self.tenant_id,
             'DeleteNW_DeviceName1': device_name,
             'DeleteNW_DeviceType1': device_type})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_setting_nat(self, call_wf):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        self.nwa.setting_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('SettingNAT'),
            {'TenantID': self.tenant_id,
             'ReconfigNW_VlanLogicalName1': vlan_name,
             'ReconfigNW_VlanType1': vlan_type,
             'ReconfigNW_DeviceType1': 'TFW',
             'ReconfigNW_DeviceName1': fw_name,
             'LocalIP': local_ip,
             'GlobalIP': global_ip})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_setting_fw_policy(self, call_wf):
        fw_name = 'TFW8'
        props = {'properties': [1]}
        self.nwa.setting_fw_policy_async(
            self.tenant_id, fw_name, props
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('SettingFWPolicy'),
            {'TenantID': self.tenant_id,
             'DCResourceType': 'TFW_Policy',
             'DCResourceOperation': 'Setting',
             'DeviceInfo': {'Type': 'TFW', 'DeviceName': fw_name},
             'Property': props})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_delete_nat(self, call_wf):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'

        self.nwa.delete_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )

        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('DeleteNAT'),
            {'TenantID': self.tenant_id,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type,
             'DeleteNW_DeviceType1': 'TFW',
             'DeleteNW_DeviceName1': fw_name,
             'LocalIP': local_ip,
             'GlobalIP': global_ip})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_create_general_dev(self, call_wf):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        self.nwa.create_general_dev(
            self.tenant_id, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-1'
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('CreateGeneralDev'),
            {'TenantID': self.tenant_id,
             'CreateNW_DeviceType1': 'GeneralDev',
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_POD1,
             'CreateNW_VlanLogicalName1': vlan_name,
             'CreateNW_VlanType1': vlan_type,
             'CreateNW_PortType1': port_type,
             'CreateNW_VlanLogicalID1': 'vlan-logical-id-1'})

    @patch('networking_nec.nwa.nwalib.client.NwaClient.call_workflow')
    def test_delete_general_dev(self, call_wf):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        self.nwa.delete_general_dev(
            self.tenant_id, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-2'
        )
        call_wf.assert_called_once_with(
            self.tenant_id,
            self.nwa.post,
            workflow.NwaWorkflow.path('DeleteGeneralDev'),
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
