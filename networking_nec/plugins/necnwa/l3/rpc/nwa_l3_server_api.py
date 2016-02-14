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

from neutron.common import rpc as n_rpc
from oslo_log import log as logging
import oslo_messaging

LOG = logging.getLogger(__name__)


class NwaL3ServerRpcApi(object):

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, topic):
        target = oslo_messaging.Target(topic=topic,
                                       version=self.BASE_RPC_API_VERSION)
        self.client = n_rpc.get_client(target)

    def create_fwaas_ids(self, context, tfw):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'create_fwaas_ids',
            tfw=tfw,
        )

    def delete_fwaas_ids(self, context, tfw):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'delete_fwaas_ids',
            tfw=tfw,
        )

    def get_fwaas_id(self, context, tfw, type_):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'get_fwaas_id',
            tfw=tfw,
            type=type_
        )

    def clear_fwaas_id(self, context, tfw, type_, id_):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'clear_fwaas_id',
            tfw=tfw,
            type=type_,
            id=id_
        )

    def blk_clear_fwaas_ids(self, context, tfw, ids):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'blk_clear_fwaas_ids',
            tfw=tfw,
            ids=ids
        )

    def update_floatingip_status(self, context, floatingip_id, status):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'update_floatingip_status',
            floatingip_id=floatingip_id,
            status=status
        )
