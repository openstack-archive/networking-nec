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

import re

from neutron.common import exceptions
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec._i18n import _LE, _LW
from networking_nec.plugins.necnwa.common import config
from networking_nec.plugins.necnwa.nwalib import client as nwa_cli

LOG = logging.getLogger(__name__)

KEY_CREATE_TENANT_NW = 'CreateTenantNW'

POLICY_CREATE = 'Create'
POLICY_UPDATE = 'Update'
POLICY_DELETE = 'Delete'

POLICY_RULE = 'RULE'
POLICY_ALLOW = 'ALL_ALLOW'
POLICY_DENY = 'ALL_DENY'
POLICY_PERMIT = POLICY_ALLOW

POLICY_TYPE_POOL = 'pool'
POLICY_TYPE_VIP = 'vip'
POLICY_TYPE_MEMBER = 'member'
POLICY_TYPE_HEALTHMONITOR = 'health_monitor'


FW_PROTOCOL_MAP = {'tcp': '0', 'udp': '1'}
FW_PROTOCOL_ID_MAP = {'icmp': 'PING', 'any': 'ALL'}

DUMMY_POLICY_ADDRESS_MEMBER_ID_START = 1000
DUMMY_POLICY_ADDRESS_GROUP_ID_START = 2000
DUMMY_POLICY_SERVICE_ID_START = 3000
DUMMY_POLICY_ID_START = 4000

DEFAULT_DENY = {
    "delivery_address_group_id": "all",
    "delivery_address_type": "0",
    "device_type": "0",
    "fwl_service_id_data": ["ALL"],
    "originating_address_group_id": "all",
    "policy_id": "65535",
    "used_global_ip_out": "0"
}

DEFAULT_PERMIT = {
    "delivery_address_group_id": "all",
    "delivery_address_type": "0",
    "device_type": "1",
    "fwl_service_id_data": ["ALL"],
    "originating_address_group_id": "all",
    "policy_id": "65535",
    "used_global_ip_out": "0"
}


class NWADriverError(exceptions.NeutronException):
    message = ("NWA Driver Error: api=%(api)s "
               "msg=%(msg)s")


def parse_port(port):
    ports = port.split(':')

    if 1 < len(ports):
        return ports[0], ports[1]

    return ports[0], ports[0]


