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

from neutron.db import model_base
import sqlalchemy as sa


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
