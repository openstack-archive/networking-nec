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

import datetime

from oslo_log import log as logging
from oslo_serialization import jsonutils
import requests

from networking_nec._i18n import _, _LI, _LE
from networking_nec.nwa.nwalib import exceptions as nwa_exc
from networking_nec.nwa.nwalib import workflow


LOG = logging.getLogger(__name__)

DATE_HEADER_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'

UMF_API_VERSION = '2.0.2.1.201502'
OLD_UMF_API_VERSION = '2.0.2.201402'


# datetime.datetime.utcnow cannot be mocked.
# It is required to mock utcnow in unit test.
def utcnow():
    return datetime.datetime.utcnow()


class RestClient(object):
    """A HTTP/HTTPS client for NEC NWA Drivers."""

    def __init__(self, host=None, port=None, use_ssl=True, auth=None,
                 umf_api_version=UMF_API_VERSION):
        """Creates a new client to some NWA.

        :param host: The host where service resides
        :param port: The port where service resides
        :param use_ssl: True to use SSL, False to use HTTP
        :param: auth: function to generate Authorization header.
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.auth = auth
        self.umf_api_version = umf_api_version
        self._post_data = None

        LOG.info(
            _LI('NWA init: host=%(host)s port=%(port)s use_ssl=%(use_ssl)s '
                'auth=%(auth)s'),
            {'host': self.host, 'port': self.port, 'use_ssl': self.use_ssl,
             'auth': self.auth}
        )
        LOG.info(_LI('NWA init: umf api version: %s'),
                 self.umf_api_version)

    def _url(self, path):
        protocol = "http"
        if self.use_ssl:
            protocol = "https"
        return '%s://%s:%s%s' % (protocol, self.host, self.port, path)

    def workflow_polling_log_post_data(self, url, body):
        self._post_data = (url, body)

    def _make_headers(self, path):
        datestr = utcnow().strftime(DATE_HEADER_FORMAT)
        headers = {
            # XXX: If auth is None, RestClient will be broken.
            'Authorization': self.auth(datestr, path),
            'Content-Type': 'application/json',
            'Date': datestr,
            'X-UMF-API-Version': self.umf_api_version
        }
        return headers

    def _send_receive(self, method, path, body=None):
        scheme = "http"
        if self.use_ssl:
            scheme = "https"

        url = "%s://%s:%d%s" % (scheme, self.host, int(self.port), path)
        headers = self._make_headers(path)
        LOG.debug('NWA HTTP Headers %s', headers)
        res = requests.request(method, url, data=body, headers=headers,
                               verify=False, proxies={'no': 'pass'})
        return res

    def rest_api(self, method, url, body=None):
        if isinstance(body, dict):
            body = jsonutils.dumps(body, indent=4, sort_keys=True)

        LOG.debug("NWA %(method)s %(host)s:%(port)s%(url)s body=%(body)s",
                  {'method': method, 'host': self.host, 'port': self.port,
                   'url': url, 'body': body})

        status_code = -1
        try:
            res = self._send_receive(method, url, body)
        except requests.exceptions.RequestException as e:
            msg = _("NWA Failed to connect %(host)s:%(port)s: %(reason)s")
            msg_params = {'host': self.host,
                          'port': self.port,
                          'reason': e}
            LOG.error(msg, msg_params)
            raise nwa_exc.NwaException(status_code, msg % msg_params, e)

        data = res.text
        LOG.debug("NWA returns: httpStatus=%(status)s body=%(data)s",
                  {'status': res.status_code,
                   'data': data})
        try:
            data = jsonutils.loads(data)
        except (ValueError, TypeError):
            pass
        status_code = int(res.status_code)
        if 200 <= status_code and status_code <= 209:
            return (status_code, data)
        else:
            msg = _("NWA failed: %(method)s %(host)s:%(port)s%(url)s "
                    "(HTTP/1.1 %(status_code)s %(reason)s) body=%(data)s")
            msg_params = {'method': method,
                          'host': self.host,
                          'port': self.port,
                          'url': url,
                          'status_code': res.status_code,
                          'reason': res.reason,
                          'data': data}
            LOG.warning(msg, msg_params)
            raise nwa_exc.NwaException(status_code, msg % msg_params)

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

    def rest_api_return_check(self, method, url, body=None):
        status_code = 200
        try:
            self._log_rest_request(method, url, body)
            status_code, data = self.rest_api(method, url, body)
            self._log_rest_response(status_code, data)
            return status_code, data

        except nwa_exc.NwaException as e:
            status_code = e.http_status
            return status_code, None

    def get(self, url):
        return self.rest_api_return_check("GET", url)

    def post(self, url, body=None):
        return self.rest_api_return_check("POST", url, body=body)

    def put(self, url, body=None):
        return self.rest_api_return_check("PUT", url, body=body)

    def delete(self, url):
        return self.rest_api_return_check("DELETE", url)
