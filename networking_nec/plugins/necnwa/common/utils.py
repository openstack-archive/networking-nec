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

from networking_nec.plugins.necnwa.common import config


def get_nwa_tenant_id(tenant_id):
    return config.CONF.NWA.region_name + tenant_id


def get_tenant_info(context):
    tenant_id = context.network.current['tenant_id']
    nwa_tenant_id = get_nwa_tenant_id(tenant_id)
    return tenant_id, nwa_tenant_id
