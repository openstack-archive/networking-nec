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

from mock import MagicMock
from mock import patch

from neutron.tests import base

from networking_nec.plugins.necnwa.nwalib import client
from networking_nec.plugins.necnwa.nwalib import exceptions as nwa_exc
from networking_nec.plugins.necnwa.nwalib import semaphore as nwa_sem
from networking_nec.plugins.necnwa.nwalib import workflow

TENANT_ID = 'OpenT9004'
CONTEXT = MagicMock()

# create general dev
DC_RESOURCE_GROUP_POD1 = 'OpenStack/DC1/Common/Pod1Grp/Pod1'
DC_RESOURCE_GROUP_POD2 = 'OpenStack/DC1/Common/Pod2Grp/Pod2'

# create tenant nw
DC_RESOURCE_GROUP_APP1 = 'OpenStack/DC1/Common/App1Grp/App1'

RESULTS = {}


def ok1(ctx, http_status, rj, *args, **kwargs):
    RESULTS['success'] = {
        'context': ctx,
        'http_status': http_status,
        'result': rj
    }


def ng1(ctx, http_status, rj, *args, **kwargs):
    RESULTS['failure'] = {
        'context': ctx,
        'http_status': http_status,
        'result': rj
    }
    if kwargs.get('exception', None):
        RESULTS['failure']['exception'] = kwargs['exception']


def init_async():
    global RESULTS
    RESULTS = {}


