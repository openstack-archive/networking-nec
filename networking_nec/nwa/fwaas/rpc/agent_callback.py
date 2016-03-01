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

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class FWaaSAgentCallback(object):

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, driver):
        self.driver = driver

    def create_firewall(self, context, **kwargs):
        return self.driver.create_firewall(context, **kwargs)

    def update_firewall(self, context, **kwargs):
        return self.driver.update_firewall(context, **kwargs)

    def delete_firewall(self, context, **kwargs):
        return self.driver.delete_firewall(context, **kwargs)
