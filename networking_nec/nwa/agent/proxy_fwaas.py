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

from neutron.agent.l3.agent import L3PluginApi
from neutron.common import topics
from neutron.plugins.common import constants as n_constants
from neutron_fwaas.services.firewall.agents.firewall_agent_api import \
    FWaaSPluginApiMixin
from oslo_config import cfg
from oslo_log import helpers
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec.nwa.common import constants as nwa_const
from networking_nec.nwa.common import exceptions as nwa_exc
from networking_nec.nwa.common import utils as nwa_com_utils
from networking_nec.nwa.fwaas.rpc import server_api as nwa_fwaas_rpc
from networking_nec.nwa.l2.rpc import nwa_l2_server_api
from networking_nec.nwa.l2.rpc import tenant_binding_api

LOG = logging.getLogger(__name__)

POLICY_CREATE = 'Create'
POLICY_UPDATE = 'Update'
POLICY_DELETE = 'Delete'

POLICY_RULE = 'RULE'
POLICY_ALLOW = 'ALL_ALLOW'
POLICY_DENY = 'ALL_DENY'
POLICY_PERMIT = POLICY_ALLOW

FW_PROTOCOL_MAP = {'tcp': '0', 'udp': '1'}
FW_PROTOCOL_ID_MAP = {'icmp': 'PING', 'any': 'ALL'}

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


def parse_port(port):
    ports = port.split(':')
    if 1 < len(ports):
        return ports[0], ports[1]
    return ports[0], ports[0]


