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
import sqlalchemy as sa

from networking_nec.plugins.necnwa.db import models as nmodels

# 0 is autoincrement
NWA_MIN_ID = 0
NWA_MAX_ID = 65535


def add_nwa_firewall_rule(session, rule):
    try:
        recs = session.query(nmodels.NWAFirewallRule).filter(
            nmodels.NWAFirewallRule.id == rule['id']).all()
        if len(recs) > 0:
            return False

        with session.begin(subtransactions=True):
            rec = nmodels.NWAFirewallRule(
                rule
            )
            session.add(rec)
        return True

    except sa.orm.exc.NoResultFound:
        return False


# def create_fwaas_ids(session, tfw_name, max_index=65535):
def create_fwaas_ids(session, tfw_name, max_index=1024):
    try:
        recs = session.query(nmodels.NWAFirewallIds).filter(
            nmodels.NWAFirewallIds.tfw == tfw_name).all()

        if len(recs) > 0:
            return False

        with session.begin(subtransactions=True):
            recs = []
            for res_id in range(1, max_index + 1):
                recs.append(
                    nmodels.NWAFirewallIds(
                        res_id, tfw_name, None, used=False
                    )
                )
            session.add_all(recs)

        return True
    except Exception:
        return False


def get_fwaas_id(session, tfw, type):
    try:
        with session.begin(subtransactions=True):
            rec = session.query(nmodels.NWAFirewallIds).filter(
                nmodels.NWAFirewallIds.tfw == tfw
            ).filter(
                nmodels.NWAFirewallIds.used == 0
            ).order_by(
                nmodels.NWAFirewallIds.created_at
            ).order_by(
                nmodels.NWAFirewallIds.res_id
            ).first()

            if not rec:
                return 0

            rec.type = type
            rec.used = True
            rec.created_at = timeutils.utcnow()
            return rec.res_id
    except Exception:
        return 0


def blk_clear_fwaas_id(session, tfw, ids):
    try:
        with session.begin(subtransactions=True):
            for res_id in ids:
                rec = session.query(nmodels.NWAFirewallIds).filter(
                    nmodels.NWAFirewallIds.tfw == tfw
                ).filter(
                    nmodels.NWAFirewallIds.type == type
                ).filter(
                    nmodels.NWAFirewallIds.res_id == res_id
                ).one()

                rec.type = ''
                rec.used = False
                rec.created_at = timeutils.utcnow()

        return True

    except Exception:
        return False


def clear_fwaas_id(session, tfw, type, res_id):
    try:
        with session.begin(subtransactions=True):
            rec = session.query(nmodels.NWAFirewallIds).filter(
                nmodels.NWAFirewallIds.tfw == tfw
            ).filter(
                nmodels.NWAFirewallIds.type == type
            ).filter(
                nmodels.NWAFirewallIds.res_id == res_id
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
            recs = session.query(nmodels.NWAFirewallIds).filter(
                nmodels.NWAFirewallIds.tfw == tfw_name
            ).all()
            if not recs:
                return False
            query = (session.query(nmodels.NWAFirewallIds).
                     filter_by(tfw=tfw_name))
            query.delete()
        return True

    except Exception:
        return False


def add_nwa_fwaas(session, tenant_id, fwaas_id, tfw_name):
    try:
        fwaas = session.query(nmodels.NWAFWaaS).filter(
            nmodels.NWAFWaaS.tenant_id == tenant_id).all()
        if len(fwaas) > 0:
            return False
        with session.begin(subtransactions=True):
            nwa = nmodels.NWAFWaaS(
                tenant_id,
                fwaas_id,
                tfw_name
            )
            session.add(nwa)
        return True
    except sa.orm.exc.NoResultFound:
        return False


def add_nwa_address_group(session, id, tenant_id, policy_id):
    try:
        address_group = session.query(nmodels.NWAFWaaSAddressGroup).filter(
            nmodels.NWAFWaaSAddressGroup.id == id).all()

        if len(address_group) > 0:
            return False

        with session.begin(subtransactions=True):
            rec = nmodels.NWAFWaaSAddressGroup(
                id, tenant_id, policy_id
            )
            session.add(rec)
        return True
    except sa.orm.exc.NoResultFound:
        return False


# id       ... address member id 1-65535
# type     ... type
# rule_id  ... rule uuid
# subnet   ... subnet address
# address  ... ip address
def add_nwa_address_member(session, type, policy_id, rule_id, subnet, address,
                           id=0):
    try:
        num = id if isinstance(id, int) else int(id)
        if(
                num < NWA_MIN_ID or
                NWA_MAX_ID < num
        ):
            return None

        member = session.query(nmodels.NWAFWaaSAddressMember).filter(
            nmodels.NWAFWaaSAddressMember.id == num).all()

        if len(member) > 0:
            return None

        with session.begin(subtransactions=True):
            rec = nmodels.NWAFWaaSAddressMember(
                type, policy_id, rule_id, subnet, address, num
            )
            session.add(rec)

        return {
            'id': str(rec.id),
            'policy_id': rec.policy_id,
            'rule_id': rec.rule_id,
            'type': rec.type,
            'subnet': rec.subnet
        }

    except sa.orm.exc.NoResultFound:
        return None
    except ValueError:
        return None


def add_nwa_fwaas_policy(session, tenant_id, rule, id=0):
    try:
        num = id if isinstance(id, int) else int(id)
        if(
                num < NWA_MIN_ID or
                NWA_MAX_ID < num
        ):
            return None

        member = session.query(nmodels.NWAFWaaSPolicy).filter(
            nmodels.NWAFWaaSPolicy.id == num).all()

        if len(member) > 0:
            return None

        with session.begin(subtransactions=True):
            rec = nmodels.NWAFWaaSPolicy(
                num, rule['firewall_policy_id'], rule['id']
            )
            session.add(rec)
            print(rec)

        return {
            'id': rec.id
        }

    except sa.orm.exc.NoResultFound:
        return None

    except ValueError:
        return None
