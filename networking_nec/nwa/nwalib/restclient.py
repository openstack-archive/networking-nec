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

from networking_nec._i18n import _, _LI
from networking_nec.nwa.nwalib import exceptions as nwa_exc


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

    def get(self, url):
        return self.rest_api("GET", url)

    def post(self, url, body=None):
        return self.rest_api("POST", url, body=body)

    def put(self, url, body=None):
        return self.rest_api("PUT", url, body=body)

    def delete(self, url):
        return self.rest_api("DELETE", url)
