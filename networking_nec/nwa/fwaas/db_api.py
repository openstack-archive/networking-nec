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

import sqlalchemy as sa

from neutron.db import model_base
from neutron.db import models_v2
from oslo_utils import timeutils


class NWAFirewallIds(model_base.BASEV2, models_v2.HasId):
    __tablename__ = 'nwa_firewall_ids'

    tfw = sa.Column(sa.String(length=32), nullable=False)
    res_id = sa.Column(sa.Integer, nullable=False)
    type = sa.Column(sa.Enum('address_member', 'address_groups', 'services',
                             'policies', 'nats', 'routingss', '',
                             name='nwa_firewall_ids_type'), default='')
    used = sa.Column(sa.Boolean, nullable=False, default=False)
    created_at = sa.Column(sa.DateTime(), nullable=False)

    def __init__(self, res_id, tfw, type_=None, used=False):
        self.res_id = res_id
        self.tfw = tfw
        self.type = type_
        self.used = used
        self.created_at = timeutils.utcnow()


def create_fwaas_ids(session, tfw_name, max_index=1024):
    try:
        recs = session.query(NWAFirewallIds).filter(
            NWAFirewallIds.tfw == tfw_name).all()

        if recs:
            return False

        with session.begin(subtransactions=True):
            recs = []
            for res_id in range(1, max_index+1):
                recs.append(
                    NWAFirewallIds(
                        res_id, tfw_name, None, used=False
                    )
                )
            session.add_all(recs)
        return True
    except sa.orm.exc.NoResultFound:
        return False


def get_fwaas_id(session, tfw, type_):
    try:
        with session.begin(subtransactions=True):
            rec = session.query(NWAFirewallIds).filter(
                NWAFirewallIds.tfw == tfw
            ).filter(
                NWAFirewallIds.used == 0
            ).order_by(
                NWAFirewallIds.created_at
            ).order_by(
                NWAFirewallIds.res_id
            ).first()
            rec.type = type_
            rec.used = True
            rec.created_at = timeutils.utcnow()
            return rec.res_id
    except sa.orm.exc.NoResultFound:
        return False


def blk_clear_fwaas_ids(session, tfw, ids):
    try:
        with session.begin(subtransactions=True):
            for res_id in ids:
                rec = session.query(NWAFirewallIds).filter(
                    NWAFirewallIds.tfw == tfw
                ).filter(
                    NWAFirewallIds.type == type
                ).filter(
                    NWAFirewallIds.res_id == res_id
                ).one()
                rec.type = ''
                rec.used = False
                rec.created_at = timeutils.utcnow()
            return True
    except sa.orm.exc.NoResultFound:
        return False


def clear_fwaas_id(session, tfw, type_, res_id):
    try:
        with session.begin(subtransactions=True):
            rec = session.query(NWAFirewallIds).filter(
                NWAFirewallIds.tfw == tfw
            ).filter(
                NWAFirewallIds.type == type_
            ).filter(
                NWAFirewallIds.res_id == res_id
            ).one()
            rec.type = ''
            rec.used = False
            rec.created_at = timeutils.utcnow()
            return True
    except sa.orm.exc.NoResultFound:
        return False


def delete_fwaas_ids(session, tfw_name):
    try:
        with session.begin(subtransactions=True):
            recs = session.query(NWAFirewallIds).filter(
                NWAFirewallIds.tfw == tfw_name
            ).all()
            if not recs:
                return False
            query = (session.query(NWAFirewallIds).
                     filter_by(tfw=tfw_name))
            query.delete()
            return True
    except sa.orm.exc.NoResultFound:
        return False
