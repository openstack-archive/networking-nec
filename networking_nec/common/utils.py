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

import functools

from oslo_log import log


LOG = log.getLogger(__name__)


def _get_full_class_name(cls):
    return '%s.%s' % (cls.__module__,
                      getattr(cls, '__qualname__', cls.__name__))


def log_method_return_value(method):

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        first_arg = args[0]
        cls = first_arg if isinstance(first_arg, type) else first_arg.__class__
        ret = method(*args, **kwargs)
        data = {'class_name': _get_full_class_name(cls),
                'method_name': method.__name__,
                'ret': ret}
        LOG.debug('%(class_name)s method %(method_name)s '
                  'call returned %(ret)s', data)
        return ret

    return wrapper
