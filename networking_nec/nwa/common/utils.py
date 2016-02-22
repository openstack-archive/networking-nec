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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec._i18n import _, _LE, _LW
# It is required to register nwa options
from networking_nec.nwa.common import config  # noqa

LOG = logging.getLogger(__name__)


def get_nwa_tenant_id(tenant_id):
    return cfg.CONF.NWA.region_name + tenant_id


def get_tenant_info(context):
    tenant_id = context.network.current['tenant_id']
    nwa_tenant_id = get_nwa_tenant_id(tenant_id)
    return tenant_id, nwa_tenant_id


def load_json_from_file(name, json_file, json_str, default_value):
    if json_file:
        json_file_abspath = cfg.CONF.find_file(json_file)
        if not json_file_abspath:
            LOG.error(_LE('Failed to load %(name)s_file'
                          '"%(json_file)s": file not found'),
                      {'name': name, 'json_file': json_file})
            raise cfg.Error(_('NECNWA option parse error'))
        try:
            with open(json_file_abspath) as f:
                return jsonutils.loads(f.read())
        except Exception as e:
            LOG.error(_LE('Failed to load %(name)s_file '
                          '"%(json_file)s": %(reason)s'),
                      {'reason': e, 'name': name, 'json_file': json_file})
            raise cfg.Error(_('NECNWA option parse error'))
    elif json_str:
        try:
            return jsonutils.loads(json_str)
        except Exception as e:
            LOG.error(_LE('NECNWA option error during loading %(name)s '
                          '(%(data)s): %(reason)s'),
                      {'reason': e, 'name': name, 'data': json_str})
            raise cfg.Error(_('NECNWA option parse error'))
    else:
        LOG.warning(_LW('%(name)s is not configured. '
                        'Make sure to set [NWA] %(name)s_file '
                        'in NWA plugin configuration file. '
                        'Using %(default)s as default value.'),
                    {'name': name, 'default': default_value})
        return default_value
