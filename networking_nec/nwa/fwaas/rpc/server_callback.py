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

from networking_nec.nwa.fwaas import db_api as nwa_fwaas_db

LOG = logging.getLogger(__name__)


class FWaaSServerCallback(object):

    BASE_RPC_API_VERSION = '1.0'

    def create_fwaas_ids(self, context, tfw):
        session = db_api.get_session()
        return {
            'result': nwa_fwaas_db.create_fwaas_ids(session, tfw)
        }

    def delete_fwaas_ids(self, context, tfw):
        session = db_api.get_session()
        return {
            'result': nwa_fwaas_db.delete_fwaas_ids(session, tfw)
        }

    def get_fwaas_id(self, context, tfw, type_):
        session = db_api.get_session()
        fwid = nwa_fwaas_db.get_fwaas_id(session, tfw, type_)
        return {
            'id': fwid,
            'result': False if fwid == 0 else True
        }

    def clear_fwaas_id(self, context, tfw, type_, id_):
        session = db_api.get_session()
        return {
            'id': id_,
            'result': nwa_fwaas_db.clear_fwaas_id(session, tfw, type_, id_)
        }

    def blk_clear_fwaas_ids(self, context, tfw, ids):
        session = db_api.get_session()
        return {
            'result': nwa_fwaas_db.blk_clear_fwaas_ids(session, tfw, ids)
        }
