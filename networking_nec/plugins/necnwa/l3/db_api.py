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

from sqlalchemy.orm import exc as sa_exc

from neutron.db import l3_db
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def get_tenant_id_by_router(session, router_id):
    rt_tid = None
    with session.begin(subtransactions=True):
        try:
            router = session.query(l3_db.Router).filter_by(id=router_id).one()
            rt_tid = router.tenant_id
        except sa_exc.NoResultFound:
            LOG.debug("router not found %s", router_id)

    LOG.debug("rt_tid=%s", rt_tid)
    return rt_tid
