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

# place NWA_tenant into DB.

import sqlalchemy as sa

from neutron.db import model_base
from neutron.db import models_v2
from oslo_utils import timeutils


class NWATenantBinding(object):

    """Relation between OpenStack Tenant ID and NWA Tenant ID."""
    # __tablename__ = 'nwa_tenant_binding'

    # should be foreign key.
    tenant_id = sa.Column(sa.String(36),
                          primary_key=True)
    nwa_tenant_id = sa.Column(sa.String(64))
    value_json = sa.Column(sa.String(32768), nullable=False, default='')

    def __init__(self, tenant_id, nwa_tenant_id, value_json):
        self.tenant_id = tenant_id
        self.nwa_tenant_id = nwa_tenant_id
        self.value_json = value_json

    def __repr__(self):
        return "<TenantState(%s,%s,%s)>" % (
            self.tenant_id, self.nwa_tenant_id, self.value_json
        )


class NWATenantBindingN(model_base.BASEV2):

    """Relation between OpenStack Tenant ID and NWA Tenant ID."""
    __tablename__ = 'nwa_tenant_binding'

    tenant_id = sa.Column(sa.String(36), primary_key=True)
    nwa_tenant_id = sa.Column(sa.String(64))
    json_key = sa.Column(sa.String(192), nullable=False,
                         default='', primary_key=True)
    json_value = sa.Column(sa.String(1024), nullable=False,
                           default='')

    def __init__(self, tenant_id, nwa_tenant_id, json_key, json_value):
        self.tenant_id = tenant_id
        self.nwa_tenant_id = nwa_tenant_id
        self.json_key = json_key
        self.json_value = json_value

    def __repr__(self):
        return "<TenantState(%s,%s,%s)>" % (
            self.tenant_id, self.nwa_tenant_id,
            {self.json_key: self.json_value}
        )


class NWATenantQueue(model_base.BASEV2):
    """Relation between OpenStack Tenant ID and NWA Tenant ID."""
    __tablename__ = 'nwa_tenant_queue'

    tenant_id = sa.Column(sa.String(36), primary_key=True)
    nwa_tenant_id = sa.Column(sa.String(64))
    topic = sa.Column(sa.String(128), default='')

    def __init__(self, tenant_id, nwa_tenant_id, topic):
        self.tenant_id = tenant_id
        self.nwa_tenant_id = nwa_tenant_id
        self.topic = topic

    def __repr__(self):
        return "<TenantQueue(%s,%s,%s)>" % (
            self.tenant_id,
            self.nwa_tenant_id,
            self.topic
        )


class NWAFirewallIds(model_base.BASEV2, models_v2.HasId):
    __tablename__ = 'nwa_firewall_ids'

    tfw = sa.Column(sa.String(length=32), nullable=False)
    res_id = sa.Column(sa.Integer, nullable=False)
    type = sa.Column(sa.Enum('address_member', 'address_groups', 'services',
                             'policies', 'nats', 'routingss', '',
                             name='nwa_firewall_ids_type'), default='')
    used = sa.Column(sa.Boolean, nullable=False, default=False)
    created_at = sa.Column(sa.DateTime(), nullable=False)

    """
    __table_args__ = (
        sa.UniqueConstraint(
            tfw, id,
            name='uniq_tfw_ids0tfw0id'),
        model_base.BASEV2.__table_args__
    )
    """

    def __init__(self, res_id, tfw, type=None, used=False):
        self.res_id = res_id
        self.tfw = tfw
        self.type = type
        self.used = used
        self.created_at = timeutils.utcnow()
