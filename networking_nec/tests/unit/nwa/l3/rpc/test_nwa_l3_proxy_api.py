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

from neutron.tests import base

from networking_nec.nwa.l3.rpc.nwa_l3_proxy_api import NwaL3ProxyApi


class TestNwaL3ProxyApi(base.BaseTestCase):

    def setUp(self):
        self.context = mock.ANY
        self.tenant_id = 'T1'
        self.nwa_tenant_id = 'DC1T1'
        self.client = mock.MagicMock()
        self.proxy = NwaL3ProxyApi(self.client)
        super(TestNwaL3ProxyApi, self).setUp()

    def test_create_tenant_fw(self):
        cctxt = mock.Mock()
        self.client.prepare.return_value = cctxt
        nwa_info1 = [{'a': 1}, {'b': 2}, {'c': 3}]
        self.proxy.create_tenant_fw(self.context, self.tenant_id,
                                    self.nwa_tenant_id, nwa_info1)
        cctxt.cast.assert_called_with(
            self.context, 'create_tenant_fw',
            tenant_id=self.tenant_id,
            nwa_tenant_id=self.nwa_tenant_id,
            nwa_info=nwa_info1
        )

    def test_delete_tenant_fw(self):
        cctxt = mock.Mock()
        self.client.prepare.return_value = cctxt
        nwa_info2 = [{'a': 4}, {'b': 5}, {'c': 6}]
        self.proxy.delete_tenant_fw(self.context, self.tenant_id,
                                    self.nwa_tenant_id, nwa_info2)
        cctxt.cast.assert_called_with(
            self.context, 'delete_tenant_fw',
            tenant_id=self.tenant_id,
            nwa_tenant_id=self.nwa_tenant_id,
            nwa_info=nwa_info2
        )

    def test_setting_nat(self):
        cctxt = mock.Mock()
        self.client.prepare.return_value = cctxt
        floating1 = [{'x': 1}, {'y': 2}, {'z': 3}]
        self.proxy.setting_nat(self.context, self.tenant_id,
                               self.nwa_tenant_id, floating1)
        cctxt.cast.assert_called_with(
            self.context, 'setting_nat',
            tenant_id=self.tenant_id,
            nwa_tenant_id=self.nwa_tenant_id,
            floating=floating1
        )

    def test_delete_nat(self):
        cctxt = mock.Mock()
        self.client.prepare.return_value = cctxt
        floating2 = [{'x': 4}, {'y': 5}, {'z': 6}]
        self.proxy.delete_nat(self.context, self.tenant_id,
                              self.nwa_tenant_id, floating2)
        cctxt.cast.assert_called_with(
            self.context, 'delete_nat',
            tenant_id=self.tenant_id,
            nwa_tenant_id=self.nwa_tenant_id,
            floating=floating2
        )
