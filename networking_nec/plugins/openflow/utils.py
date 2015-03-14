# Copyright 2014 NEC Corporation.  All rights reserved.
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

from oslo_log import log as logging
from oslo_utils import excutils
from sqlalchemy.orm import exc as sa_exc

from neutron.common import exceptions as n_exc
from neutron import manager

LOG = logging.getLogger(__name__)


def update_resource_status(context, resource, id, status, ignore_error=False):
    """Update status of specified resource."""
    request = {'status': status}
    plugin = manager.NeutronManager.get_plugin()
    obj_getter = getattr(plugin, '_get_%s' % resource)
    try:
        with context.session.begin(subtransactions=True):
            obj_db = obj_getter(context, id)
            obj_db.update(request)
    except (sa_exc.StaleDataError, n_exc.NotFound) as e:
        with excutils.save_and_reraise_exception() as ctxt:
            if ignore_error:
                LOG.debug("deleting %(resource)s %(id)s is being executed "
                          "concurrently. Ignoring %(exc).",
                          {'resource': resource, 'id': id,
                           'exc': e.__class__.__name__})
                ctxt.reraise = False
                return


def update_resource_status_if_changed(context, resource_type,
                                      resource_dict, new_status,
                                      ignore_error=False):
    if resource_dict['status'] != new_status:
        update_resource_status(context, resource_type,
                               resource_dict['id'],
                               new_status, ignore_error)
        resource_dict['status'] = new_status


def cmp_dpid(dpid_a, dpid_b):
    """Compare two datapath IDs as hexadecimal int.

    It returns True if equal, otherwise False.
    """
    try:
        return (int(dpid_a, 16) == int(dpid_b, 16))
    except Exception:
        return False
