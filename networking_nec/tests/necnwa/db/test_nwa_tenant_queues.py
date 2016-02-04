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

import os
import os.path

from networking_nec.plugins.necnwa.l2 import db_api as nwa_api

from neutron.common import config
from neutron import context

# ROOTDIR = os.path.dirname(__file__)
ROOTDIR = '/'
ETCDIR = os.path.join(ROOTDIR, 'etc/neutron')


def etcdir(*p):
    return os.path.join(ETCDIR, *p)

tenant1 = 'ffffffffff0000000000000000000001'
tenant2 = 'ffffffffff0000000000000000000002'
tenant3 = 'ffffffffff0000000000000000000003'


class TestNWAFunctions(object):

    def config_parse(self, conf=None, args=None):
        """Create the default configurations."""
        # neutron.conf.test includes rpc_backend which needs to be cleaned up
        if args is None:
            args = []
        args += ['--config-file', etcdir('neutron.conf')]
        if conf is None:
            config.init(args=args)
        else:
            conf(args)

    def test_001(self):
        self.config_parse()
        ctx = context.get_admin_context()
        print(nwa_api.add_nwa_tenant_queue(ctx.session, tenant1))
        print(nwa_api.add_nwa_tenant_queue(ctx.session, tenant2))

    """
    def test_002(self):
        self.config_parse()
        ctx = context.get_admin_context()
        print nwa_api.get_nwa_tenant_queue(ctx.session, tenant1)
        print nwa_api.get_nwa_tenant_queue(ctx.session, tenant2)
        print nwa_api.get_nwa_tenant_queue(ctx.session, tenant3)

    def test_003(self):
        self.config_parse()
        ctx = context.get_admin_context()
        print nwa_api.get_nwa_tenant_queues(ctx.session)

    def test_004(self):
        self.config_parse()
        ctx = context.get_admin_context()
        print nwa_api.del_nwa_tenant_queue(ctx.session, tenant1)
        print nwa_api.del_nwa_tenant_queue(ctx.session, tenant2)
        print nwa_api.del_nwa_tenant_queue(ctx.session, tenant3)

    def test_005(self):
        self.config_parse()
        ctx = context.get_admin_context()
        print nwa_api.get_nwa_tenant_queues(ctx.session)
    """
