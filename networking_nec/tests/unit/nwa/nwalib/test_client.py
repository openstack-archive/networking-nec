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

from networking_nec.nwa.nwalib import client


class TestNwaClientBase(base.BaseTestCase):

    def setUp(self):
        super(TestNwaClientBase, self).setUp()
        host = '127.0.0.1'
        port = '12081'
        access_key_id = 'PzGIIoLbL7ttHFkDHqLguFz/7+VsVJbDmV0iLWAkJ0g='
        secret_access_key = 'nbvX65iujFoYomXTKROF9GKUN6L2rAM/sI+cvNdW7sw='

        self.nwa = client.NwaClient(
            host=host, port=port, access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            load_workflow_list=False
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
