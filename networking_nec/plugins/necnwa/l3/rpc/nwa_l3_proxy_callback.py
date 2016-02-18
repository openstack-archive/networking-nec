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

from oslo_log import helpers
from oslo_log import log as logging
import oslo_messaging

LOG = logging.getLogger(__name__)


class NwaL3ProxyCallback(object):

    target = oslo_messaging.Target(version='1.0')

    def __init__(self, context, agent):
        self.context = context
        self.agent = agent

    @helpers.log_method_call
    def create_tenant_fw(self, context, **kwargs):
        return self.agent.create_tenant_fw(context, **kwargs)

    @helpers.log_method_call
    def delete_tenant_fw(self, context, **kwargs):
        return self.agent.delete_tenant_fw(context, **kwargs)

    @helpers.log_method_call
    def setting_nat(self, context, **kwargs):
        return self.agent.setting_nat(context, **kwargs)

    @helpers.log_method_call
    def delete_nat(self, context, **kwargs):
        return self.agent.delete_nat(context, **kwargs)