class NECNWAAgentBaseDriver(object):

    def __init__(self, agent, context):
        self.agent = agent
        self.context = context
        self.conf = config.CONF
        self.client = nwa_cli.NwaClient()
        self.res_name = self.conf.NWA.resource_group_name

    def handle_success(self, context, rcode, jbody, *args, **kargs):
        pass

    def handle_error(self, context, rcode, jbody, *args, **kargs):
        pass

    def get_nwa_tenant_binding(self, context, tid, nwa_tid):
        nwa_data = self.agent.nwa_core_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid
        )
        return nwa_data

    def get_nwa_networks(self, context, tid, nwa_tid):
        nwa_data = self.agent.nwa_core_rpc.get_nwa_networks(
            context, tid, nwa_tid
        )
        return nwa_data

    def get_nwa_network(self, context, net_id):
        nwa_data = self.agent.nwa_core_rpc.get_nwa_network(
            context, net_id
        )
        return nwa_data

    def _count_active_vlan(self, context, nwa_data):
        vlan_key = "^VLAN_*"
        return sum(not re.match(vlan_key, k) is None for k in nwa_data.keys())

    def nwa_create_tenant(self, context, tid, nwa_tid):
        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        if not nwa_data:
            LOG.debug("[NWA] CreateTenant tid=%s", nwa_tid)
            rcode, body = self.client.create_tenant(nwa_tid)
            # ignore result

            nwa_data['CreateTenant'] = True
            nwa_data['NWA_tenant_id'] = nwa_tid

            LOG.debug("nwa_data=%s", jsonutils.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))

            return self.agent.nwa_core_rpc.add_nwa_tenant_binding(
                context, tid, nwa_tid, nwa_data
            )

        return nwa_data

    def nwa_delete_tenant(self, context, tid, nwa_tid):
        rcode, body = self.client.delete_tenant(nwa_tid)

        if rcode == 200:
            LOG.debug("[NWA] DeleteTenant Success. tid=%s", tid)
        else:
            LOG.debug("[NWA] DeleteTenant Error."
                      "tid=%s rcode=%d" % (tid, rcode))

        self.agent.nwa_core_rpc.delete_nwa_tenant_binding(
            context, tid, nwa_tid
        )

        return

    def nwa_create_tenant_nw(self, context, tid, nwa_tid, resource_group_name):
        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        if KEY_CREATE_TENANT_NW not in nwa_data.keys():
            rcode, body = self.client.create_tenant_nw(
                self.handle_success,
                self.handle_error,
                context,
                nwa_tid,
                resource_group_name
            )

            if (
                    rcode == 200 and
                    body['status'] == 'SUCCESS'
            ):
                LOG.debug("CreateTenantNW succeed.")
                nwa_data[KEY_CREATE_TENANT_NW] = True

                LOG.debug("nwa_data=%s", jsonutils.dumps(
                    nwa_data,
                    indent=4,
                    sort_keys=True
                ))
                self.agent.nwa_core_rpc.set_nwa_tenant_binding(
                    context, tid, nwa_tid, nwa_data
                )

                return True, nwa_data
            else:
                LOG.error(_LE("CreateTenantNW Failed."))
                return False, dict()

        return True, nwa_data

    def nwa_delete_tenant_nw(self, context, tid, nwa_tid):
        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        if self._count_active_vlan(context, nwa_data):
            return False, None

        rcode, body = self.client.delete_tenant_nw(
            self.handle_success,
            self.handle_error,
            context,
            nwa_tid,
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCESS'
        ):
            LOG.debug("DeleteTenantNW SUCCESS.")
            nwa_data.pop(KEY_CREATE_TENANT_NW)

            LOG.debug("nwa_data=%s", jsonutils.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            self.agent.nwa_core_rpc.set_nwa_tenant_binding(
                context, tid, nwa_tid, nwa_data
            )
        else:
            raise NWADriverError(api="CreateTenantNW", msg=None)

        return True, nwa_data

    def nwa_create_vlan(
            self, context, tid, nwa_tid, net_id, net_name,
            subnet_id, netaddr, mask, vlan_type
    ):
        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        nw_vlan_key = 'NW_' + net_id
        if nw_vlan_key not in nwa_data.keys():
            rcode, body = self.client.create_vlan(
                self.handle_success,
                self.handle_error,
                context,
                nwa_tid,
                netaddr,
                mask,
                vlan_type=vlan_type,
                openstack_network_id=net_id
            )

            if (
                    rcode == 200 and
                    body['status'] == 'SUCCESS'
            ):
                LOG.debug("CreateVlan succeed.")
                nw_net = 'NW_' + net_id
                nwa_data[nw_net] = net_name
                nwa_data[nw_net + '_network_id'] = net_id
                nwa_data[nw_net + '_subnet_id'] = subnet_id
                nwa_data[nw_net + '_subnet'] = netaddr
                nwa_data[nw_net + '_nwa_network_name'] = \
                    body['resultdata']['LogicalNWName']

                vp_net = 'VLAN_' + net_id
                nwa_data[vp_net + '_CreateVlan'] = ''

                if body['resultdata']['VlanID'] != '':
                    nwa_data[vp_net + '_VlanID'] = body['resultdata']['VlanID']
                else:
                    nwa_data[vp_net + '_VlanID'] = ''

                nwa_data[vp_net] = 'physical_network'

                LOG.debug("nwa_data=%s", jsonutils.dumps(
                    nwa_data,
                    indent=4,
                    sort_keys=True
                ))
                self.agent.nwa_core_rpc.set_nwa_tenant_binding(
                    context, tid, nwa_tid, nwa_data
                )
            else:
                # create vlan failed.
                LOG.error(_LE("CreateVlan Failed."))
                return False, None
        else:
            LOG.warning(_LW("already create vlan in nwa."))

        return True, nwa_data

    def nwa_delete_vlan(self, context, tid, nwa_tid, net_id, vlan_type):
        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        vlan_key = 'VLAN_' + net_id

        if vlan_key not in nwa_data.keys():
            msg = "vlan key not found. vlan key=%s" % vlan_key
            raise NWADriverError(api="DeleteVlan", msg=msg)

        rcode, body = self.client.delete_vlan(
            self.handle_success,
            self.handle_error,
            context,
            nwa_tid,
            nwa_data['NW_' + net_id + '_nwa_network_name'],
            vlan_type
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCESS'
        ):
            LOG.debug("DeleteVlan SUCCESS.")

            nw_net = 'NW_' + net_id
            nwa_data.pop(nw_net)
            nwa_data.pop(nw_net + '_network_id')
            nwa_data.pop(nw_net + '_subnet_id')
            nwa_data.pop(nw_net + '_subnet')
            nwa_data.pop(nw_net + '_nwa_network_name')

            vp_net = 'VLAN_' + net_id
            nwa_data.pop(vp_net)
            nwa_data.pop(vp_net + '_VlanID')
            nwa_data.pop(vp_net + '_CreateVlan')

            physical_network = self.res_name

            self.agent.nwa_core_rpc.release_dynamic_segment_from_agent(
                context, physical_network,
                net_id
            )

            LOG.debug("nwa_data=%s", jsonutils.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            self.agent.nwa_core_rpc.set_nwa_tenant_binding(
                context, tid, nwa_tid, nwa_data
            )
        else:
            LOG.debug("DeleteVlan FAILED.")
            return False, None

        return True, nwa_data
