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

import base64
import hashlib
import hmac

from oslo_log import log as logging

from networking_nec._i18n import _LI
from networking_nec.plugins.necnwa.common import config as nwaconf
from networking_nec.plugins.necnwa.nwalib import restclient


LOG = logging.getLogger(__name__)

cfgNWA = nwaconf.cfg.CONF.NWA

CRLF = '\x0D\x0A'


class NwaRestClient(restclient.RestClient):
    '''Client class of NWA rest. '''

    def __init__(self, *args, **kwargs):
        access_key_id = kwargs.pop('access_key_id',
                                   cfgNWA.access_key_id)
        secret_access_key = kwargs.pop('secret_access_key',
                                       cfgNWA.secret_access_key)

        self._init_default(
            kwargs,
            url=cfgNWA.server_url,
            auth=self.define_auth_function(access_key_id, secret_access_key)
        )
        super(NwaRestClient, self).__init__(*args, **kwargs)

        self.workflow_first_wait = cfgNWA.scenario_polling_first_timer
        self.workflow_wait_sleep = cfgNWA.scenario_polling_timer
        self.workflow_retry_count = cfgNWA.scenario_polling_count
        LOG.info(
            _LI('NWA init: host=%(host)s port=%(port)s use_ssl=%(use_ssl)s '
                'auth=%(auth)s'),
            {'host': self.host, 'port': self.port, 'use_ssl': self.use_ssl,
             'auth': self.auth}
        )
        LOG.info(_LI('NWA init: workflow wait: %(first_wait)ss + '
                     '%(wait_sleep)ss x %(retry_count)s times.'),
                 {'first_wait': self.workflow_first_wait,
                  'wait_sleep': self.workflow_wait_sleep,
                  'retry_count': self.workflow_retry_count})
        LOG.info(_LI('NWA init: umf api version: %s'),
                 self.umf_api_version)

    def define_auth_function(self, access_key_id, secret_access_key):
        def azure_auth(datestr, path):
            signature = hmac.new(
                secret_access_key,
                datestr + CRLF + path,
                hashlib.sha256
            ).digest()
            return ('SharedKeyLite %s:%s' %
                    (access_key_id,
                     base64.encodestring(signature).rstrip()))

        auth = None
        if access_key_id and secret_access_key:
            auth = azure_auth
        return auth
