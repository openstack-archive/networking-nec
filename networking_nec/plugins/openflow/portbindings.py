# Copyright 2015 NEC Corporation.  All rights reserved.
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

from neutron.agent import securitygroups_rpc as sg_rpc
from neutron.api.v2 import attributes as attrs
from neutron.common import exceptions as n_exc
from neutron.db import portbindings_db
from neutron.extensions import portbindings

from networking_nec.plugins.openflow.db import api as ndb
from networking_nec.plugins.openflow import exceptions as nexc
from networking_nec.plugins.openflow import utils as necutils


class PortBindingMixin(portbindings_db.PortBindingMixin):

    def _get_base_binding_dict(self):
        sg_enabled = sg_rpc.is_firewall_enabled()
        vif_details = {portbindings.CAP_PORT_FILTER: sg_enabled,
                       portbindings.OVS_HYBRID_PLUG: sg_enabled}
        binding = {portbindings.VIF_TYPE: portbindings.VIF_TYPE_OVS,
                   portbindings.VIF_DETAILS: vif_details}
        return binding

    def _extend_port_dict_binding_portinfo(self, port_res, portinfo):
        if portinfo:
            port_res[portbindings.PROFILE] = {
                'datapath_id': portinfo['datapath_id'],
                'port_no': portinfo['port_no'],
            }
        elif portbindings.PROFILE in port_res:
            del port_res[portbindings.PROFILE]

    def _validate_portinfo(self, profile):
        key_specs = {
            'datapath_id': {'type:string': None, 'required': True},
            'port_no': {'type:non_negative': None, 'required': True,
                        'convert_to': attrs.convert_to_int}
        }
        msg = attrs._validate_dict_or_empty(profile, key_specs=key_specs)
        if msg:
            raise n_exc.InvalidInput(error_message=msg)

        datapath_id = profile.get('datapath_id')
        port_no = profile.get('port_no')
        try:
            dpid = int(datapath_id, 16)
        except ValueError:
            raise nexc.ProfilePortInfoInvalidDataPathId()
        if dpid > 0xffffffffffffffffL:
            raise nexc.ProfilePortInfoInvalidDataPathId()
        # Make sure dpid is a hex string beginning with 0x.
        dpid = hex(dpid)

        if int(port_no) > 65535:
            raise nexc.ProfilePortInfoInvalidPortNo()

        return {'datapath_id': dpid, 'port_no': port_no}

    def _process_portbindings_portinfo_create(self, context, port_data, port):
        """Add portinfo according to bindings:profile in create_port().

        :param context: neutron api request context
        :param port_data: port attributes passed in PUT request
        :param port: port attributes to be returned
        """
        profile = port_data.get(portbindings.PROFILE)
        # If portbindings.PROFILE is None, unspecified or an empty dict
        # it is regarded that portbinding.PROFILE is not set.
        profile_set = attrs.is_attr_set(profile) and profile
        if profile_set:
            portinfo = self._validate_portinfo(profile)
            portinfo['mac'] = port['mac_address']
            ndb.add_portinfo(context.session, port['id'], **portinfo)
        else:
            portinfo = None
        self._extend_port_dict_binding_portinfo(port, portinfo)

    def _process_portbindings_portinfo_update(self, context, port_data, port):
        """Update portinfo according to bindings:profile in update_port().

        :param context: neutron api request context
        :param port_data: port attributes passed in PUT request
        :param port: port attributes to be returned
        """
        if portbindings.PROFILE not in port_data:
            return
        profile = port_data.get(portbindings.PROFILE)
        # If binding:profile is None or an empty dict,
        # it means binding:.profile needs to be cleared.
        # TODO(amotoki): Allow Make None in binding:profile in
        # the API layer. See LP bug #1220011.
        profile_set = attrs.is_attr_set(profile) and profile
        cur_portinfo = ndb.get_portinfo(context.session, port['id'])
        if profile_set:
            portinfo = self._validate_portinfo(profile)
            if cur_portinfo:
                if (necutils.cmp_dpid(portinfo['datapath_id'],
                                      cur_portinfo.datapath_id) and
                        portinfo['port_no'] == cur_portinfo.port_no):
                    return
                ndb.del_portinfo(context.session, port['id'])
            portinfo['mac'] = port['mac_address']
            ndb.add_portinfo(context.session, port['id'], **portinfo)
        elif cur_portinfo:
            portinfo = None
            ndb.del_portinfo(context.session, port['id'])
        else:
            portinfo = None
        self._extend_port_dict_binding_portinfo(port, portinfo)

    def extend_port_dict_binding(self, port_res, port_db):
        super(PortBindingMixin, self).extend_port_dict_binding(port_res,
                                                               port_db)
        self._extend_port_dict_binding_portinfo(port_res, port_db.portinfo)

    def _process_portbindings_create(self, context, port_data, port):
        super(PortBindingMixin, self)._process_portbindings_create_and_update(
            context, port_data, port)
        self._process_portbindings_portinfo_create(context, port_data, port)

    def _process_portbindings_update(self, context, port_data, port):
        super(PortBindingMixin, self)._process_portbindings_create_and_update(
            context, port_data, port)
        self._process_portbindings_portinfo_update(context, port_data, port)
