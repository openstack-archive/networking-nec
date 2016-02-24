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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import encodeutils
from six.moves.urllib import parse as urlparse

from networking_nec.nwa.common import config as nwaconf
from networking_nec.nwa.nwalib import restclient


LOG = logging.getLogger(__name__)

cfgNWA = nwaconf.cfg.CONF.NWA

CRLF = '\x0D\x0A'


class NwaRestClient(restclient.RestClient):
    '''Client class of NWA rest. '''

    def __init__(self, host=None, port=None, use_ssl=True, auth=None,
                 access_key_id=None, secret_access_key=None, **kwargs):
        if auth is None:
            auth = self._define_auth_function(access_key_id, secret_access_key)
        if not host or not port:
            if not cfgNWA.server_url:
                raise cfg.Error("'server_url' or (host, port) "
                                "must be specified.")
            host, port, use_ssl = self._parse_server_url(cfgNWA.server_url)
        super(NwaRestClient, self).__init__(host, port, use_ssl, auth,
                                            **kwargs)

    def _parse_server_url(self, url):
        url_parts = urlparse.urlparse(url)
        return (url_parts.hostname,
                url_parts.port,
                url_parts.scheme == 'https')

    def _define_auth_function(self, access_key_id, secret_access_key):
        access_key_id = access_key_id or cfgNWA.access_key_id
        secret_access_key = secret_access_key or cfgNWA.secret_access_key
        if not access_key_id or not secret_access_key:
            # XXX: Don't we need to raise an error?
            # raise cfg.Error('access_key_id and secret_access_key must '
            #                 'be specified.')
            return

        def azure_auth(datestr, path):
            signature = hmac.new(
                encodeutils.safe_encode(secret_access_key),
                encodeutils.safe_encode(datestr + CRLF + path),
                hashlib.sha256
            ).digest()
            return (encodeutils.safe_encode('SharedKeyLite %s:'
                                            % access_key_id) +
                    base64.b64encode(signature))

        return azure_auth
