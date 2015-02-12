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

from neutron import manager


def update_resource_status(context, resource, id, status):
    """Update status of specified resource."""
    request = {'status': status}
    plugin = manager.NeutronManager.get_plugin()
    obj_getter = getattr(plugin, '_get_%s' % resource)
    with context.session.begin(subtransactions=True):
        obj_db = obj_getter(context, id)
        obj_db.update(request)


def update_resource_status_if_changed(context, resource_type,
                                      resource_dict, new_status):
    if resource_dict['status'] != new_status:
        update_resource_status(context, resource_type,
                               resource_dict['id'],
                               new_status)
        resource_dict['status'] = new_status


def cmp_dpid(dpid_a, dpid_b):
    """Compare two datapath IDs as hexadecimal int.

    It returns True if equal, otherwise False.
    """
    try:
        return (int(dpid_a, 16) == int(dpid_b, 16))
    except Exception:
        return False
