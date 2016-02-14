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

from copy import deepcopy
from netaddr import IPNetwork
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

    driver_name = 'lbaas_base'

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

    def _count_tlb(self, context, nwa_data):
        vlan_key = "^LB_VIP_.*"
        return sum(not re.match(vlan_key, k) is None for k in nwa_data.keys())

    def _is_tlb(self, context, nwa_data, vlan_type):
        vlan_key = 'LB_' + vlan_type + '_LogicalLBName'
        return True if vlan_key in nwa_data.keys() else False

    def nwa_create_tenant(self, context, tid, nwa_tid):
        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        if not nwa_data:
            LOG.debug("[NWA] CreateTenant tid=%s", nwa_tid)
            self.client.create_tenant(nwa_tid)  # ignore result
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
        rcode, __ = self.client.delete_tenant(nwa_tid)
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
        net_key = 'NW_' + net_id
        if net_key not in nwa_data.keys():
            LOG.warning(_LW("already create vlan in nwa."))
            return True, nwa_data

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
        if rcode != 200 or body['status'] != 'SUCCESS':
            # create vlan failed.
            LOG.error(_LE("CreateVlan Failed."))
            return False, None

        LOG.debug("CreateVlan succeed.")
        nwa_data[net_key] = net_name
        nwa_data[net_key + '_network_id'] = net_id
        nwa_data[net_key + '_subnet_id'] = subnet_id
        nwa_data[net_key + '_subnet'] = netaddr
        nwa_data[net_key +
                 '_nwa_network_name'] = body['resultdata']['LogicalNWName']

        vlan_key = 'VLAN_' + net_id
        nwa_data[vlan_key] = 'physical_network'
        nwa_data[vlan_key + '_CreateVlan'] = ''
        nwa_data[vlan_key + '_VlanID'] = body['resultdata']['VlanID']

        LOG.debug("nwa_data=%s", jsonutils.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))
        self.agent.nwa_core_rpc.set_nwa_tenant_binding(
            context, tid, nwa_tid, nwa_data
        )
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

    def _release_fwaas_ids(self, context, tfw, body):
        release_ids = []
        id_keys = ["DeleteAddressGroupID",
                   "DeleteNATID",
                   "DeletePolicyID",
                   "DeleteRoutingID",
                   "DeleteServiceID",
                   "DeleteAddressMemberID"]

        for key in id_keys:
            if key in body['resultdata'].keys():
                if (
                        isinstance(body['resultdata'][key], str) and
                        body['resultdata'][key] != ''
                ):
                    ids = body['resultdata'][key].split(',')
                    release_ids.extend(ids)

        if not release_ids:
            return

        release_ids = list(set([int(i) for i in release_ids]))
        release_ids.sort()

        self.agent.nwa_core_rpc.balk_clear_fwaas_id(context, tfw, release_ids)

    def _make_fwaas_policy(self, context, firewall, op_type):
        props = {
            'name': firewall['name'],
            'description': firewall['description'],
            'operation_type': op_type,
            'admin_state_up': firewall['admin_state_up'],
            'Policy': {'Rules': []}
        }

        fw_rules = []

        if not op_type == POLICY_DELETE:
            for fw_rule in firewall['firewall_rule_list']:
                rule = deepcopy(fw_rule)
                rule.pop('tenant_id')
                rule.pop('firewall_policy_id')
                rule.pop('shared')
                fw_rules.append(rule)

        props['Policy']['Rules'] = fw_rules

        return props

    def _make_common_policy(self, context, firewall, p_type, p_op, tfw):
        if p_type == POLICY_PERMIT:
            return {
                "operation_type": "Update",
                "policies": [DEFAULT_PERMIT]
            }
        elif p_type == POLICY_DENY:
            return {
                "operation_type": "Update",
                "policies": [DEFAULT_DENY]
            }
        elif p_type == POLICY_RULE:
            return self._make_policy_rule(context, firewall, p_op, tfw)

        return {'operation_type': p_op}

    def _make_policy_rule(self, context, firewall, p_op, tfw):
        fw_policies = {
            'operation_type': p_op,
            "address_groups": [],
            "services": [],
            "policies": []
        }
        for rule in firewall['firewall_rule_list']:
            if not rule['enabled']:
                continue

            service = {}

            policy = {
                'policy_id': self.make_policy_id(context, tfw),
                'used_global_ip_out': '0',
                'fwl_service_id_data': []
            }

            # src address
            if rule['source_ip_address']:
                src_addr_grp = self.make_address_group_member(
                    context, tfw, rule['source_ip_address'])
                grp_id = self.make_address_group_id(context, tfw)
                fw_policies['address_groups'].append(
                    {
                        'address_member_data': [src_addr_grp],
                        'address_group_id': grp_id
                    }
                )
                policy['originating_address_group_id'] = grp_id
            else:
                policy['originating_address_group_id'] = 'all'

            # dst address
            if rule['destination_ip_address']:
                dst_addr_grp = self.make_address_group_member(
                    context, tfw, rule['destination_ip_address'])
                grp_id = self.make_address_group_id(context, tfw)
                fw_policies['address_groups'].append(
                    {
                        'address_member_data': [dst_addr_grp],
                        'address_group_id': grp_id
                    }
                )
                policy['delivery_address_group_id'] = grp_id
            else:
                policy['delivery_address_group_id'] = 'all'

            # service: protocol and port
            if rule['protocol'] in FW_PROTOCOL_MAP.keys():
                service['protocol'] = FW_PROTOCOL_MAP[rule['protocol']]
                # move from
                # policy['fwl_service_id_data']
                #        .append(service['fwl_service_id'])
            elif rule['protocol'] in FW_PROTOCOL_ID_MAP.keys():
                policy['fwl_service_id_data'].append(
                    FW_PROTOCOL_ID_MAP[rule['protocol']])
            elif not rule['protocol']:
                policy['fwl_service_id_data'].append('ALL')
            else:
                raise NWADriverError(
                    api="SettingFWPolicy",
                    msg="invalid protocol %s" % rule['protocol']
                )

            if rule['source_port']:
                port_start, port_end = parse_port(rule['source_port'])
                service['originating_port_start'] = port_start
                service['originating_port_end'] = port_end

            if rule['destination_port']:
                port_start, port_end = parse_port(rule['destination_port'])
                service['delivery_port_start'] = port_start
                service['delivery_port_end'] = port_end

            if (
                    rule['source_port'] or
                    rule['destination_port'] or
                    rule['protocol']
            ):
                if 0 < len(service.keys()):
                    service['fwl_service_id'] = self.make_service_id(
                        context, tfw
                    )
                    if 'originating_port_start' not in service.keys():
                        service['originating_port_start'] = '1'
                    if 'delivery_port_start' not in service.keys():
                        service['delivery_port_start'] = '1'
                    if 'originating_port_end' not in service.keys():
                        service['originating_port_end'] = '65535'
                    if 'delivery_port_end' not in service.keys():
                        service['delivery_port_end'] = '65535'

                    fw_policies['services'].append(service)
                    # move to
                    policy['fwl_service_id_data'].append(
                        service['fwl_service_id']
                    )

            # action
            policy['device_type'] = '0' \
                                    if rule['action'] == 'deny' else '1'
            fw_policies['policies'].append(policy)

        fw_policies['policies'].append(DEFAULT_DENY)
        return {k: v for k, v in fw_policies.items() if not v}

    def nwa_setting_fw_policy(self, context, tid, nwa_tid, tfw, firewall,
                              p_type, p_op, common_api=False):
        nwa_data = self.get_nwa_tenant_binding(context, tid, nwa_tid)

        # Common Policy
        if common_api:
            props = self._make_common_policy(context, firewall, p_type, p_op,
                                             tfw)
        else:
            props = self._make_fwaas_policy(context, firewall, p_op)

        rcode, body = self.client.setting_fw_policy(nwa_tid, tfw, props)

        if (
                rcode == 200 and
                body['status'] == 'SUCCESS'
        ):
            LOG.debug("SettingFWPolicy Success.")

            if common_api:
                self._release_fwaas_ids(context, tfw, body)
        else:
            raise NWADriverError(api="SettingFWPolicy", msg=None)

        return True, nwa_data

    def make_address_member_id(self, context, tfw):
        ret = self.agent.nwa_core_rpc.get_fwaas_id(context, tfw,
                                                   'address_member')
        if ret['result']:
            return str(ret['id'])

        msg = "Can't get address_member id"
        raise NWADriverError(api="SettingFWPolicy", msg=msg)

    def make_address_group_id(self, context, tfw):
        ret = self.agent.nwa_core_rpc.get_fwaas_id(context, tfw,
                                                   'address_groups')
        if ret['result']:
            return str(ret['id'])

        msg = "Can't get address_group id"
        raise NWADriverError(api="SettingFWPolicy", msg=msg)

    def make_service_id(self, context, tfw):
        ret = self.agent.nwa_core_rpc.get_fwaas_id(context, tfw, 'services')
        if ret['result']:
            return str(ret['id'])

        msg = "Can't get service id"
        raise NWADriverError(api="SettingFWPolicy", msg=msg)

    def make_policy_id(self, context, tfw):
        ret = self.agent.nwa_core_rpc.get_fwaas_id(context, tfw, 'policies')
        if ret['result']:
            return str(ret['id'])

        msg = "Can't get policy id"
        raise NWADriverError(api="SettingFWPolicy", msg=msg)

    def make_address_group_member(self, context, tfw, address):
        net = address.split('/')
        if 1 < len(net):
            return {
                'address': net[0],
                'subnet': str(IPNetwork(address).netmask),
                'type': '1',
                'address_member_id': self.make_address_member_id(context, tfw)
            }

        return {
            'address': net[0],
            'subnet': '255.255.255.255',
            'type': '0',
            'address_member_id': self.make_address_member_id(context, tfw)
        }