# pylint: disable=too-many-instance-attributes
class AgentProxyFWaaS(object):

    def __init__(self, context, agent_top, client):
        self.nwa_tenant_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN)
        self.nwa_l2_rpc = nwa_l2_server_api.NwaL2ServerRpcApi(topics.PLUGIN)
        self.nwa_fwaas_rpc = nwa_fwaas_rpc.FWaaSServerApi(topics.PLUGIN)
        self.agent_top = agent_top
        self.client = client
        self.context = context
        self.conf = cfg.CONF
        self.fwaas_plugin_rpc = FWaaSPluginApiMixin(
            nwa_const.NWA_FIREWALL_PLUGIN,
            self.conf.host)
        self.l3_plugin_rpc = L3PluginApi(
            topics.L3PLUGIN,
            self.conf.host)

    @property
    def proxy_tenant(self):
        return self.agent_top.proxy_tenant

    @property
    def proxy_l2(self):
        return self.agent_top.proxy_l2

    def update_status(self, context, firewall_id, status):
        self.fwaas_plugin_rpc.set_firewall_status(context, firewall_id, status)

    @helpers.log_method_call
    def create_firewall(self, context, **kwargs):
        firewall = kwargs.get('firewall')
        tid = firewall['tenant_id']
        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)
        router_ids = firewall['add-router-ids']
        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)
        for router_id in router_ids:
            if 'DEV_' + router_id + '_TenantFWName' in nwa_data.keys():
                tfw = nwa_data['DEV_' + router_id + '_TenantFWName']
                self._nwa_setting_fw_policy(context, tid, nwa_tid, tfw,
                                            firewall, POLICY_RULE,
                                            POLICY_CREATE)
        self.fwaas_plugin_rpc.set_firewall_status(context, firewall['id'],
                                                  n_constants.ACTIVE)

    def update_firewall(self, context, **kwargs):
        LOG.debug("kwargs=%s" % jsonutils.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))

        firewall = kwargs.get('firewall')
        tid = firewall['tenant_id']
        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)

        add_router_ids = firewall['add-router-ids']
        del_router_ids = firewall['del-router-ids']
        router_ids = firewall['router_ids']

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)

        for router_id in firewall['router_ids']:
            if 'DEV_' + router_id + '_TenantFWName' in nwa_data.keys():
                tfw = nwa_data['DEV_' + router_id + '_TenantFWName']
                # set rules
                LOG.debug("set policy in router.")
                self._nwa_setting_fw_policy(context, tid, nwa_tid, tfw,
                                            firewall, POLICY_RULE,
                                            POLICY_UPDATE)

        for router_id in add_router_ids:
            if router_id in router_ids:
                continue

            router_key = 'DEV_' + router_id + '_TenantFWName'
            if router_key in nwa_data.keys():
                tfw = nwa_data[router_key]
                # set all deny
                LOG.debug("set policy in router.")
                self._nwa_setting_fw_policy(context, tid, nwa_tid, tfw,
                                            firewall, POLICY_RULE,
                                            POLICY_UPDATE)

        for router_id in del_router_ids:
            router_key = 'DEV_' + router_id + '_TenantFWName'
            if router_key in nwa_data.keys():
                tfw = nwa_data[router_key]
                # set all permit
                LOG.debug("remove policy in router.(set all permit)")
                self._nwa_setting_fw_policy(context, tid, nwa_tid, tfw,
                                            firewall, POLICY_PERMIT,
                                            POLICY_UPDATE)

        self.fwaas_plugin_rpc.set_firewall_status(context, firewall['id'],
                                                  n_constants.ACTIVE)

        return

    def delete_firewall(self, context, **kwargs):
        LOG.debug("kwargs=%s" % jsonutils.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))

        firewall = kwargs.get('firewall')
        tid = firewall['tenant_id']
        nwa_tid = nwa_com_utils.get_nwa_tenant_id(tid)

        router_ids = firewall['del-router-ids']

        if not router_ids:
            return

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)

        for router_id in router_ids:
            if 'DEV_' + router_id + '_TenantFWName' in nwa_data.keys():
                tfw = nwa_data['DEV_' + router_id + '_TenantFWName']
                # set all deny or empty rules
                self._nwa_setting_fw_policy(context, tid, nwa_tid, tfw,
                                            firewall, POLICY_RULE,
                                            POLICY_DELETE)

        self.fwaas_plugin_rpc.firewall_deleted(context, firewall['id'])

    def _nwa_setting_fw_policy(self, context, tid, nwa_tid, tfw, firewall,
                               p_type, p_op, common_api=False):
        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tid, nwa_tid)

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
            raise nwa_exc.DriverError(api="SettingFWPolicy", msg=None)

        return True, nwa_data

    def _make_address_member_id(self, context, tfw):
        ret = self.nwa_fwaas_rpc.get_fwaas_id(context, tfw, 'address_member')
        if ret['result']:
            return str(ret['id'])

        msg = "Can't get address_member id"
        raise nwa_exc.DriverError(api="SettingFWPolicy", msg=msg)

    def _make_address_group_id(self, context, tfw):
        ret = self.nwa_fwaas_rpc.get_fwaas_id(context, tfw, 'address_groups')
        if ret['result']:
            return str(ret['id'])

        msg = "Can't get address_group id"
        raise nwa_exc.DriverError(api="SettingFWPolicy", msg=msg)

    def _make_service_id(self, context, tfw):
        ret = self.nwa_fwaas_rpc.get_fwaas_id(context, tfw, 'services')
        if ret['result']:
            return str(ret['id'])

        msg = "Can't get service id"
        raise nwa_exc.DriverError(api="SettingFWPolicy", msg=msg)

    def _make_policy_id(self, context, tfw):
        ret = self.nwa_fwaas_rpc.get_fwaas_id(context, tfw, 'policies')
        if ret['result']:
            return str(ret['id'])

        msg = "Can't get policy id"
        raise nwa_exc.DriverError(api="SettingFWPolicy", msg=msg)

    def _make_address_group_member(self, context, tfw, address):
        net = address.split('/')
        if 1 < len(net):
            return {
                'address': net[0],
                'subnet': str(IPNetwork(address).netmask),
                'type': '1',
                'address_member_id': self._make_address_member_id(context, tfw)
            }

        return {
            'address': net[0],
            'subnet': '255.255.255.255',
            'type': '0',
            'address_member_id': self._make_address_member_id(context, tfw)
        }

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

        self.nwa_fwaas_rpc.blk_clear_fwaas_ids(context, tfw, release_ids)

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

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
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
                'policy_id': self._make_policy_id(context, tfw),
                'used_global_ip_out': '0',
                'fwl_service_id_data': []
            }

            # src address
            if rule['source_ip_address']:
                src_addr_grp = self._make_address_group_member(
                    context, tfw, rule['source_ip_address'])
                grp_id = self._make_address_group_id(context, tfw)
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
                dst_addr_grp = self._make_address_group_member(
                    context, tfw, rule['destination_ip_address'])
                grp_id = self._make_address_group_id(context, tfw)
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
                raise nwa_exc.DriverError(
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
                    service['fwl_service_id'] = self._make_service_id(
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
