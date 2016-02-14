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

from oslo_utils import timeutils

from networking_nec.plugins.necnwa.fwaas import models as fwmodels


def create_fwaas_ids(session, tfw_name, max_index=1024):
    try:
        recs = session.query(fwmodels.NWAFirewallIds).filter(
            fwmodels.NWAFirewallIds.tfw == tfw_name).all()

        if len(recs) > 0:
            return False

        with session.begin(subtransactions=True):
            recs = []
            for res_id in range(1, max_index + 1):
                recs.append(
                    fwmodels.NWAFirewallIds(
                        res_id, tfw_name, None, used=False
                    )
                )
            session.add_all(recs)

        return True
    except Exception:
        return False


def get_fwaas_id(session, tfw, type_):
    try:
        with session.begin(subtransactions=True):
            rec = session.query(fwmodels.NWAFirewallIds).filter(
                fwmodels.NWAFirewallIds.tfw == tfw
            ).filter(
                fwmodels.NWAFirewallIds.used == 0
            ).order_by(
                fwmodels.NWAFirewallIds.created_at
            ).order_by(
                fwmodels.NWAFirewallIds.res_id
            ).first()

            if not rec:
                return 0

            rec.type = type_
            rec.used = True
            rec.created_at = timeutils.utcnow()
            return rec.res_id
    except Exception:
        return 0


def blk_clear_fwaas_ids(session, tfw, ids):
    try:
        with session.begin(subtransactions=True):
            for res_id in ids:
                rec = session.query(fwmodels.NWAFirewallIds).filter(
                    fwmodels.NWAFirewallIds.tfw == tfw
                ).filter(
                    fwmodels.NWAFirewallIds.res_id == res_id
                ).one()

                rec.type = ''
                rec.used = False
                rec.created_at = timeutils.utcnow()

        return True

    except Exception:
        return False


def clear_fwaas_id(session, tfw, type_, res_id):
    try:
        with session.begin(subtransactions=True):
            rec = session.query(fwmodels.NWAFirewallIds).filter(
                fwmodels.NWAFirewallIds.tfw == tfw
            ).filter(
                fwmodels.NWAFirewallIds.type == type_
            ).filter(
                fwmodels.NWAFirewallIds.res_id == res_id
            ).one()

            rec.type = ''
            rec.used = False
            rec.created_at = timeutils.utcnow()
            return True
    except Exception:
        return False


def delete_fwaas_ids(session, tfw_name):
    try:
        with session.begin(subtransactions=True):
            recs = session.query(fwmodels.NWAFirewallIds).filter(
                fwmodels.NWAFirewallIds.tfw == tfw_name
            ).all()
            if not recs:
                return False
            query = (session.query(fwmodels.NWAFirewallIds).
                     filter_by(tfw=tfw_name))
            query.delete()
        return True

    except Exception:
        return False
