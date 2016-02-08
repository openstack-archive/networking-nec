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
from neutron.db import models_v2
from oslo_utils import timeutils
import sqlalchemy as sa


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