class TestNwaClient(base.BaseTestCase):
    '''Test code for Nwa Client '''

    def setUp(self):
        super(TestNwaClient, self).setUp()
        host = '127.0.0.1'
        port = '12081'
        access_key_id = 'PzGIIoLbL7ttHFkDHqLguFz/7+VsVJbDmV0iLWAkJ0g='
        secret_access_key = 'nbvX65iujFoYomXTKROF9GKUN6L2rAM/sI+cvNdW7sw='

        self.nwa = client.NwaClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key
        )
        self.nwa2 = client.NwaClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key
        )
        self.nwa.workflow_first_wait = 0
        self.nwa2.workflow_first_wait = 0

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
        # print json.dumps(self.business_vlan, indent=4, sort_keys=True)

    def test_workflow_kick_and_wait_raise(self):
        call_ne = MagicMock(side_effect=nwa_exc.NwaException(200, 'm1', None))
        call_ne.__name__ = 'POST'
        self.assertRaises(
            nwa_exc.NwaException,
            self.nwa.workflow_kick_and_wait, call_ne, None, None
        )

    @patch('eventlet.semaphore.Semaphore.locked')
    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
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
    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflow_kick_and_wait')
    def test_call_workflow(self, wkaw, lock):
        call = MagicMock()
        call.__name__ = 'POST'

        def mkreq(tid, b, nocache=None):
            return call, 'url_' + str(tid), 'body_' + str(b)

        wkaw.return_value = 200, '0'
        hst, rd = self.nwa.call_workflow(mkreq, '0', '0')
        self.assertEqual(hst, 200)
        self.assertEqual(rd, '0')

        wkaw.return_value = 201, '1'
        hst, rd = self.nwa.call_workflow(mkreq, '1', '1')
        self.assertEqual(hst, 201)
        self.assertEqual(rd, '1')

        # 'nocache' in kwargs
        wkaw.return_value = 202, '2'
        hst, rd = self.nwa.call_workflow(mkreq, '2', '2', nocache=True)
        self.assertEqual(hst, 202)
        self.assertEqual(rd, '2')

        # 'nocache' is hook function
        wkaw.return_value = 203, '3'

        def hook(self, *args, **kwargs):
            self.assertEqual(args[0].__name__, 'POST')
            self.assertEqual(args[1], 'url_3')
            self.assertEqual(args[2], 'body_3')
            self.assertEqual(args[3], 203)
            self.assertEqual(args[4], '3')

        s = nwa_sem.Semaphore()
        s.hook = hook
        hst, rd = self.nwa.call_workflow(mkreq, '3', '3', nocache=s.hook)
        self.assertEqual(hst, 203)
        self.assertEqual(rd, '3')

    def test_get_reserved_dc_resource(self):
        self.nwa.get_reserved_dc_resource(TENANT_ID)

    def test_get_tenant_resource(self):
        self.nwa.get_tenant_resource(TENANT_ID)

    def test_get_dc_resource_groups(self):
        self.nwa.get_dc_resource_groups('OpenStack/DC1/Common/Pod2Grp/Pod2')

    @patch('networking_nec.plugins.necnwa.nwalib.client.NwaClient.get')
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
        init_async()
        vlan_type = 'PublicVLAN'
        ipaddr = '172.16.0.0'
        mask = '28'
        rt = self.nwa.create_vlan(
            ok1, ng1, CONTEXT, TENANT_ID,
            vlan_type, ipaddr, mask
        )
        return rt

    def delete_nat(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_100'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.5'
        global_ip = '10.0.1.5'
        fw_name = 'TFW77'
        rt = self.nwa.delete_nat(
            ok1, ng1, CONTEXT, TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        return rt

    def setting_nat(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        local_ip = '172.16.1.6'
        global_ip = '10.0.1.6'
        fw_name = 'TFW78'
        rt = self.nwa.setting_nat(
            ok1, ng1, CONTEXT, TENANT_ID,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        return rt

    def update_tenant_fw(self):
        init_async()
        vlan_name = 'LNW_BusinessVLAN_101'
        vlan_type = 'BusinessVLAN'
        vlan_devaddr = '192.168.6.254'
        fw_name = 'TFW79'
        rt = self.nwa.update_tenant_fw(
            ok1, ng1, CONTEXT, TENANT_ID,
            fw_name, vlan_devaddr,
            vlan_name, vlan_type
        )
        return rt

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.post')
    def test_delete_nat(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.delete_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.delete_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.delete_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.post')
    def test_setting_nat(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.setting_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.setting_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.setting_nat()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.post')
    def test_update_tenant_fw(self, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        rd, rj = self.update_tenant_fw()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in428 history
        rd, rj = self.update_tenant_fw()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

        post.reset_mock()                 # check no in history
        rd, rj = self.update_tenant_fw()
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(post.call_count, 1)

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.call_workflow')
    def test_setting_fw_policy(self, cawk):
        cawk.return_value = (200, {'status': 'SUCCESS'})
        props = {'Property': 1}
        fw_name = 'TFW8'
        rd, rj = self.nwa.setting_fw_policy(TENANT_ID, fw_name, props)
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')

        cawk.return_value = (500, None)
        rd, rj = self.nwa.setting_fw_policy(TENANT_ID, fw_name, props)
        self.assertEqual(rd, 500)

    def create_general_dev(self, vlan_name):
        init_async()
        dcresgrp_name = 'Common/App/Pod3'
        rd, rj = self.nwa.create_general_dev(
            ok1, ng1, CONTEXT, TENANT_ID,
            dcresgrp_name, vlan_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        return rd, rj

    def delete_general_dev(self, vlan_name):
        init_async()
        dcresgrp_name = 'Common/App/Pod3'
        rd, rj = self.nwa.delete_general_dev(
            ok1, ng1, CONTEXT, TENANT_ID,
            dcresgrp_name, vlan_name
        )
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        return rd, rj

    def test_general_dev(self):
        params = [
            (5, ['dA', 'dB', 'dC', 'dD', 'dA']),
            (4, ['d1', 'd2', 'd3', 'd1']),
            (3, ['cA', 'dA', 'cA']),      # delete to "create"
            (3, ['c1', 'd2', 'c1']),      # don't delete if name is not same.
            (3, ['cB', 'dB', 'cC']),
            (4, ['cX', 'dX', 'cX', 'dX']),
            (6, ['c1', 'c2', 'd1', 'd2', 'c1', 'd1']),
            (4, ['cE', 'dE', 'dE', 'dE']),
        ]
        for count, vlan_names in params:
            yield self.check_general_dev, count, vlan_names

    @patch('networking_nec.plugins.necnwa.nwalib'
           '.client.NwaClient.workflowinstance')
    @patch('networking_nec.plugins.necnwa.nwalib.restclient.RestClient.post')
    def check_general_dev(self, count, vlan_names, post, wki):
        post.__name__ = 'post'
        post.return_value = (200, {'status': 'SUCCESS', 'executionid': "01"})
        wki.return_value = (200, {'status': 'SUCCESS'})

        post.reset_mock()
        for vlan_name in vlan_names:
            name = vlan_name[1:]
            if vlan_name.startswith('c'):
                self.assertEqual(self.create_general_dev(name)[0], 200)
            else:
                self.assertEqual(self.delete_general_dev(name)[0], 200)
        self.assertEqual(post.call_count, count)


class TestUtNwaClient(base.BaseTestCase):
    '''Unit test for NwaClient '''

    def setUp(self):
        super(TestUtNwaClient, self).setUp()
        self.nwa = client.NwaClient(load_workflow_list=False)
        self.tenant_id = 'OpenT9004'

    def test__create_tenant_nw(self):
        method, url, body = self.nwa._create_tenant_nw(
            self.tenant_id,
            DC_RESOURCE_GROUP_APP1
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('CreateTenantNW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         DC_RESOURCE_GROUP_APP1)
        self.assertEqual(body['CreateNW_OperationType'], 'CreateTenantNW')

    def test__delete_tenant_nw(self):
        method, url, body = self.nwa._delete_tenant_nw(
            self.tenant_id
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteTenantNW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)

    def test__create_vlan(self):
        vlan_type = 'BusinessVLAN'
        ipaddr = '10.0.0.0'
        mask = 24
        open_nid = 'UUID'
        method, url, body = self.nwa._create_vlan(
            self.tenant_id, vlan_type, ipaddr, mask, open_nid
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('CreateVLAN'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_IPSubnetMask1'], mask)
        self.assertEqual(body['CreateNW_IPSubnetAddress1'], ipaddr)
        self.assertEqual(body['CreateNW_VlanType1'], vlan_type)
        self.assertEqual(body['CreateNW_VlanLogicalID1'], open_nid)

    def test__delete_vlan(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        method, url, body = self.nwa._delete_vlan(
            self.tenant_id, vlan_name, vlan_type
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteVLAN'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['DeleteNW_VlanType1'], vlan_type)

    def test__create_tenant_fw(self):
        vlan_devaddr = '10.0.0.254'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        method, url, body = self.nwa._create_tenant_fw(
            self.tenant_id, DC_RESOURCE_GROUP_APP1,
            vlan_devaddr, vlan_name, vlan_type
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('CreateTenantFW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         DC_RESOURCE_GROUP_APP1)
        self.assertEqual(body['CreateNW_Vlan_DeviceAddress1'], vlan_devaddr)
        self.assertEqual(body['CreateNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['CreateNW_VlanType1'], vlan_type)

    def test__update_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        method, url, body = self.nwa._update_tenant_fw(
            self.tenant_id,
            device_name, device_type,
            vlan_name, vlan_type, 'connect'
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('UpdateTenantFW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['ReconfigNW_DeviceName1'], device_name)
        self.assertEqual(body['ReconfigNW_DeviceType1'], device_type)
        self.assertEqual(body['ReconfigNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['ReconfigNW_VlanType1'], vlan_type)

    def test__delete_tenant_fw(self):
        device_name = 'TFW0'
        device_type = 'TFW'
        method, url, body = self.nwa._delete_tenant_fw(
            self.tenant_id,
            device_name, device_type,
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteTenantFW'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_DeviceName1'], device_name)
        self.assertEqual(body['DeleteNW_DeviceType1'], device_type)

    def test__setting_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        method, url, body = self.nwa._setting_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('SettingNAT'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['ReconfigNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['ReconfigNW_VlanType1'], vlan_type)
        self.assertEqual(body['LocalIP'], local_ip)
        self.assertEqual(body['GlobalIP'], global_ip)

    def test__setting_fw_policy(self):
        fw_name = 'TFW8'
        props = {'properties': [1]}
        method, url, body = self.nwa._setting_fw_policy(
            self.tenant_id, fw_name, props
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('SettingFWPolicy'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DCResourceType'], 'TFW_Policy')
        self.assertEqual(body['DCResourceOperation'], 'Setting')
        self.assertIsInstance(body['DeviceInfo'], dict)
        self.assertEqual(body['Property'], props)
        di = body['DeviceInfo']
        self.assertEqual(di['DeviceName'], fw_name)
        self.assertEqual(di['Type'], 'TFW')

    def test__delete_nat(self):
        fw_name = 'TFW8'
        vlan_name = 'LNW_PublicVLAN_46'
        vlan_type = 'PublicVLAN'
        local_ip = '172.16.0.2'
        global_ip = '10.0.0.10'
        method, url, body = self.nwa._delete_nat(
            self.tenant_id,
            vlan_name, vlan_type, local_ip, global_ip, fw_name
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteNAT'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['DeleteNW_VlanType1'], vlan_type)
        self.assertEqual(body['LocalIP'], local_ip)
        self.assertEqual(body['GlobalIP'], global_ip)

    def test__create_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        method, url, body = self.nwa._create_general_dev(
            self.tenant_id, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-1'
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('CreateGeneralDev'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['CreateNW_DCResourceGroupName'],
                         DC_RESOURCE_GROUP_POD1)
        self.assertEqual(body['CreateNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['CreateNW_VlanType1'], vlan_type)
        self.assertEqual(body['CreateNW_PortType1'], port_type)

    def test__delete_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        method, url, body = self.nwa._delete_general_dev(
            self.tenant_id, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-2'
        )
        self.assertEqual(method, self.nwa.post)
        self.assertRegex(url, workflow.NwaWorkflow.path('DeleteGeneralDev'))
        self.assertIsInstance(body, dict)
        self.assertEqual(body['TenantID'], self.tenant_id)
        self.assertEqual(body['DeleteNW_DCResourceGroupName'],
                         DC_RESOURCE_GROUP_POD1)
        self.assertEqual(body['DeleteNW_VlanLogicalName1'], vlan_name)
        self.assertEqual(body['DeleteNW_VlanType1'], vlan_type)


class TestSendQueueIsNotEmpty(base.BaseTestCase):
    def test_send_queue_is_not_empty(self):
        rb = client.send_queue_is_not_empty()
        self.assertFalse(rb)
