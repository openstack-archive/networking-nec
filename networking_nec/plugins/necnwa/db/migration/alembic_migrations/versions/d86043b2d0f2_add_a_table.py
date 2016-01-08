# Copyright 2016 OpenStack Foundation
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
#

"""Add tables for necnwa

Revision ID: d86043b2d0f2
Revises: kilo
Create Date: 2016-01-12 14:36:11.217570

"""

# revision identifiers, used by Alembic.
revision = 'd86043b2d0f2'
down_revision = None

from alembic import op
import sqlalchemy as sa

action_types = sa.Enum('allow', 'deny', name='nwa_firewallrules_action')
nwa_firewall_ids_type = sa.Enum(
    'address_member', 'address_groups', 'services', 'policies', 'nats',
    'routingss', '', name='nwa_firewall_ids_type')


def upgrade():
    op.create_table(
        'nwa_tenant_binding',
        sa.Column('tenant_id', sa.String(length=36),
                  nullable=False, primary_key=True),
        sa.Column('nwa_tenant_id', sa.String(length=64)),
        sa.Column('json_key', sa.String(length=192),
                  nullable=False, primary_key=True),
        sa.Column('json_value', sa.String(length=1024),
                  nullable=False, default='')
    )

    op.create_table(
        'nwa_tenant_queue',
        sa.Column('tenant_id', sa.String(length=36),
                  nullable=False, primary_key=True),
        sa.Column('nwa_tenant_id', sa.String(length=64),
                  nullable=False, default=''),
        sa.Column('topic', sa.String(length=122), nullable=False, default='')
    )

    op.create_table(
        'nwa_firewall_ids',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tfw', sa.String(length=32), nullable=False),
        sa.Column('res_id', sa.Integer, nullable=False),
        sa.Column('type', nwa_firewall_ids_type, nullable=False, default=''),
        sa.Column('used', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
