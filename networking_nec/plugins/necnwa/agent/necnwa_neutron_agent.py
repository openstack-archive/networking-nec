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

import socket
import sys
import time
import re
import json

import eventlet
eventlet.monkey_patch()

from oslo_config import cfg
from oslo_messaging.rpc.server import get_rpc_server
from oslo_messaging.target import Target

from neutron.agent import rpc as agent_rpc
from neutron.common import rpc as n_rpc
from neutron.common import config as logging_config
from neutron.common import constants

from neutron.common import topics
from neutron import context as q_context
from oslo_log import log as logging
from oslo_utils import importutils
from oslo_service import loopingcall

from neutron.plugins.ml2 import driver_api as api

from networking_nec.plugins.necnwa.common import config
from networking_nec.plugins.necnwa.agent import necnwa_agent_rpc
from networking_nec.plugins.necnwa.nwalib import client as nwa_cli
from networking_nec.plugins.necnwa import necnwa_core_plugin
from networking_nec.plugins.necnwa import necnwa_utils

from neutron.plugins.common import constants as n_constants
from networking_nec.plugins.necnwa.agent.necnwa_lbaas_callback import NECNWALBaaSCallback
from networking_nec.plugins.necnwa.agent.necnwa_fwaas_callback import NECNWAFirewallCallback

LOG = logging.getLogger(__name__)

KEY_CREATE_TENANT_NW = 'CreateTenantNW'
WAIT_AGENT_NOTIFIER = 20
#WAIT_AGENT_NOTIFIER = 1

VLAN_OWN_GDV = '_GD'
VLAN_OWN_TFW = '_TFW'

all_deny_rule = {"Policy": {"Rules": [{"action": "deny"}]}}
all_allow_rule = {"Policy": {"Rules": [{"action": "allow"}]}}

all_permit_policies = {
    "policies": [{"policy_id": "65535",
                  "originating_address_group_id": "all",
                  "delivery_address_group_id": "all",
                  "delivery_address_type": "0",
                  "device_type": "1",
                  "fwl_service_id_data": ["ALL"],
                  "used_global_ip_out": "0"}],
    "operation_type": "Update"
}

all_deny_policies = {
    "policies": [{"policy_id": "65535",
                  "originating_address_group_id": "all",
                  "delivery_address_group_id": "all",
                  "delivery_address_type": "0",
                  "device_type": "0",
                  "fwl_service_id_data": ["ALL"],
                  "used_global_ip_out": "0"}],
    "operation_type": "Update"
}


def check_vlan(network_id, nwa_data):
    #dev_key = 'VLAN_' + network_id + '_.*_VlanID$'
    # TFW, GDV: VLAN_' + network_id + '_.*_VlanID$
    # TLB:      VLAN_LB_' + network_id + '_.*_VlanID$
    dev_key = 'VLAN_.*_' + network_id + '_.*_VlanID$'
    cnt = 0
    for k in nwa_data.keys():
        if re.match(dev_key, k):
            LOG.debug("find device in network(id=%s)" % network_id)
            cnt += 1

    return cnt


def count_device_id(device_id, nwa_data):
    dev_key = 'DEV_' + device_id + '_'
    cnt = 0
    for k in nwa_data.keys():
        if re.match(dev_key, k):
            LOG.debug("found device with device_id={}".format(device_id))
            cnt += 1
    return cnt


def check_segment(network_id, res_name, nwa_data, dev_type):
    dev_key = 'DEV_.*_' + network_id + '_' + res_name
    cnt = 0
    for k in nwa_data.keys():
        if (
                re.match(dev_key, k) and
                dev_type == nwa_data[k]
        ):
            LOG.debug("find device in network(id=%s),"
                      "resource_group_name=%s,"
                      "type=%s" % (network_id, res_name, dev_type))
            cnt += 1
    return cnt


def check_segment_gd(network_id, res_name, nwa_data):
    return check_segment(network_id, res_name, nwa_data, necnwa_utils.NWA_DEVICE_GDV)


def check_segment_tfw(network_id, res_name, nwa_data):
    return check_segment(network_id, res_name, nwa_data, necnwa_utils.NWA_DEVICE_TFW)


class NECNWAAgentRpcCallback(object):
    RPC_API_VERSION = '1.0'

    def __init__(self, context, agent):
        self.context = context
        self.agent = agent

    def get_nwa_rpc_servers(self, context, **kwargs):
        LOG.debug("kwargs=%s" % kwargs)
        return {'nwa_rpc_servers':
                [
                    {
                        'tenant_id': k,
                        'topic': v['topic']
                    } for k, v in self.agent.rpc_servers.items()
                ]}

    def create_server(self, context, **kwargs):
        LOG.debug("kwargs=%s" % kwargs)
        tenant_id = kwargs.get('tenant_id')
        return self.agent.create_tenant_rpc_server(tenant_id)

    def delete_server(self, context, **kwargs):
        LOG.debug("kwargs=%s" % kwargs)
        tenant_id = kwargs.get('tenant_id')
        return self.agent.delete_tenant_rpc_server(tenant_id)


