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

import eventlet
from oslo_log import log as logging
import six

from networking_nec._i18n import _LI
from networking_nec.plugins.necnwa.nwalib import workflow


LOG = logging.getLogger(__name__)


class Thread(object):
    def __init__(self, thread):
        self.thread = thread

    def stop(self):
        self.thread.kill()

    def wait(self):
        return self.thread.wait()


class Semaphore(object):
    lock = eventlet.semaphore.Semaphore(1)
    tenants = {}

    @classmethod
    def get_tenant_semaphore(cls, tenant_id):
        if not isinstance(tenant_id, six.string_types) or tenant_id == '':
            raise TypeError('%s is not a string' % tenant_id)
        with Semaphore.lock:
            if tenant_id not in Semaphore.tenants:
                LOG.info(_LI('create semaphore for %s'), tenant_id)
                Semaphore.tenants[tenant_id] = Semaphore()
            return Semaphore.tenants[tenant_id]

    @classmethod
    def delete_tenant_semaphore(cls, tenant_id):
        with Semaphore.lock:
            if tenant_id in Semaphore.tenants:
                LOG.info(_LI('delete semaphore for %s'), tenant_id)
                del Semaphore.tenants[tenant_id]

    @classmethod
    def any_locked(cls):
        with Semaphore.lock:
            for t in Semaphore.tenants:
                if Semaphore.tenants[t].sem.locked():
                    return True
        return False

    def __init__(self):
        self._sem = eventlet.semaphore.Semaphore(1)
        self._histrun = []
        self._histsiz = 2

    @property
    def sem(self):
        return self._sem

    @property
    def histrun(self):
        return self._histrun

    @property
    def histsiz(self):
        return self._histsiz

    def search_history(self, call, url, body):
        name = call.__name__
        for hr in self.histrun:
            if hr['call'] == name and hr['url'] == url and hr['body'] == body:
                LOG.debug('NWA search_history - hit name=%(name)s url=%(url)s '
                          'body=%(body)s',
                          {'name': name, 'url': url, 'body': body})
                return hr['http_status'], hr['rj']
        LOG.debug('NWA search_history - no hit')
        return None, None

    def push_history(self, call, url, body, http_status, rj):
        while len(self.histrun) > self.histsiz:
            self.histrun.pop()
        (hs, rb) = self.search_history(call, url, body)
        if rb is not None:
            return
        if isinstance(rj, dict) and rj.get('status') == 'SUCCESS':
            hr = {
                'call': call.__name__,
                'url': url,
                'body': body,
                'http_status': http_status,
                'rj': rj
            }
            self.histrun.insert(0, hr)
            LOG.debug('NWA push_history - hr=%s', hr)

    def create_general_dev_history(self, call, creurl, body, http_status, rj):
        name = call.__name__
        url = workflow.NwaWorkflow.path('DeleteGeneralDev')
        for hr in self.histrun:
            if hr['call'] == name and hr['url'] == url:
                create = body['CreateNW_VlanLogicalName1']
                delete = hr['body']['DeleteNW_VlanLogicalName1']
                if create == delete:
                    hr['url'], hr['body'] = None, None
                    LOG.debug('NWA delete_history - hit name=%(name)s '
                              'url=%(url)s body=%(body)s',
                              {'name': name, 'url': url, 'body': body})
        self.push_history(call, creurl, body, http_status, rj)

    def delete_general_dev_history(self, call, delurl, body, http_status, rj):
        name = call.__name__
        url = workflow.NwaWorkflow.path('CreateGeneralDev')
        for hr in self.histrun:
            if hr['call'] == name and hr['url'] == url:
                create = hr['body']['CreateNW_VlanLogicalName1']
                delete = body['DeleteNW_VlanLogicalName1']
                if create == delete:
                    hr['url'], hr['body'] = None, None
                    LOG.debug('NWA delete_history - hit name=%(name)s '
                              'url=%(url)s body=%(body)s',
                              {'name': name, 'url': url, 'body': body})
        self.push_history(call, delurl, body, http_status, rj)
