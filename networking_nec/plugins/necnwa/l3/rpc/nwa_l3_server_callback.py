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

from neutron.db import api as db_api
from neutron.extensions import l3
from neutron import manager
from neutron.plugins.common import constants as plugin_constants
from oslo_log import log as logging
import oslo_messaging

from networking_nec.plugins.necnwa.fwaas import db_api as fwaas_api

LOG = logging.getLogger(__name__)


class NwaL3ServerRpcCallback(object):

    target = oslo_messaging.Target(version='1.0')

    @property
    def l3plugin(self):
        if not hasattr(self, '_l3plugin'):
            self._l3plugin = manager.NeutronManager.get_service_plugins()[
                plugin_constants.L3_ROUTER_NAT]
        return self._l3plugin

    def create_fwaas_ids(self, context, tfw):
        session = db_api.get_session()
        result = fwaas_api.create_fwaas_ids(
            session, tfw
        )
        return {'result': result}

    def delete_fwaas_ids(self, context, tfw):
        session = db_api.get_session()
        result = fwaas_api.delete_fwaas_ids(
            session, tfw
        )
        return {'result': result}

    def get_fwaas_id(self, context, tfw, type_):
        session = db_api.get_session()
        id_ = fwaas_api.get_fwaas_id(
            session, tfw, type_
        )
        LOG.debug("tfw=%s, type=%s id=%d" % (tfw, type, id_))
        return {
            'id': id_,
            'result': False if id_ == 0 else True,
        }

    def clear_fwaas_id(self, context, tfw, type_, id_):
        session = db_api.get_session()
        ret = fwaas_api.clear_fwaas_id(
            session, tfw, type_, id_
        )
        return {
            'id': id_,
            'result': ret,
        }

    def blk_clear_fwaas_id(self, context, tfw, ids):
        session = db_api.get_session()
        ret = fwaas_api.blk_clear_fwaas_ids(
            session, tfw, ids
        )
        return {
            'result': ret
        }

    def update_floatingip_status(self, context, floatingip_id, status):
        '''Update operational status for a floating IP.'''
        with context.session.begin(subtransactions=True):
            LOG.debug('New status for floating IP %s: %s' %
                      (floatingip_id, status))
            try:
                self.l3plugin.update_floatingip_status(context,
                                                       floatingip_id,
                                                       status)
            except l3.FloatingIPNotFound:
                LOG.debug("Floating IP: %s no longer present.",
                          floatingip_id)
