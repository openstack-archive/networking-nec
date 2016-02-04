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

from neutron.tests import base

from networking_nec.plugins.necnwa.common.config import cfg
from networking_nec.plugins.necnwa.nwalib import client


CONFIG_FILE_CONTENTS = """
#
[OpenStack]
NeutronDBid = neutron
NeutronDBpw = password
NeutronDBtable = neutron

[NWA]
server_url = http://127.0.0.1:12081
access_key_id = 5g2ZMAdMwZ1gQqZagNqbJSrlopQUAUHILcP2nmxVs28=
secret_access_key = JE35Lup5CvI68lneFS4EtSGCh1DnG8dBtTRycPQ83QA=
resource_group_name = OpenStack/DC1/Common/App1Grp/App1
scenario_polling_timer =5
resource_group = [
   {
       "physical_network": "physnet1",
       "device_owner":"compute:None",
       "ResourceGroupName":"OpenStack/DC1/Common/Pod1Grp/Pod1"
   },
   {
       "physical_network": "physnet1",
       "device_owner":"network:dhcp",
       "ResourceGroupNliame":"OpenStack/DC1/Common/Pod1Grp/Pod1"
   },
   {
       "physical_network": "physnet2",
       "device_owner":"network:dhcp",
       "ResourceGroupName":"OpenStack/DC1/Common/Pod2Grp/Pod2"
   },
   {
       "physical_network": "physnet1",
       "device_owner":"compute:AZ1",
       "ResourceGroupName":"OpenStack/DC1/Common/Pod1Grp/Pod1"
   },
   {
       "physical_network": "physnet2",
       "device_owner":"compute:AZ2",
       "ResourceGroupName":"OpenStack/DC1/Common/Pod2Grp/Pod2"
   },
   {
       "physical_network": "physnet3",
       "device_owner":"network:router_gateway",
       "ResourceGroupName":"OpenStack/DC1/Common/App1"
   },
   {
       "physical_network": "physnet3",
       "device_owner":"network:router_interface",
       "ResourceGroupName":"OpenStack/DC1/Common/App1"
   },
   {
       "physical_network":"",
       "device_owner":"Stopper",
       "ResourceGroupName":"Stopper"
   }]
"""


class TestConfig(base.BaseTestCase):
    '''Unit test for NwaClient config. '''

    def test_nwa_config(self):
        cfgfile = self.get_temp_file_path('nwa.ini')
        with open(cfgfile, 'w') as f:
            f.write(CONFIG_FILE_CONTENTS)
        cfg.CONF(args=[], default_config_files=[cfgfile])
        nwa1 = client.NwaClient()
        self.assertEqual(nwa1.host, '127.0.0.1')
        self.assertEqual(nwa1.port, 12081)
        self.assertFalse(nwa1.use_ssl)
        self.assertEqual(nwa1.workflow_first_wait, 2)
        self.assertEqual(nwa1.workflow_wait_sleep, 5)
        self.assertEqual(nwa1.workflow_retry_count, 6)
        self.assertEqual(
            nwa1.auth(
                'Wed, 11 Feb 2015 17:24:51 GMT',
                '/umf/tenant/DC1'
            ),
            b'SharedKeyLite 5g2ZMAdMwZ1gQqZagNqbJSrlopQUAUHILcP2nmxVs28='
            b':mNd/AZJdMawfhJpVUT/lQcH7fPMz+4AocKti1jD1lCI='
        )
        headers = nwa1._make_headers('/')
        self.assertEqual(headers.get('Content-Type'), 'application/json')
        self.assertIsNotNone(headers.get('X-UMF-API-Version'))
        self.assertIsNotNone(headers.get('Authorization'))
        self.assertIsNotNone(headers.get('Date'))

        host = '1.2.3.4'
        port = 12345
        nwa2 = client.NwaClient(host=host, port=port, use_ssl=True)
        self.assertEqual(nwa2.host, host)
        self.assertEqual(nwa2.port, port)
        self.assertTrue(nwa2.use_ssl)
        auth = nwa2.define_auth_function('user', 'password')
        self.assertEqual(
            auth(
                'Wed, 11 Feb 2015 17:24:51 GMT',
                '/umf/tenant/DC1'
            ),
            b'SharedKeyLite user:d7ym8ADuKFoIphXojb1a36lvMb5KZK7fPYKz7RlDcpw='
        )
