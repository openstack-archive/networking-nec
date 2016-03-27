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

from neutron.plugins.ml2 import models as models_ml2
import sqlalchemy as sa
from sqlalchemy import and_

from networking_nec.nwa.l2 import models as nmodels


class NWATenantBinding(object):
    """Relation between OpenStack Tenant ID and NWA Tenant ID."""
    def __init__(self, tenant_id, nwa_tenant_id, value_json):
        self.tenant_id = tenant_id
        self.nwa_tenant_id = nwa_tenant_id
        self.value_json = value_json

    def __repr__(self):
        return "<TenantBinding(%s,%s,%s)>" % (
            self.tenant_id, self.nwa_tenant_id, self.value_json
        )


def add_nwa_tenant_binding(session, tenant_id, nwa_tenant_id, json_value):
    try:
        if not isinstance(json_value, dict):
            return False
        nwa = session.query(nmodels.NWATenantKeyValue).filter(
            nmodels.NWATenantKeyValue.tenant_id == tenant_id).all()
        if nwa:
            return False
        with session.begin(subtransactions=True):
            for json_key, json_value in json_value.items():
                item = nmodels.NWATenantKeyValue(tenant_id, nwa_tenant_id,
                                                 json_key, json_value)
                session.add(item)
        return True
    except sa.orm.exc.NoResultFound:
        return False


def convert_if_special_value(s):
    if s == 'True' or s == '1':
        return True
    if s == 'False' or s == '0':
        return False
    return s


def get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id):
    try:
        value_json = {
            nwa.json_key: convert_if_special_value(nwa.json_value)
            for nwa in session.query(nmodels.NWATenantKeyValue).filter(
                nmodels.NWATenantKeyValue.tenant_id == tenant_id).filter(
                    nmodels.NWATenantKeyValue.nwa_tenant_id ==
                    nwa_tenant_id).all()
        }
        if value_json:
            return NWATenantBinding(tenant_id, nwa_tenant_id, value_json)
        else:
            return None
    except sa.orm.exc.NoResultFound:
        return None


def set_nwa_tenant_binding(session, tenant_id, nwa_tenant_id, value_json):
    item = get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
    if not item:
        return False
    _json = item.value_json
    if not isinstance(_json, dict):
        return False
    if not isinstance(value_json, dict):
        return False
    with session.begin(subtransactions=True):
        for key, value in value_json.items():
            if key in _json:
                if value != _json[key]:
                    # update
                    item = session.query(nmodels.NWATenantKeyValue).filter(
                        and_(nmodels.NWATenantKeyValue.tenant_id == tenant_id,
                             nmodels.NWATenantKeyValue.json_key == key)).one()
                    item.json_value = value
            else:
                # insert
                # item = nmodels.NWATenantKeyValue(
                #        tenant_id, nwa_tenant_id, key, value)
                # session.add(item)
                insert = ("INSERT INTO nwa_tenant_key_value (tenant_id,"
                          "nwa_tenant_id,json_key,json_value) "
                          " VALUES (\'%s\',\'%s\',\'%s\',\'%s\') "
                          "ON DUPLICATE KEY UPDATE "
                          " json_value=\'%s\'" % (tenant_id, nwa_tenant_id,
                                                  key, value, value))
                session.execute(insert)
        for key, value in _json.items():
            if key not in value_json:
                # delete
                item = session.query(nmodels.NWATenantKeyValue).filter(
                    and_(nmodels.NWATenantKeyValue.tenant_id == tenant_id,
                         nmodels.NWATenantKeyValue.json_key == key)).one()
                session.delete(item)
    return True


def del_nwa_tenant_binding(session, tenant_id, nwa_tenant_id):
    try:
        with session.begin(subtransactions=True):
            item = get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
            if not item:
                return False
            with session.begin(subtransactions=True):
                session.query(nmodels.NWATenantKeyValue).filter(
                    and_(nmodels.NWATenantKeyValue.tenant_id == tenant_id,
                         nmodels.NWATenantKeyValue.nwa_tenant_id ==
                         nwa_tenant_id)).delete()
            return True
    except sa.orm.exc.NoResultFound:
        return False


def ensure_port_binding(session, port_id):

    with session.begin(subtransactions=True):
        try:
            record = (session.query(models_ml2.PortBindingLevel).
                      filter_by(port_id=port_id).
                      one())
        except sa.orm.exc.NoResultFound:
            # for kilo(re mearge)
            record = (session.query(models_ml2.PortBinding).
                      filter_by(port_id=port_id).
                      one())
        return record


def add_nwa_tenant_queue(session, tenant_id, nwa_tenant_id='', topic=''):
    try:
        nwa = session.query(nmodels.NWATenantQueue).filter(
            nmodels.NWATenantQueue.tenant_id == tenant_id).all()
        if nwa:
            return False
        with session.begin(subtransactions=True):
            nwa = nmodels.NWATenantQueue(
                tenant_id,
                nwa_tenant_id,
                topic
            )
            session.add(nwa)
        return True
    except sa.orm.exc.NoResultFound:
        return False


def get_nwa_tenant_queue(session, tenant_id):
    try:
        queue = session.query(nmodels.NWATenantQueue).filter(
            nmodels.NWATenantQueue.tenant_id == tenant_id).one()

        if queue:
            return queue
        else:
            return None
    except sa.orm.exc.NoResultFound:
        return None


def get_nwa_tenant_queues(session):
    try:
        queues = session.query(nmodels.NWATenantQueue).all()
        return queues
    except sa.orm.exc.NoResultFound:
        return None


def del_nwa_tenant_queue(session, tenant_id):
    try:
        with session.begin(subtransactions=True):
            item = get_nwa_tenant_queue(session, tenant_id)
            if not item:
                return False
            with session.begin(subtransactions=True):
                session.query(nmodels.NWATenantQueue).filter(
                    nmodels.NWATenantQueue.tenant_id == tenant_id
                ).delete()
            return True
    except sa.orm.exc.NoResultFound:
        return False
