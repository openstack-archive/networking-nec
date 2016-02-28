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

from mock import patch
from neutron.tests import base
from oslo_config import cfg

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

        wki = patch('networking_nec.nwa.nwalib.nwa_restclient.'
                    'NwaRestClient.workflowinstance').start()
        wki.return_value = (200, {'status': 'SUCCESS'})

        self.post = patch('networking_nec.nwa.nwalib.restclient.'
                          'RestClient.post').start()
        self.post.__name__ = 'post'
        self.post.return_value = (200, {'status': 'SUCCESS',
                                        'executionid': "01"})


class TestNwaClient(TestNwaClientBase):

    def test_setting_fw_policy(self):
        props = {'Property': 1}
        fw_name = 'TFW8'

        rd, rj = self.nwa.setting_fw_policy(TENANT_ID, fw_name, props)
        self.assertEqual(rd, 200)
        self.assertEqual(rj['status'], 'SUCCESS')


class TestUtNwaClientBase(base.BaseTestCase):
    '''Unit test for NwaClient '''

    def setUp(self):
        super(TestUtNwaClientBase, self).setUp()
        cfg.CONF.set_override('server_url', 'http://127.0.0.1:8080',
                              group='NWA')
        self.nwa = client.NwaClient(load_workflow_list=False)
        self.tenant_id = 'OpenT9004'
        self.call_wf = patch('networking_nec.nwa.nwalib.nwa_restclient.'
                             'NwaRestClient.call_workflow').start()


class TestUtNwaClient(TestUtNwaClientBase):

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


class TestSendQueueIsNotEmpty(base.BaseTestCase):
    def test_send_queue_is_not_empty(self):
        rb = client.send_queue_is_not_empty()
        self.assertFalse(rb)
