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

from neutron.plugins.common import constants as n_constants

from oslo_log import log as logging
LOG = logging.getLogger(__name__)


class NECNWALBaaSCallback(object):
    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, context, driver):
        self.context = context
        self.driver = driver

    def create_pool(self, context, pool, **kwargs):
        try:
            return self.driver.create_pool(context, pool)
        except:
            LOG.error("create_pool driver error.")
            return self.driver.update_status('pool', pool['id'], n_constants.ERROR)

    def update_pool(self, context, old_pool, pool, **kwargs):
        try:
            return self.driver.update_pool(context, old_pool, pool)
        except:
            LOG.error("update_pool driver error.")
            return self.driver.update_status('pool', pool['id'], n_constants.ERROR)

    def delete_pool(self, context, pool, **kwargs):
        try:
            return self.driver.delete_pool(context, pool)
        except:
            LOG.error("delete_pool( driver error.")
            return self.driver.update_status('pool', pool['id'], n_constants.ERROR)

    def create_member(self, context, member, **kwargs):
        try:
            return self.driver.create_member(context, member)
        except:
            LOG.error("create_member driver error.")
            return self.driver.update_status('member', member['id'], n_constants.ERROR)

    def update_member(self, context, member, **kwargs):
        try:
            return self.driver.update_member(context, member)
        except:
            LOG.error("update_member update_member driver error.")
            return self.driver.update_status('member', member['id'], n_constants.ERROR)

    def delete_member(self, context, member, **kwargs):
        try:
            return self.driver.delete_member(context, member)
        except:
            LOG.error("delete_member driver error.")
            return self.driver.update_status('member', member['id'], n_constants.ERROR)

    def create_vip(self, context, vip, **kwargs):
        try:
            return self.driver.create_vip(context, vip)
        except:
            LOG.error("create_vip driver error.")
            return self.driver.update_status('vip', vip['id'], n_constants.ERROR)

    def update_vip(self, context, vip, **kwargs):
        try:
            return self.driver.update_vip(context, vip)
        except:
            LOG.error("update_vip driver error.")
            return self.driver.update_status('vip', vip['id'], n_constants.ERROR)

    def delete_vip(self, context, vip, **kwargs):
        try:
            return self.driver.delete_vip(context, vip)
        except:
            LOG.error("delete_vip driver error.")
            return self.driver.update_status('vip', vip['id'], n_constants.ERROR)

    def create_pool_health_monitor(self, context, health_monitor, pool_id, **kwargs):
        try:
            return self.driver.create_pool_health_monitor(context, health_monitor, pool_id)
        except:
            LOG.error("create_pool_health_monitor driver error.")

    def update_pool_health_monitor(self, context, old_health_monitor,
                                   health_monitor, pool_id, **kwargs):
        try:
            return self.driver.update_pool_health_monitor(context,
                                                          old_health_monitor,
                                                          health_monitor, pool_id)
        except:
            LOG.error("update_pool_health_monitor driver error.")

    def delete_pool_health_monitor(self, context, health_monitor, pool_id,
                                   **kwargs):
        try:
            return self.driver.delete_pool_health_monitor(context, health_monitor, pool_id)
        except:
            LOG.error("delete_pool_health_monitor driver error.")
