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

from neutron.common import exceptions as n_exc

from networking_nec._i18n import _


class NWAClientError(n_exc.NeutronException):
    message = _('NWAClient Error %(msg)s')


class NWAUtilsError(n_exc.NeutronException):
    message = _('NWAUtils Error %(msg)s')


class ResourceGroupNameNotFound(n_exc.NotFound):
    message = _("ResourceGroupName %(device_owner)s could not be found")
