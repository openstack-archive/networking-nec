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

import testscenarios

from networking_nec.nwa.nwalib import workflow
from networking_nec.tests.unit.nwa.nwalib import test_client

TENANT_ID = 'OpenT9004'
DC_RESOURCE_GROUP_POD1 = 'OpenStack/DC1/Common/Pod1Grp/Pod1'
DC_RESOURCE_GROUP_APP1 = 'OpenStack/DC1/Common/App1Grp/App1'


class TestNwaClientL2Scenario(testscenarios.WithScenarios,
                              test_client.TestNwaClientBase):

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

    def test_general_dev(self):
        dcresgrp_name = 'Common/App/Pod3'
        for operation, vlan_name in self.operations:
            method = getattr(self.nwa.l2, '%s_general_dev' % operation)
            rd, rj = method(TENANT_ID, dcresgrp_name, vlan_name)
            self.assertEqual(rd, 200)
            self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, len(self.operations))


class TestNwaClientL2(test_client.TestNwaClientBase):

    def test_create_tenant_nw(self):
        rd, rj = self.nwa.l2.create_tenant_nw(TENANT_ID,
                                              DC_RESOURCE_GROUP_APP1)
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('CreateTenantNW'),
            {'TenantID': TENANT_ID,
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_APP1,
             'CreateNW_OperationType': 'CreateTenantNW'})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_delete_tenant_nw(self):
        rd, rj = self.nwa.l2.delete_tenant_nw(TENANT_ID)
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('DeleteTenantNW'),
            {'TenantID': TENANT_ID})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_create_vlan(self):
        vlan_type = 'BusinessVLAN'
        ipaddr = '10.0.0.0'
        mask = 24
        open_nid = 'UUID'

        rd, rj = self.nwa.l2.create_vlan(
            TENANT_ID, ipaddr, mask, vlan_type, open_nid
        )

        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('CreateVLAN'),
            {'TenantID': TENANT_ID,
             'CreateNW_IPSubnetMask1': mask,
             'CreateNW_IPSubnetAddress1': ipaddr,
             'CreateNW_VlanType1': vlan_type,
             'CreateNW_VlanLogicalID1': open_nid})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_create_vlan_without_open_nid(self):
        vlan_type = 'BusinessVLAN'
        ipaddr = '10.0.0.0'
        mask = 24

        rd, rj = self.nwa.l2.create_vlan(
            TENANT_ID, ipaddr, mask, vlan_type
        )

        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('CreateVLAN'),
            {'TenantID': TENANT_ID,
             'CreateNW_IPSubnetMask1': mask,
             'CreateNW_IPSubnetAddress1': ipaddr,
             'CreateNW_VlanType1': vlan_type})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_delete_vlan(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        rd, rj = self.nwa.l2.delete_vlan(
            TENANT_ID, vlan_name, vlan_type
        )
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('DeleteVLAN'),
            {'TenantID': TENANT_ID,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_create_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        rd, rj = self.nwa.l2.create_general_dev(
            TENANT_ID, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-1'
        )
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('CreateGeneralDev'),
            {'TenantID': TENANT_ID,
             'CreateNW_DeviceType1': 'GeneralDev',
             'CreateNW_DCResourceGroupName': DC_RESOURCE_GROUP_POD1,
             'CreateNW_VlanLogicalName1': vlan_name,
             'CreateNW_VlanType1': vlan_type,
             'CreateNW_PortType1': port_type,
             'CreateNW_VlanLogicalID1': 'vlan-logical-id-1'})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)

    def test_delete_general_dev(self):
        vlan_name = 'LNW_BusinessVLAN_49'
        vlan_type = 'BusinessVLAN'
        port_type = 'BM'
        rd, rj = self.nwa.l2.delete_general_dev(
            TENANT_ID, DC_RESOURCE_GROUP_POD1,
            vlan_name, vlan_type, port_type, 'vlan-logical-id-2'
        )
        self.post.assert_called_once_with(
            workflow.NwaWorkflow.path('DeleteGeneralDev'),
            {'TenantID': TENANT_ID,
             'DeleteNW_DeviceType1': 'GeneralDev',
             'DeleteNW_DCResourceGroupName': DC_RESOURCE_GROUP_POD1,
             'DeleteNW_VlanLogicalName1': vlan_name,
             'DeleteNW_VlanType1': vlan_type,
             'DeleteNW_PortType1': port_type,
             'DeleteNW_VlanLogicalID1': 'vlan-logical-id-2'})
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')
        self.assertEqual(self.post.call_count, 1)
