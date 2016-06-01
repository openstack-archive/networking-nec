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
import copy
import hashlib
import hmac
import re

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
import six
from six.moves.urllib import parse as urlparse

from networking_nec._i18n import _LI, _LW, _LE
from networking_nec.nwa.common import config as nwaconf
from networking_nec.nwa.nwalib import exceptions as nwa_exc
from networking_nec.nwa.nwalib import restclient
from networking_nec.nwa.nwalib import semaphore as nwa_sem
from networking_nec.nwa.nwalib import workflow


LOG = logging.getLogger(__name__)

cfgNWA = nwaconf.cfg.CONF.NWA

CRLF = '\x0D\x0A'


class NwaRestClient(restclient.RestClient):
    '''Client class of NWA rest. '''

    workflow_list_is_loaded = False

    def __init__(self, host=None, port=None, use_ssl=True, auth=None,
                 access_key_id=None, secret_access_key=None, **kwargs):
        load_workflow_list = kwargs.pop('load_workflow_list', True)
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
        self.workflow_first_wait = cfg.CONF.NWA.scenario_polling_first_timer
        self.workflow_wait_sleep = cfg.CONF.NWA.scenario_polling_timer
        self.workflow_retry_count = cfg.CONF.NWA.scenario_polling_count
        LOG.info(_LI('NWA init: workflow wait: %(first_wait)ss + '
                     '%(wait_sleep)ss x %(retry_count)s times.'),
                 {'first_wait': self.workflow_first_wait,
                  'wait_sleep': self.workflow_wait_sleep,
                  'retry_count': self.workflow_retry_count})
        if load_workflow_list and not NwaRestClient.workflow_list_is_loaded:
            self.update_workflow_list()
            NwaRestClient.workflow_list_is_loaded = True

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
        elif status == 'SUCCEED':
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

    def workflowinstance(self, execution_id):
        return self.get('/umf/workflowinstance/' + execution_id)

    def stop_workflowinstance(self, execution_id):
        return self.delete('/umf/workflowinstance/' + execution_id)

    def workflow_kick_and_wait(self, call, url, body):
        http_status = -1
        rj = None
        (http_status, rj) = call(url, body)

        if not isinstance(rj, dict):
            return (http_status, None)

        exeid = rj.get('executionid')
        if not isinstance(exeid, six.string_types):
            LOG.error(_LE('Invalid executin id %s'), exeid)
        try:
            wait_time = self.workflow_first_wait
            eventlet.sleep(wait_time)
            for __ in range(self.workflow_retry_count):
                (http_status, rw) = self.workflowinstance(exeid)
                if not isinstance(rw, dict):
                    LOG.error(
                        _LE('NWA workflow: failed %(http_status)s %(body)s'),
                        {'http_status': http_status, 'body': rw}
                    )
                    return (http_status, None)
                if rw.get('status') != 'RUNNING':
                    LOG.debug('%s', rw)
                    return (http_status, rw)
                eventlet.sleep(wait_time)
                wait_time = self.workflow_wait_sleep
            LOG.warning(_LW('NWA workflow: retry over. retry count is %s.'),
                        self.workflow_retry_count)
        except Exception as e:
            LOG.error(_LE('NWA workflow: %s'), e)
        return (http_status, None)

    def call_workflow(self, tenant_id, post, name, body):
        url = workflow.NwaWorkflow.path(name)
        try:
            wkf = nwa_sem.Semaphore.get_tenant_semaphore(tenant_id)
            if wkf.sem.locked():
                LOG.info(_LI('NWA sem %s(count)s: %(name)s %(url)s %(body)s'),
                         {'count': wkf.sem.balance,
                          'name': post.__name__,
                          'url': url,
                          'body': body})
            with wkf.sem:
                n = copy.copy(self)
                n.workflow_polling_log_post_data(url, body)
                http_status, rj = n.workflow_kick_and_wait(post, url, body)
                return http_status, rj
        except Exception as e:
            LOG.exception(_LE('%s'), e)
            return -1, None

    def wait_workflow_done(self, thr):
        LOG.debug('*** start wait')
        thr.wait()
        LOG.debug('*** end wait')

    def get_tenant_resource(self, tenant_id):
        return self.get('/umf/reserveddcresource/' + tenant_id)

    def get_dc_resource_groups(self, group=None):
        if not group:
            url = '/umf/dcresource/groups'
        else:
            url = '/umf/dcresource/groups/' + str(group)
        return self.get(url)

    def get_reserved_dc_resource(self, tenant_id):
        url = '/umf/reserveddcresource/' + str(tenant_id)
        return self.get(url)

    def get_workflow_list(self):
        try:
            url = '/umf/workflow/list'
            return self.get(url)
        except Exception as e:
            LOG.warning(_LW('The initial worklist is not updated,'
                            ' using default worklist. (%s)'), e)
            return None, None

    def update_workflow_list(self):
        __, rj = self.get_workflow_list()
        nameid = {}
        if isinstance(rj, dict) and rj.get('Workflows'):
            def new_nameid(wf):
                path = wf.get('Path')
                if isinstance(path, six.string_types):
                    m = re.search(r'\\([a-zA-Z0-9_]+)$', path)
                    if m:
                        key = str(m.group(1))
                        nameid[key] = str(wf.get('Id'))
            for _wf in rj.get('Workflows'):
                new_nameid(_wf)
        workflow.NwaWorkflow.update_nameid(nameid)