class NECNWAProxyCallback(object):
    RPC_API_VERSION = '1.0'

    def __init__(self, context, agent):
        self.context = context
        self.agent = agent

    def create_general_dev(self, context, **kwargs):
        LOG.debug("Rpc callback kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))
        return self.agent.create_general_dev(context, **kwargs)

    def delete_general_dev(self, context, **kwargs):
        LOG.debug("Rpc callback kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))
        return self.agent.delete_general_dev(context, **kwargs)

    def create_tenant_fw(self, context, **kwargs):
        LOG.debug("Rpc callback kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))
        return self.agent.create_tenant_fw(context, **kwargs)

    def delete_tenant_fw(self, context, **kwargs):
        LOG.debug("Rpc callback kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))
        return self.agent.delete_tenant_fw(context, **kwargs)

    def setting_nat(self, context, **kwargs):
        LOG.debug("Rpc callback kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))
        return self.agent.setting_nat(context, **kwargs)

    def delete_nat(self, context, **kwargs):
        LOG.debug("Rpc callback kwargs=%s" % json.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))
        return self.agent.delete_nat(context, **kwargs)


class NECNWANeutronAgent(object):

    rpc_servers = dict()
    topic = necnwa_agent_rpc.NWA_AGENT_TOPIC

    def __init__(self, polling_interval):
        """Constructor.

        @param polling_interval: interval (secs) to check the nwa.
        """
        self.polling_interval = polling_interval
        self.need_sync = True

        self.conf = config.CONF

        self.agent_state = {
            'binary': 'neutron-necnwa-agent',
            'host': config.CONF.host,
            'topic': necnwa_agent_rpc.NWA_AGENT_TOPIC,
            'configurations': {},
            'agent_type': necnwa_agent_rpc.NWA_AGENT_TYPE,
            'start_flag': True}

        self.client = nwa_cli.NwaClient()

        self.setup_rpc()
        LOG.debug(self.agent_state)

    def setup_rpc(self):
        """ setup_rpc
        """
        self.host = socket.gethostname()
        self.agent_id = 'necnwa-q-agent.%s' % self.host

        self.context = q_context.get_admin_context_without_session()

        self.nwa_core_rpc = necnwa_core_plugin.NECNWAPluginTenantBinding(
            topics.PLUGIN
        )

        self.state_rpc = agent_rpc.PluginReportStateAPI(topics.PLUGIN)
        self.callback_nwa = NECNWAAgentRpcCallback(self.context, self)
        self.callback_proxy = NECNWAProxyCallback(self.context, self)

        # lbaas
        if self.conf.NWA.lbaas_driver:
            self.lbaas_driver = importutils.import_object(
                self.conf.NWA.lbaas_driver, self, self.context
            )
            self.callback_lbaas = NECNWALBaaSCallback(self.context, self.lbaas_driver)
        else:
            self.lbaas_driver = None
            self.callback_lbaas = None

        # fwaas
        if self.conf.NWA.fwaas_driver:
            self.fwaas_driver = importutils.import_object(
                self.conf.NWA.fwaas_driver, self, self.context
            )
            self.callback_fwaas = NECNWAFirewallCallback(self.context, self.fwaas_driver)
        else:
            self.fwaas_driver = None
            self.callback_fwaas = None

        # endpoints
        self.endpoints = [self.callback_nwa]

        # create connection
        self.conn = n_rpc.create_connection(new=True)

        self.conn.create_consumer(self.topic, self.endpoints,
                                  fanout=False)

        self.conn.consume_in_threads()

        report_interval = config.CONF.AGENT.report_interval
        if report_interval:
            heartbeat = loopingcall.FixedIntervalLoopingCall(
                self._report_state)
            heartbeat.start(interval=report_interval)

    def create_tenant_rpc_server(self, tid):
        """ create_ blocking rpc server
        @param tid: openstack tenant id
        """

        ret = dict()

        if tid in self.rpc_servers.keys():
            LOG.warning(
                "already in message queue and server."
                " queue=%s" % self.rpc_servers[tid]['topic']
            )

            return {'result': 'FAILED'}

        topic = "%s-%s" % (self.topic, tid)

        target = Target(
            topic=topic, server=cfg.CONF.host, fanout=False)

        assert n_rpc.TRANSPORT is not None
        serializer = n_rpc.RequestContextSerializer(None)

        server = get_rpc_server(
            n_rpc.TRANSPORT, target, [self.callback_proxy, self.callback_lbaas, self.callback_fwaas],
            'blocking', serializer
        )
        self.rpc_servers[tid] = {
            'server': server,
            'topic': topic
        }

        LOG.debug("RPCServer create: topic=%s" % topic)

        self.rpc_servers[tid]['server'].start()

        ret['result'] = 'SUCCEED'
        ret['tenant_id'] = tid
        ret['topic'] = topic

        return ret

    def delete_tenant_rpc_server(self, tid):
        if not tid in self.rpc_servers.keys():
            LOG.warning(
                "rpc server not found. tid=%s" % tid
            )

            return {'result': 'FAILED'}

        self.rpc_servers[tid]['server'].stop()
        self.rpc_servers.pop(tid)

        ret = {
            'result': 'SUCCEED',
            'tenant_id': tid
        }

        LOG.debug("RPCServer delete: %s" % ret)

        return ret

    def _report_state(self):
        try:
            queues = [v['topic'] for k, v in self.rpc_servers.items()]
            self.agent_state['configurations']['tenant_queues'] = queues
            self.state_rpc.report_state(self.context,
                                        self.agent_state)
            self.agent_state.pop('start_flag', None)

            servers = [{'tenant_id': tid} for tid in self.rpc_servers.keys()]
            self.nwa_core_rpc.update_tenant_rpc_servers(
                self.context, servers
            )

        except Exception:
            LOG.exception("Failed reporting state!")

    def loop_handler(self):
        pass

    def daemon_loop(self):
        """Main processing loop for NECNWA Plugin Agent."""
        while True:
            self.loop_handler()
            time.sleep(self.polling_interval)

    # NWA API
    def _create_tenant(self, context, **kwargs):
        """
        @param context: contains user information.
        @param kwargs: nwa_tenant_id
        @return: succeed - dict of status, and infomation.
        """
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        rcode, body = self.client.create_tenant(nwa_tenant_id)
        # ignore result
        return True, {
            'CreateTenant': True,
            'NWA_tenant_id': nwa_tenant_id
        }

    def _delete_tenant(self, context, **kwargs):
        """ Delete Tenant.
        @param context: contains user information.
        @param kwargs: nwa_tenant_id
        @return: resutl(succeed = (True, dict(empty)  other = False, None)
        """
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        rcode, body = self.client.delete_tenant(nwa_tenant_id)
        # ignore result
        return True, body

    def _create_tenant_nw(self, context, **kwargs):
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')

        # get resource gropu name for NWA TenantNW.
        resource_group_name = nwa_info['resource_group_name_nw']
        nwa_data = kwargs.get('nwa_data')

        if not KEY_CREATE_TENANT_NW in nwa_data.keys():
            LOG.debug("nwa_tenant_id=%s, resource_group_name_nw=%s" % (nwa_tenant_id, resource_group_name))
            rcode, body = self.client.create_tenant_nw(
                self._dummy_ok,
                self._dummy_ng,
                context,
                nwa_tenant_id,
                resource_group_name
            )

            if (
                    rcode == 200 and
                    body['status'] == 'SUCCEED'
            ):
                LOG.debug("CreateTenantNW succeed.")
                nwa_data[KEY_CREATE_TENANT_NW] = True
                return True, nwa_data
            else:
                LOG.error("CreateTenantNW Failed.")

                return False, dict()

    def _delete_tenant_nw(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')

        rcode, body = self.client.delete_tenant_nw(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("DeleteTenantNW SUCCEED.")
            nwa_data.pop(KEY_CREATE_TENANT_NW)
        else:
            LOG.error("DeleteTenantNW %s." % body['status'])
            return False, None

        return True, nwa_data

    def _create_vlan(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        network_name = nwa_info['network']['name']
        vlan_type = nwa_info['network']['vlan_type']
        subnet_id = nwa_info['subnet']['id']
        netaddr = nwa_info['subnet']['netaddr']
        mask = nwa_info['subnet']['mask']
        network_id = nwa_info['network']['id']

        nw_vlan_key = 'VLAN_' + network_id
        if nw_vlan_key in nwa_data.keys():
            LOG.warning("aleady in vlan_key %s" % nw_vlan_key)
            return True, nwa_data

        rcode, body = self.client.create_vlan(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            netaddr,
            mask,
            vlan_type=vlan_type,
            openstack_network_id=network_id
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            # create vlan succeed.
            LOG.debug("CreateVlan succeed.")
            nw_net = 'NW_' + network_id
            nwa_data[nw_net] = network_name
            nwa_data[nw_net + '_network_id'] = network_id
            nwa_data[nw_net + '_subnet_id'] = subnet_id
            nwa_data[nw_net + '_subnet'] = netaddr
            nwa_data[nw_net + '_nwa_network_name'] = body['resultdata']['LogicalNWName']

            vp_net = nw_vlan_key
            nwa_data[vp_net + '_CreateVlan'] = ''

            if body['resultdata']['VlanID'] != '':
                nwa_data[vp_net + '_VlanID'] = body['resultdata']['VlanID']
            else:
                nwa_data[vp_net + '_VlanID'] = ''
            nwa_data[vp_net] = 'physical_network'
        else:
            # create vlan failed.
            LOG.error("CreateVlan Failed.")
            return False, None

        return True, nwa_data

    def _delete_vlan(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        vlan_type = nwa_info['network']['vlan_type']
        physical_network = nwa_info['physical_network']
        network_id = nwa_info['network']['id']

        # delete vlan
        rcode, body = self.client.delete_vlan(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            nwa_data['NW_' + network_id + '_nwa_network_name'],
            vlan_type
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("DeleteVlan SUCCEED.")

            nw_net = 'NW_' + network_id
            nwa_data.pop(nw_net)
            nwa_data.pop(nw_net + '_network_id')
            nwa_data.pop(nw_net + '_subnet_id')
            nwa_data.pop(nw_net + '_subnet')
            nwa_data.pop(nw_net + '_nwa_network_name')

            vp_net = 'VLAN_' + network_id
            nwa_data.pop(vp_net)
            nwa_data.pop(vp_net + '_VlanID')
            nwa_data.pop(vp_net + '_CreateVlan')

            self.nwa_core_rpc.release_dynamic_segment_from_agent(
                context, physical_network,
                network_id
            )

        else:
            LOG.debug("DeleteVlan FAILED.")
            self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
            return False, None

        return True, nwa_data

    def create_tenant_fw(self, context, **kwargs):
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')

        network_id = nwa_info['network']['id']
        network_name = nwa_info['network']['name']
        vlan_type = nwa_info['network']['vlan_type']
        ipaddr = nwa_info['port']['ip']
        macaddr = nwa_info['port']['mac']
        device_owner = nwa_info['device']['owner']
        device_id = nwa_info['device']['id']
        port_id = nwa_info['port']['id']
        physical_network = nwa_info['physical_network']
        resource_group = nwa_info['resource_group_name']
        resource_group_name_nw = nwa_info['resource_group_name_nw']

        # for common policy setting

        LOG.debug("tenant_id=%s, network_id=%s, device_owner=%s" % (
            tenant_id, network_id, device_owner
        ))

        nwa_data = self.nwa_core_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        nwa_created = False

        # create tenant
        if not nwa_data:
            rcode, nwa_data = self._create_tenant(context, **kwargs)
            LOG.info("_create_tenant.ret_val=%s" % json.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            if self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id,
                    nwa_data, nwa_created=True) is False:
                return None

        # create tenant nw
        if not KEY_CREATE_TENANT_NW in nwa_data.keys():
            result, nwa_data = self._create_tenant_nw(
                context, nwa_data=nwa_data, **kwargs
            )
            LOG.info("_create_tenant_nw.ret_val=%s" % json.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            if result is False:
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id,
                    nwa_data, nwa_created=nwa_created
                )

        # create vlan
        nw_vlan_key = 'NW_' + network_id
        if not nw_vlan_key in nwa_data.keys():
            result, nwa_data = self._create_vlan(
                context, nwa_data=nwa_data, **kwargs
            )
            LOG.info("_create_vlan.ret_val=%s" % json.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            if result is False:
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id,
                    nwa_data, nwa_created=nwa_created
                )

        dev_key = 'DEV_' + device_id
        if not dev_key in nwa_data.keys():
            vlan_logical_name = nwa_data['NW_' + network_id + '_nwa_network_name']
            rcode, body = self.client.create_tenant_fw(
                self._dummy_ok,
                self._dummy_ng,
                context,
                nwa_tenant_id,
                resource_group,
                ipaddr,
                vlan_logical_name,
                vlan_type
            )

            if (
                    rcode == 200 and
                    body['status'] == 'SUCCEED'
            ):
                LOG.debug("CreateTenantFW SUCCEED.")

                tfw_name = body['resultdata']['TenantFWName']

                nwa_data['DEV_' + device_id] = 'device_id'
                nwa_data['DEV_' + device_id + '_device_owner'] = device_owner
                nwa_data['DEV_' + device_id + '_TenantFWName'] = tfw_name
                nwa_data['DEV_' + device_id + '_' + network_id] = network_name
                nwa_data['DEV_' + device_id + '_' + network_id + '_ip_address'] = ipaddr
                nwa_data['DEV_' + device_id + '_' + network_id + '_mac_address'] = macaddr
                nwa_data['DEV_' + device_id + '_' + network_id + '_' + resource_group_name_nw] = necnwa_utils.NWA_DEVICE_TFW
                # for ext net
                nwa_data['DEV_' + device_id + '_' + network_id + '_TenantFWName'] = tfw_name

                vlan_key = 'VLAN_' + network_id
                seg_key = 'VLAN_' + network_id + '_' + resource_group_name_nw + VLAN_OWN_TFW

                if nwa_data[vlan_key + '_CreateVlan'] == '':
                    nwa_data[seg_key + '_VlanID'] = body['resultdata']['VlanID']
                else:
                    nwa_data[seg_key + '_VlanID'] = nwa_data[vlan_key + '_VlanID']
                nwa_data[seg_key] = 'physical_network'

                LOG.info("_create_tenant_fw.ret_val=%s" % json.dumps(
                    nwa_data,
                    indent=4,
                    sort_keys=True
                ))

                if self.fwaas_driver:
                    # for common policy setting.
                    self._create_fwaas_ids(context, tfw_name)

                    # set firewall(draft)
                    self._setting_fw_policy_all_permit(context, tfw_name, **kwargs)

            else:
                LOG.debug("CreateTenantFW FAILED.")
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data, nwa_created=nwa_created
                )

        elif not dev_key + '_' + network_id in nwa_data.keys():

            rcode, body = self._update_tenant_fw(
                context,
                connect='connect',
                nwa_data=nwa_data,
                **kwargs
            )
            LOG.info("_update_tenant_fw.ret_val=%s" % json.dumps(
                body,
                indent=4,
                sort_keys=True
            ))
            if rcode is False:
                LOG.error("UpdateTenantFW FAILED.")
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data, nwa_created=nwa_created
                )
        else:
            LOG.warning("unknown device.")

        ret = self._update_tenant_binding(
            context, tenant_id, nwa_tenant_id, nwa_data, nwa_created=nwa_created
        )

        vlan_id = int(nwa_data['VLAN_' + network_id + '_' + resource_group_name_nw + VLAN_OWN_TFW + '_VlanID'], 10)

        segment = {api.PHYSICAL_NETWORK: physical_network,
                   api.NETWORK_TYPE: n_constants.TYPE_VLAN,
                   api.SEGMENTATION_ID: vlan_id}

        self.nwa_core_rpc.update_port_state_with_notifire(
            context, device_id, self.agent_id, port_id, segment, network_id
        )

        return ret

    def _create_fwaas_ids(self, context, tfw):
        if self.nwa_core_rpc.create_fwaas_ids(context, tfw):
            LOG.debug('FWaaS Ids Create Success')
        else:
            LOG.error('FWaaS Ids Create Error')
        return

    def _delete_fwaas_ids(self, context, tfw):
        if self.nwa_core_rpc.delete_fwaas_ids(context, tfw):
            LOG.debug('FWaaS Ids Delete Success')
        else:
            LOG.error('FWaaS Ids Delete Error')
        return

    def _update_tenant_fw(self, context, **kwargs):
        connect = kwargs.get('connect')
        if connect == 'connect':
            return self._update_tenant_fw_connect(context, **kwargs)
        if connect == 'disconnect':
            return self._update_tenant_fw_disconnect(context, **kwargs)

    def _update_tenant_fw_connect(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        device_id = nwa_info['device']['id']
        network_id = nwa_info['network']['id']
        network_name = nwa_info['network']['name']
        vlan_type = nwa_info['network']['vlan_type']
        ipaddr = nwa_info['port']['ip']
        macaddr = nwa_info['port']['mac']
        resource_group_name_nw = nwa_info['resource_group_name_nw']

        device_name = nwa_data['DEV_' + device_id + '_TenantFWName']
        vlan_logical_name = nwa_data['NW_' + network_id + '_nwa_network_name']

        rcode, body = self.client.update_tenant_fw(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            device_name,
            ipaddr,
            vlan_logical_name,
            vlan_type,
            connect='connect')

        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("UpdateTenantFW succeed.")
            tfw_name = body['resultdata']['TenantFWName']
            net_dev = 'DEV_' + device_id + '_' + network_id
            nwa_data[net_dev] = network_name
            nwa_data[net_dev + '_ip_address'] = ipaddr
            nwa_data[net_dev + '_mac_address'] = macaddr
            nwa_data[net_dev + '_TenantFWName'] = tfw_name
            nwa_data[net_dev + '_' + resource_group_name_nw] = necnwa_utils.NWA_DEVICE_TFW

            vlan_key = 'VLAN_' + network_id
            seg_key = 'VLAN_' + network_id + '_' + resource_group_name_nw + VLAN_OWN_TFW
            if nwa_data[vlan_key + '_CreateVlan'] == '':
                nwa_data[seg_key + '_VlanID'] = body['resultdata']['VlanID']
            else:
                nwa_data[seg_key + '_VlanID'] = nwa_data[vlan_key + '_VlanID']
            nwa_data[seg_key] = 'physical_network'

            # for common policy setting.
            self._create_fwaas_ids(context, tfw_name)

            return True, nwa_data
        else:
            LOG.debug("UpdateTenantFW failed.")
            return False, None

    def _update_tenant_fw_disconnect(self, context, **kwargs):
        """ Update Tenant FW
        @param context: contains user information.
        @param kwargs:
        @return: result(succeed = True, other = False), data(nwa_data or None)
        """
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        network_id = nwa_info['network']['id']
        vlan_type = nwa_info['network']['vlan_type']
        ipaddr = nwa_info['port']['ip']
        device_id = nwa_info['device']['id']
        resource_group_name_nw = nwa_info['resource_group_name_nw']

        device_name = nwa_data['DEV_' + device_id + '_TenantFWName']
        vlan_logical_name = nwa_data['NW_' + network_id + '_nwa_network_name']

        # delete fwaas ids on db.
        self._delete_fwaas_ids(context, device_name)

        rcode, body = self.client.update_tenant_fw(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            device_name,
            ipaddr,
            vlan_logical_name,
            vlan_type,
            connect='disconnect'
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("UpdateTenantFW(disconnect) SUCCEED.")
        else:
            LOG.error("UpdateTenantFW(disconnect) FAILED.")
            return False, {
                'status': 'FAILED',
                'msg': 'UpdateTenantFW(disconnect) FAILED.'
            }

        nwa_data.pop('DEV_' + device_id + '_' + network_id)
        nwa_data.pop('DEV_' + device_id + '_' + network_id + '_ip_address')
        nwa_data.pop('DEV_' + device_id + '_' + network_id + '_mac_address')
        nwa_data.pop('DEV_' + device_id + '_' + network_id + '_TenantFWName')
        nwa_data.pop('DEV_' + device_id + '_' + network_id + '_' + resource_group_name_nw)

        vp_net = 'VLAN_' + network_id + '_' + resource_group_name_nw + VLAN_OWN_TFW
        tfw_key = vp_net + '_FW_TFW' + device_id

        if tfw_key in nwa_data.keys():
            nwa_data.pop(tfw_key)

        if not check_segment_tfw(network_id, resource_group_name_nw, nwa_data):
            nwa_data.pop(vp_net)
            nwa_data.pop(vp_net + '_VlanID')

        return True, nwa_data

    def _delete_tenant_fw(self, context, **kwargs):
        """ Delete Tenant FW
        @param context: contains user information.
        @param kwargs: nwa_tenant_id, nwa_tenant_id, nwa_info, nwa_data
        @return: resutl(succeed = True, other = False), data(nwa_data or None)
        """
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        network_id = nwa_info['network']['id']
        device_id = nwa_info['device']['id']
        resource_group_name_nw = nwa_info['resource_group_name_nw']

        device_name = nwa_data['DEV_' + device_id + '_TenantFWName']

        if self.fwaas_driver:
            # set default setting.
            self._setting_fw_policy_all_deny(context, device_name, **kwargs)
            # delete fwaas ids on db.
            self._delete_fwaas_ids(context, device_name)

        device_type = 'TFW'
        rcode, body = self.client.delete_tenant_fw(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            device_name,
            device_type
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("DeleteTenantFW SUCCEED.")

            # delete recode
            dev_key = 'DEV_' + device_id
            nwa_data.pop(dev_key)
            nwa_data.pop(dev_key + '_device_owner')
            nwa_data.pop(dev_key + '_TenantFWName')
            nwa_data.pop(dev_key + '_' + network_id)
            nwa_data.pop(dev_key + '_' + network_id + '_ip_address')
            nwa_data.pop(dev_key + '_' + network_id + '_mac_address')
            nwa_data.pop(dev_key + '_' + network_id + '_TenantFWName')
            nwa_data.pop(dev_key + '_' + network_id + '_' + resource_group_name_nw)

            vp_net = 'VLAN_' + network_id + '_' + resource_group_name_nw + VLAN_OWN_TFW
            tfw_key = vp_net + '_FW_TFW' + device_id
            if tfw_key in nwa_data.keys():
                nwa_data.pop(tfw_key)

            if not check_segment_tfw(network_id, resource_group_name_nw, nwa_data):
                nwa_data.pop(vp_net)
                nwa_data.pop(vp_net + '_VlanID')

        else:
            msg = "DeleteTenantFW %s." % body['status']
            LOG.error(msg)
            return False, msg

        return True, nwa_data

    def delete_tenant_fw(self, context, **kwargs):
        """ Delete Tenant FireWall.
        @param context: contains user information.
        @param kwargs: tenant_id, nwa_tenant_id, nwa_info
        @return: dict of status and msg.
        """
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')

        network_id = nwa_info['network']['id']
        device_id = nwa_info['device']['id']

        nwa_data = self.nwa_core_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        # check tfw interface
        tfwif = "^DEV_" + device_id + '_.*_TenantFWName$'
        count = sum(not re.match(tfwif, k) is None for k in nwa_data.keys())

        if 1 < count:
            result, ret_val = self._update_tenant_fw(
                context,
                nwa_data=nwa_data,
                connect='disconnect',
                **kwargs
            )
            LOG.info("_update_tenant_fw(disconnect).ret_val=%s" % json.dumps(
                ret_val,
                indent=4,
                sort_keys=True
            ))
            if result is False:
                LOG.error("UpdateTenantFW disconnect FAILED")
            tfw_sgif = "^DEV_.*_" + network_id + '_TYPE$'
            sgif_count = sum(not re.match(tfw_sgif, k) is None for k in nwa_data.keys())
            if sgif_count:
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data
                )
        elif count == 1:
            # delete tenant fw
            result, ret_val = self._delete_tenant_fw(context, nwa_data=nwa_data, **kwargs)
            LOG.info("_delete_tenant_fw.ret_val=%s" % json.dumps(
                ret_val,
                indent=4,
                sort_keys=True
            ))
            if result is False:
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data
                )
            nwa_data = ret_val
            # delete tenant fw end.

        else:
            # error
            LOG.error("count miss match")
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )

        # port check on segment.
        if check_vlan(network_id, nwa_data):
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )

        # delete vlan
        result, ret_val = self._delete_vlan(context, nwa_data=nwa_data, **kwargs)
        LOG.info("_delete_vlan_fw.ret_val=%s" % json.dumps(
            ret_val,
            indent=4,
            sort_keys=True
        ))
        if result is False:
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete vlan end.

        # tenant network check.
        for k in nwa_data.keys():
            if re.match('NW_.*', k):
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data
                )

        # delete tenant network
        result, ret_val = self._delete_tenant_nw(context, nwa_data=nwa_data, **kwargs)
        LOG.info("_delete_tenant_nw.ret_val=%s" % json.dumps(
            ret_val,
            indent=4,
            sort_keys=True
        ))
        if result is False:
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete tenant network end

        # delete tenant
        result, ret_val = self._delete_tenant(context, nwa_data=nwa_data, **kwargs)
        LOG.info("_delete_tenant.ret_val=%s" % json.dumps(
            ret_val,
            indent=4,
            sort_keys=True
        ))
        if result is False:
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )

        LOG.info("delete_nwa_tenant_binding")
        return self.nwa_core_rpc.delete_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )
        # delete tenant end.

    def create_general_dev(self, context, **kwargs):
        """ Create GeneralDev wrapper.
        @param context: contains user information.
        @param kwargs:
        @return: dict of status and msg.
        """

        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')

        network_id = nwa_info['network']['id']
        device_owner = nwa_info['device']['owner']
        device_id = nwa_info['device']['id']
        port_id = nwa_info['port']['id']
        physical_network = nwa_info['physical_network']
        resource_group_name = nwa_info['resource_group_name']

        LOG.debug("tenant_id=%s, network_id=%s, device_owner=%s" % (
            tenant_id, network_id, device_owner
        ))

        nwa_data = self.nwa_core_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        nwa_created = False

        # create tenant
        if not nwa_data:
            rcode, nwa_data = self._create_tenant(context, **kwargs)
            LOG.info("_create_tenant.ret_val=%s" % json.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            if self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id,
                    nwa_data, nwa_created=True) is False:
                return None

        # create tenant nw
        if not KEY_CREATE_TENANT_NW in nwa_data.keys():
            rcode, ret_val = self._create_tenant_nw(context, nwa_data=nwa_data, **kwargs)
            LOG.info("_create_tenant_nw.ret_val=%s" % json.dumps(
                ret_val,
                indent=4,
                sort_keys=True
            ))
            if rcode is False:
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data, nwa_created=nwa_created
                )

        # create vlan
        nw_vlan_key = 'NW_' + network_id
        if not nw_vlan_key in nwa_data.keys():
            rcode, ret_val = self._create_vlan(context, nwa_data=nwa_data, **kwargs)
            LOG.info("_create_vlan.ret_val=%s" % json.dumps(
                ret_val,
                indent=4,
                sort_keys=True
            ))

            if rcode is False:
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data, nwa_created=nwa_created
                )

        # create general dev
        skip_generaldev = False

        """
        dev_key = 'DEV_.*_' + network_id + '_TYPE'
        for k in nwa_data.keys():
            if (
                    re.match(dev_key, k) and
                    nwa_data[k] == necnwa_utils.NWA_DEVICE_GDV
            ):
                skip_generaldev = True
        """
        if check_segment_gd(network_id, resource_group_name, nwa_data):
            skip_generaldev = True

        if skip_generaldev is False:
            rcode, ret_val = self._create_general_dev(context, nwa_data=nwa_data, **kwargs)
            if rcode is False:
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data, nwa_created=nwa_created
                )
            nwa_data = ret_val
            LOG.info("_create_general_dev.ret_val=%s" % json.dumps(
                ret_val,
                indent=4,
                sort_keys=True
            ))
        else:
            ret_val = self._create_general_dev_data(nwa_data=nwa_data, **kwargs)
            LOG.info("_create_general_dev_data.ret_val=%s" % json.dumps(
                ret_val,
                indent=4,
                sort_keys=True
            ))
            if ret_val:
                nwa_data = ret_val
            # agent waits for notifire issue for libviert.
            time.sleep(WAIT_AGENT_NOTIFIER)
        # create general dev end

        ret = self._update_tenant_binding(
            context, tenant_id, nwa_tenant_id, nwa_data, nwa_created=nwa_created
        )

        vlan_id = int(nwa_data['VLAN_' + network_id + '_' + resource_group_name + '_GD_VlanID'], 10)

        segment = {api.PHYSICAL_NETWORK: physical_network,
                   api.NETWORK_TYPE: n_constants.TYPE_VLAN,
                   api.SEGMENTATION_ID: vlan_id}

        self.nwa_core_rpc.update_port_state_with_notifire(
            context, device_id, self.agent_id, port_id, segment, network_id
        )

        return ret

    def _append_device_for_gdv(self, nwa_info, nwa_data):
        network_name = nwa_info['network']['name']
        network_id = nwa_info['network']['id']
        device_id = nwa_info['device']['id']
        device_owner = nwa_info['device']['owner']
        ipaddr = nwa_info['port']['ip']
        macaddr = nwa_info['port']['mac']
        resource_group_name = nwa_info['resource_group_name']

        dev_key = 'DEV_' + device_id
        nwa_data[dev_key] = 'device_id'
        nwa_data[dev_key + '_device_owner'] = device_owner

        net_key = dev_key + '_' + network_id
        nwa_data[net_key] = network_name
        nwa_data[net_key + '_ip_address'] = ipaddr
        nwa_data[net_key + '_mac_address'] = macaddr
        nwa_data[net_key + '_' + resource_group_name] = necnwa_utils.NWA_DEVICE_GDV

        return nwa_data

    def _create_general_dev_data(self, **kwargs):
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        self._append_device_for_gdv(nwa_info, nwa_data)

        return nwa_data

    def _create_general_dev(self, context, **kwargs):
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        network_id = nwa_info['network']['id']
        resource_group_name = nwa_info['resource_group_name']

        vlan_key = 'VLAN_' + network_id + '_' + resource_group_name
        port_type = None

        logical_name = nwa_data['NW_' + network_id + '_nwa_network_name']
        rcode, body = self.client.create_general_dev(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            resource_group_name,
            logical_name,
            port_type=port_type
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("CreateGeneralDev SUCCEED")

            vlan_key = 'VLAN_' + network_id
            if not vlan_key in nwa_data.keys():
                LOG.error("not create vlan.")
                return False, None

            seg_key = 'VLAN_' + network_id + '_' + resource_group_name + VLAN_OWN_GDV
            if nwa_data[vlan_key + '_CreateVlan'] == '':
                nwa_data[seg_key + '_VlanID'] = body['resultdata']['VlanID']
            else:
                nwa_data[seg_key + '_VlanID'] = nwa_data[vlan_key + '_VlanID']
            nwa_data[seg_key] = 'physical_network'

            self._append_device_for_gdv(nwa_info, nwa_data)
        else:
            LOG.debug("CreateGeneralDev %s" % body['status'])
            return False, None

        return True, nwa_data

    def delete_general_dev(self, context, **kwargs):
        """ Delete GeneralDev.
        @param context: contains user information.
        @param kwargs:
        @return: dict of status and msg.
        """
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        network_id = nwa_info['network']['id']
        resource_group_name = nwa_info['resource_group_name']

        nwa_data = self.nwa_core_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        # rpc return empty.
        if not nwa_data:
            LOG.error('nwa_tenant_binding not found. '
                      'tenant_id=%s, nwa_tenant_id=%s' % (tenant_id,
                                                          nwa_tenant_id))
            return {'result': 'FAILED'}

        gd_count = check_segment_gd(network_id, resource_group_name, nwa_data)

        if 1 < gd_count:
            nwa_data = self._delete_general_dev_data(nwa_data=nwa_data, **kwargs)
            LOG.info("_delete_general_dev_data.ret_val=%s" % json.dumps(
                nwa_data,
                indent=4,
                sort_keys=True
            ))
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )

        # delete general dev
        rcode, ret_val = self._delete_general_dev(context, nwa_data=nwa_data, **kwargs)
        LOG.info("_delete_general_dev.ret_val=%s" % json.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))
        if rcode is False:
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete general dev end

        # port check on segment.
        if check_vlan(network_id, nwa_data):
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )

        # delete vlan
        result, ret_val = self._delete_vlan(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        LOG.info("_delete_vlan.ret_val=%s" % json.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))

        if result is False:
            # delete vlan error.
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete vlan end.

        # tenant network check.
        for k in nwa_data.keys():
            if re.match('NW_.*', k):
                return self._update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data
                )

        # delete tenant network
        LOG.info("delete_tenant_nw")
        result, ret_val = self._delete_tenant_nw(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        LOG.info("_delete_tenant_nw.ret_val=%s" % json.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))
        if result is False:
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete tenant network end

        # delete tenant
        LOG.info("delete_tenant")
        result, ret_val = self._delete_tenant(
            context,
            nwa_data=nwa_data,
            **kwargs
        )
        if result is False:
            return self._update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        nwa_data = ret_val
        # delete tenant end.

        # delete nwa_tenant binding.
        LOG.info("delete_nwa_tenant_binding")
        return self.nwa_core_rpc.delete_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

    def _delete_general_dev_data(self, **kwargs):
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        device_id = nwa_info['device']['id']
        network_id = nwa_info['network']['id']
        resource_group_name = nwa_info['resource_group_name']

        vp_net = 'VLAN_' + network_id + '_' + resource_group_name + VLAN_OWN_GDV

        dev_key = 'DEV_' + device_id
        if dev_key in nwa_data.keys():
            nwa_data.pop(dev_key + '_' + network_id)
            nwa_data.pop(dev_key + '_' + network_id + '_ip_address')
            nwa_data.pop(dev_key + '_' + network_id + '_mac_address')
            nwa_data.pop(dev_key + '_' + network_id + '_' + resource_group_name)
            if count_device_id(device_id, nwa_data) == 1:
                nwa_data.pop(dev_key)
                nwa_data.pop(dev_key + '_device_owner')

        if not check_segment_gd(network_id, resource_group_name, nwa_data):
            nwa_data.pop(vp_net)
            nwa_data.pop(vp_net + '_VlanID')

        return nwa_data

    def _delete_general_dev(self, context, **kwargs):
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')
        nwa_data = kwargs.get('nwa_data')

        network_id = nwa_info['network']['id']
        resource_group = nwa_info['resource_group_name']

        # delete general dev
        logical_name = nwa_data['NW_' + network_id + '_nwa_network_name']
        rcode, body = self.client.delete_general_dev(
            self._dummy_ok,
            self._dummy_ng,
            context,
            nwa_tenant_id,
            resource_group,
            logical_name,
        )
        if rcode != 200:
            LOG.debug("DeleteGeneralDev Error: invalid responce."
                      " rcode = %d" % rcode)
            """
            error port send to plugin
            """
            return False, None

        if (
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("DeleteGeneralDev SUCCEED")
            nwa_data = self._delete_general_dev_data(**kwargs)

        else:
            LOG.debug("DeleteGeneralDev %s" % body['status'])
            return False, None
        # delete general dev end

        return True, nwa_data

    def _update_tenant_binding(
            self, context, tenant_id, nwa_tenant_id,
            nwa_data, nwa_created=False
    ):
        """ Update Tenant Binding on NECNWACorePlugin.
        @param context:contains user information.
        @param tenant_id: Openstack Tenant UUID
        @param nwa_tenant_id: NWA Tenand ID
        @param nwa_data: nwa_tenant_binding data.
        @param nwa_created: flag of operation. True = Create, False = Update
        @return: dict of status and msg.
        """
        LOG.debug("nwa_data=%s" % json.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))
        if nwa_created is True:
            return self.nwa_core_rpc.add_nwa_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )

        return self.nwa_core_rpc.set_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id, nwa_data
        )

    def setting_nat(self, context, **kwargs):

        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        nwa_data = self.nwa_core_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        rcode, ret_val = self._setting_nat(context, nwa_data=nwa_data, **kwargs)
        self.nwa_core_rpc.update_floatingip_status(
            context,
            kwargs['floating']['id'],
            constants.FLOATINGIP_STATUS_ACTIVE if rcode is True else
            constants.FLOATINGIP_STATUS_ERROR
        )

        if rcode is False:
            # error.
            return None

        return self._update_tenant_binding(
            context, tenant_id, nwa_tenant_id, nwa_data,
        )

    def _setting_nat(self, context, **kwargs):
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')
        floating = kwargs.get('floating')

        # new code.(neet ut)
        nat_key = 'NAT_' + floating['id']
        if nat_key in nwa_data.keys():
            LOG.debug('already in use NAT key =%s' % nat_key)
            return False, None

        vlan_logical_name = nwa_data['NW_' + floating['floating_network_id'] + '_nwa_network_name']
        vlan_type = 'PublicVLAN'
        floating_ip = floating['floating_ip_address']
        fixed_ip = floating['fixed_ip_address']
        dev_name = nwa_data['DEV_' + floating['device_id'] + '_TenantFWName']

        # setting nat
        rcode, body = self.client.setting_nat(
            self._dummy_ok,
            self._dummy_ng,
            context, nwa_tenant_id,
            vlan_logical_name,
            vlan_type, fixed_ip, floating_ip, dev_name, data=floating
        )

        if rcode != 200:
            LOG.debug("SettingNat Error: invalid responce."
                      " rcode = %d" % rcode)
            return False, None

        if (
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("SettingNat SUCCEED")

            data = floating
            nwa_data['NAT_' + data['id']] = data['device_id']
            nwa_data['NAT_' + data['id'] + '_network_id'] = data['floating_network_id']
            nwa_data['NAT_' + data['id'] + '_floating_ip_address'] = data['floating_ip_address']
            nwa_data['NAT_' + data['id'] + '_fixed_ip_address'] = data['fixed_ip_address']

        else:
            LOG.debug("SettingNat %s" % body['status'])
            return False, None
        # setting nat end.

        return True, None

    def delete_nat(self, context, **kwargs):
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        nwa_data = self.nwa_core_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        rcode, ret_val = self._delete_nat(context, nwa_data=nwa_data, **kwargs)
        self.nwa_core_rpc.update_floatingip_status(
            context,
            kwargs['floating']['id'],
            constants.FLOATINGIP_STATUS_DOWN if rcode is True else
            constants.FLOATINGIP_STATUS_ERROR
        )

        if rcode is False:
            # error.
            return None

        return self._update_tenant_binding(
            context, tenant_id, nwa_tenant_id, nwa_data,
        )

    def _delete_nat(self, context, **kwargs):
        LOG.debug("context=%s, kwargs=%s" % (context, kwargs))
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')
        floating = kwargs.get('floating')

        vlan_logical_name = nwa_data['NW_' + floating['floating_network_id'] + '_nwa_network_name']
        vlan_type = 'PublicVLAN'
        floating_ip = floating['floating_ip_address']
        fixed_ip = floating['fixed_ip_address']
        dev_name = nwa_data['DEV_' + floating['device_id'] + '_TenantFWName']

        # setting nat
        rcode, body = self.client.delete_nat(
            self._dummy_ok,
            self._dummy_ng,
            context, nwa_tenant_id,
            vlan_logical_name,
            vlan_type, fixed_ip, floating_ip, dev_name, data=floating
        )

        if rcode != 200:
            LOG.debug("DeleteNat Error: invalid responce."
                      " rcode = %d" % rcode)
            return False, None

        if (
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("DeleteNat SUCCEED")

            data = floating
            nwa_data.pop('NAT_' + data['id'])
            nwa_data.pop('NAT_' + data['id'] + '_network_id')
            nwa_data.pop('NAT_' + data['id'] + '_floating_ip_address')
            nwa_data.pop('NAT_' + data['id'] + '_fixed_ip_address')

        else:
            LOG.debug("DeleteNat %s" % body['status'])
            return False, None
        # setting nat end.

        return True, None

    def _setting_fw_policy_all_deny(self, context, tfw, **kwargs):

        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        rcode, body = self.client.setting_fw_policy(
            nwa_tenant_id,
            tfw,
            all_deny_policies
        )
        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("success body=%s" % body)
        else:
            LOG.debug("success error=%s" % body)

    def _setting_fw_policy_all_permit(self, context, tfw, **kwargs):

        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        rcode, body = self.client.setting_fw_policy(
            nwa_tenant_id,
            tfw,
            all_permit_policies
        )

        if (
                rcode == 200 and
                body['status'] == 'SUCCEED'
        ):
            LOG.debug("success body=%s" % body)
        else:
            LOG.debug("success error=%s" % body)

    def _dummy_ok(self, context, rcode, jbody, *args, **kargs):
        pass

    def _dummy_ng(self, context, rcode, jbody, *args, **kargs):
        pass


def main():
    logging_config.init(sys.argv[1:])
    logging_config.setup_logging()

    polling_interval = config.AGENT.polling_interval
    agent = NECNWANeutronAgent(polling_interval)

    agent.daemon_loop()

if __name__ == "__main__":
    main()
