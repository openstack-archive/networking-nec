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
from oslo_log import log as logging
import oslo_messaging

from networking_nec.plugins.necnwa.fwaas import db_api as necnwa_api

LOG = logging.getLogger(__name__)


class FwaasServerRpcCallbacks(object):

    target = oslo_messaging.Target(version='1.0')

    def create_fwaas_ids(self, context, tfw):
        session = db_api.get_session()
        result = necnwa_api.create_fwaas_ids(
            session, tfw
        )
        return {'result': result}

    def delete_fwaas_ids(self, context, tfw):
        session = db_api.get_session()
        result = necnwa_api.delete_fwaas_ids(
            session, tfw
        )
        return {'result': result}

    def get_fwaas_id(self, context, tfw, type):
        session = db_api.get_session()
        id = necnwa_api.get_fwaas_id(
            session, tfw, type
        )
        LOG.debug("tfw=%s, type=%s id=%d" % (tfw, type, id))
        return {
            'id': id,
            'result': False if id == 0 else True,
        }

    def clear_fwaas_id(self, context, tfw, type, id):
        session = db_api.get_session()
        ret = necnwa_api.clear_fwaas_ids(
            session, tfw, type
        )
        return {
            'id': id,
            'result': ret,
        }

    def blk_clear_fwaas_ids(self, context, tfw, ids):
        session = db_api.get_session()
        ret = necnwa_api.blk_clear_fwaas_ids(
            session, tfw, ids
        )
        return {
            'result': ret,
        }
