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

    def __init__(self):
        self._sem = eventlet.semaphore.Semaphore(1)

    @property
    def sem(self):
        return self._sem
