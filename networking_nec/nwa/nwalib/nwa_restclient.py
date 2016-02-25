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
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from six.moves.urllib import parse as urlparse

from networking_nec._i18n import _LI, _LE
from networking_nec.nwa.common import config as nwaconf
from networking_nec.nwa.nwalib import exceptions as nwa_exc
from networking_nec.nwa.nwalib import restclient
from networking_nec.nwa.nwalib import workflow


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
        self._post_data = None

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

    def workflow_polling_log_post_data(self, url, body):
        self._post_data = (url, body)

    def _log_rest_request(self, method, url, body):
        name = workflow.NwaWorkflow.name(url)
        body_str = ''
        if isinstance(body, dict):
            body_str = jsonutils.dumps(body, sort_keys=True)
        if name:
            LOG.info(_LI('NWA workflow: %(name)s %(body)s'),
                     {'name': name, 'body': body_str})
        else:
            LOG.info(_LI('NWA %(method)s %(url)s %(body)s'),
                     {'method': method,
                      'url': self._url(url),
                      'body': body_str})

    def _log_workflow_success(self, data):
        name = ''
        if self._post_data:
            post_url = self._post_data[0]
            name = (workflow.NwaWorkflow.name(post_url) or post_url)
        LOG.info(_LI("NWA workflow: %(name)s %(workflow)s"),
                 {'name': name,
                  'workflow': jsonutils.dumps(data, indent=4, sort_keys=True)})

    def _log_workflow_error(self, data):
        errno = workflow.NwaWorkflow.get_errno_from_resultdata(data)
        if not self._post_data:
            return ''
        post_url, post_body = self._post_data
        if isinstance(post_body, dict):
            post_body = jsonutils.dumps(post_body, indent=4, sort_keys=True)
        name = (workflow.NwaWorkflow.name(post_url) or post_url)
        reason = workflow.NwaWorkflow.strerror(errno)
        LOG.error(_LE("NWA workflow: %(name)s reason(%(errno)s)=%(reason)s "
                      "request=%(request)s, response=%(response)s"),
                  {'name': name,
                   'errno': errno,
                   'reason': reason,
                   'request': post_body,
                   'response': jsonutils.dumps(data, indent=4, sort_keys=True)
                   })

    def _log_rest_response(self, status_code, data):
        status = ''
        progress = ''
        if isinstance(data, dict) and data.get('status'):
            status = data.get('status')
            progress = data.get('progress')
        LOG.info(_LI("NWA HTTP %(code)s %(status)s %(progress)s"),
                 {'code': status_code,
                  'status': status, 'progress': progress})
        if status == 'FAILED':
            self._log_workflow_error(data)
        elif status == 'SUCCESS':
            self._log_workflow_success(data)

    def rest_api(self, method, url, body=None):
        status_code = 200
        try:
            self._log_rest_request(method, url, body)
            status_code, data = super(NwaRestClient,
                                      self).rest_api(method, url, body)
            self._log_rest_response(status_code, data)
            return status_code, data

        except nwa_exc.NwaException as e:
            status_code = e.http_status
            return status_code, None
