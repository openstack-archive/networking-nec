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

from neutron.common import topics
from neutron.plugins.common import constants as n_constants
from neutron.plugins.ml2 import driver_api as api
from neutron_lib import constants
from oslo_log import helpers
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec._i18n import _LE, _LI, _LW
from networking_nec.plugins.necnwa.agent.nwa_l2_network import NwaL2Network
import networking_nec.plugins.necnwa.agent.proxy_l2 as l2
import networking_nec.plugins.necnwa.common.constants as nwa_const
from networking_nec.plugins.necnwa.l2.rpc import nwa_l2_server_api
from networking_nec.plugins.necnwa.l2.rpc import tenant_binding_api
from networking_nec.plugins.necnwa.l3.rpc import nwa_l3_server_api


LOG = logging.getLogger(__name__)

VLAN_OWN_TFW = '_TFW'


# pylint: disable=too-many-instance-attributes
class AgentProxyL3(object):

    def __init__(self, agent_top, client, proxy_tenant, proxy_l2,
                 tenant_fw_create_hook=None,
                 tenant_fw_delete_hook=None,
                 tenant_fw_connect_hook=None,
                 tenant_fw_disconnect_hook=None):
        self.nwa_tenant_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN)
        self.nwa_l2_rpc = nwa_l2_server_api.NwaL2ServerRpcApi(topics.PLUGIN)
        self.nwa_l3_rpc = nwa_l3_server_api.NwaL3ServerRpcApi(topics.PLUGIN)
        self.agent_top = agent_top
        self.client = client
        self.proxy_tenant = proxy_tenant
        self.nwa_l2_network = NwaL2Network(self.nwa_tenant_rpc, proxy_tenant,
                                           proxy_l2)
        self.tenant_fw_create_hook = tenant_fw_create_hook
        self.tenant_fw_delete_hook = tenant_fw_delete_hook
        self.tenant_fw_connect_hook = tenant_fw_connect_hook
        self.tenant_fw_disconnect_hook = tenant_fw_disconnect_hook

    @helpers.log_method_call
    def create_tenant_fw(self, context, **kwargs):
        nwa_data = self.nwa_l2_network.start(context, **kwargs)
        dev_key = 'DEV_' + kwargs['nwa_info']['device']['id']
        net_key = dev_key + '_' + kwargs['nwa_info']['network']['id']
        if dev_key not in nwa_data:
            nwa_data = self._create_tenant_fw(nwa_data, context, **kwargs)
        elif net_key not in nwa_data:
            nwa_data = self._create_tenant_fw(nwa_data, context, **kwargs)
        else:
            LOG.warning(_LW("unknown device."))

        if not nwa_data:
            return self.proxy_tenant.update_tenant_binding(
                context,
                kwargs['tenant_id'], kwargs['nwa_tenant_id'],
                kwargs['nwa_data'], nwa_created=False
            )
        ret = self.proxy_tenant.update_tenant_binding(
            context,
            kwargs['tenant_id'], kwargs['nwa_tenant_id'],
            nwa_data, nwa_created=False
        )
        vlan_id = int(nwa_data['VLAN_' +
                               kwargs['nwa_info']['network']['id'] +
                               '_' +
                               kwargs['nwa_info']['resource_group_name_nw'] +
                               VLAN_OWN_TFW +
                               '_VlanID'],
                      10)
        self.nwa_l2_rpc.update_port_state_with_notifier(
            context,
            kwargs['nwa_info']['device']['id'],
            self.agent_top.agent_id,
            kwargs['nwa_info']['port']['id'],
            {
                api.PHYSICAL_NETWORK: kwargs['nwa_info']['physical_network'],
                api.NETWORK_TYPE: n_constants.TYPE_VLAN,
                api.SEGMENTATION_ID: vlan_id
            },
            kwargs['nwa_info']['network']['id']
        )
        return ret

    def _create_tenant_fw(self, nwa_data, context, **kwargs):
        network_id = kwargs['nwa_info']['network']['id']
        rcode, body = self.client.create_tenant_fw(
            kwargs['nwa_tenant_id'],
            kwargs['nwa_info']['resource_group_name'],
            kwargs['nwa_info']['port']['ip'],
            nwa_data['NW_' + network_id + '_nwa_network_name'],
            kwargs['nwa_info']['network']['vlan_type']
        )
        if rcode != 200 or body['status'] != 'SUCCESS':
            return None

        LOG.debug("CreateTenantFW SUCCESS.")

        dev_key = 'DEV_' + kwargs['nwa_info']['device']['id']
        net_key = dev_key + '_' + kwargs['nwa_info']['network']['id']
        tfw_name = body['resultdata']['TenantFWName']
        resource_group_name_nw = kwargs['nwa_info']['resource_group_name_nw']

        nwa_data[dev_key] = 'device_id'
        nwa_data[dev_key +
                 '_device_owner'] = kwargs['nwa_info']['device']['owner']
        nwa_data[dev_key + '_TenantFWName'] = tfw_name

        nwa_data[net_key] = kwargs['nwa_info']['network']['name']
        nwa_data[net_key + '_ip_address'] = kwargs['nwa_info']['port']['ip']
        nwa_data[net_key + '_mac_address'] = kwargs['nwa_info']['port']['mac']
        nwa_data[net_key + '_' +
                 resource_group_name_nw] = nwa_const.NWA_DEVICE_TFW
        nwa_data[net_key + '_TenantFWName'] = tfw_name

        vlan_key = 'VLAN_' + network_id
        seg_key = ('VLAN_' + network_id + '_' +
                   resource_group_name_nw + VLAN_OWN_TFW)

        if nwa_data[vlan_key + '_CreateVlan'] == '':
            nwa_data[seg_key + '_VlanID'] = body['resultdata']['VlanID']
        else:
            nwa_data[seg_key + '_VlanID'] = nwa_data[vlan_key + '_VlanID']
        nwa_data[seg_key] = 'physical_network'

        LOG.info(_LI("_create_tenant_fw.ret_val=%s"), jsonutils.dumps(
            nwa_data,
            indent=4,
            sort_keys=True
        ))

        if self.tenant_fw_create_hook:
            self.tenant_fw_create_hook(context, tfw_name, **kwargs)
        return nwa_data

    def _update_tenant_fw(self, context, **kwargs):
        connect = kwargs.get('connect')
        if connect == 'connect':
            rcode, body = self._update_tenant_fw_connect(context, **kwargs)
        else:                   # connect == 'disconnect'
            rcode, body = self._update_tenant_fw_disconnect(context, **kwargs)
        if rcode != 200 or body['status'] != 'SUCCESS':
            return None
        return kwargs['nwa_data']

    def _update_tenant_fw_connect(self, context, **kwargs):
        nwa_data = kwargs.get('nwa_data')

        device_id = kwargs['nwa_info']['device']['id']
        network_id = kwargs['nwa_info']['network']['id']

        rcode, body = self.client.update_tenant_fw(
            kwargs['nwa_tenant_id'],
            nwa_data['DEV_' + device_id + '_TenantFWName'],
            kwargs['nwa_info']['port']['ip'],
            nwa_data['NW_' + network_id + '_nwa_network_name'],
            kwargs['nwa_info']['network']['vlan_type'],
            connect='connect')

        if rcode != 200 or body['status'] != 'SUCCESS':
            return False, None

        LOG.debug("UpdateTenantFW succeed.")
        resource_group_name_nw = kwargs['nwa_info']['resource_group_name_nw']
        tfw_name = body['resultdata']['TenantFWName']
        net_key = 'DEV_' + device_id + '_' + network_id
        nwa_data[net_key] = kwargs['nwa_info']['network']['name']
        nwa_data[net_key + '_ip_address'] = kwargs['nwa_info']['port']['ip']
        nwa_data[net_key + '_mac_address'] = kwargs['nwa_info']['port']['mac']
        nwa_data[net_key + '_TenantFWName'] = tfw_name
        nwa_data[net_key + '_' +
                 resource_group_name_nw] = nwa_const.NWA_DEVICE_TFW

        vlan_key = 'VLAN_' + network_id
        seg_key = ('VLAN_' + network_id + '_' +
                   resource_group_name_nw + VLAN_OWN_TFW)
        if nwa_data[vlan_key + '_CreateVlan'] == '':
            nwa_data[seg_key + '_VlanID'] = body['resultdata']['VlanID']
        else:
            nwa_data[seg_key + '_VlanID'] = nwa_data[vlan_key + '_VlanID']
        nwa_data[seg_key] = 'physical_network'
        if self.tenant_fw_connect_hook:
            self.tenant_fw_connect_hook(context, tfw_name, **kwargs)
        return True, nwa_data

    @helpers.log_method_call
    def _update_tenant_fw_disconnect(self, context, **kwargs):
        """Update Tenant FW

        @param context: contains user information.
        @param kwargs:
        @return: result(succeed = True, other = False), data(nwa_data or None)
        """
        nwa_data = kwargs.get('nwa_data')

        device_id = kwargs['nwa_info']['device']['id']
        network_id = kwargs['nwa_info']['network']['id']
        device_name = nwa_data['DEV_' + device_id + '_TenantFWName']

        if self.tenant_fw_disconnect_hook:
            self.tenant_fw_disconnect_hook(context, device_name, **kwargs)

        rcode, body = self.client.update_tenant_fw(
            kwargs['nwa_tenant_id'],
            device_name,
            kwargs['nwa_info']['port']['ip'],
            nwa_data['NW_' + network_id + '_nwa_network_name'],
            kwargs['nwa_info']['network']['vlan_type'],
            connect='disconnect'
        )
        if rcode != 200 or body['status'] != 'SUCCESS':
            LOG.error(_LE("UpdateTenantFW(disconnect) FAILED."))
            return False, {
                'status': 'FAILED',
                'msg': 'UpdateTenantFW(disconnect) FAILED.'
            }

        LOG.debug("UpdateTenantFW(disconnect) SUCCESS.")
        resource_group_name_nw = kwargs['nwa_info']['resource_group_name_nw']
        net_key = 'DEV_' + device_id + '_' + network_id
        nwa_data.pop(net_key)
        nwa_data.pop(net_key + '_ip_address')
        nwa_data.pop(net_key + '_mac_address')
        nwa_data.pop(net_key + '_TenantFWName')
        nwa_data.pop(net_key + '_' + resource_group_name_nw)

        vp_net = ('VLAN_' + network_id + '_' + resource_group_name_nw +
                  VLAN_OWN_TFW)
        tfw_key = vp_net + '_FW_TFW' + device_id

        if tfw_key in nwa_data.keys():
            nwa_data.pop(tfw_key)

        if not l2.check_segment_tfw(network_id, resource_group_name_nw,
                                    nwa_data):
            nwa_data.pop(vp_net)
            nwa_data.pop(vp_net + '_VlanID')
        return True, nwa_data

    @helpers.log_method_call
    def _delete_tenant_fw(self, context, **kwargs):
        """Delete Tenant FW

        @param context: contains user information.
        @param kwargs: nwa_tenant_id, nwa_tenant_id, nwa_info, nwa_data
        @return: resutl(succeed = True, other = False), data(nwa_data or None)
        """
        nwa_data = kwargs.get('nwa_data')

        network_id = kwargs['nwa_info']['network']['id']
        device_id = kwargs['nwa_info']['device']['id']

        device_name = nwa_data['DEV_' + device_id + '_TenantFWName']
        if self.tenant_fw_delete_hook:
            self.tenant_fw_delete_hook(context, device_name, **kwargs)

        rcode, body = self.client.delete_tenant_fw(
            kwargs['nwa_tenant_id'],
            device_name,
            'TFW'
        )
        if rcode != 200 or body['status'] != 'SUCCESS':
            msg = _LE("DeleteTenantFW %s."), body['status']
            LOG.error(msg)
            return False, msg

        LOG.debug("DeleteTenantFW SUCCESS.")

        resource_group_name_nw = kwargs['nwa_info']['resource_group_name_nw']
        # delete recode
        dev_key = 'DEV_' + device_id
        net_key = dev_key + '_' + network_id
        nwa_data.pop(dev_key)
        nwa_data.pop(dev_key + '_device_owner')
        nwa_data.pop(dev_key + '_TenantFWName')

        nwa_data.pop(net_key)
        nwa_data.pop(net_key + '_ip_address')
        nwa_data.pop(net_key + '_mac_address')
        nwa_data.pop(net_key + '_TenantFWName')
        nwa_data.pop(net_key + '_' + resource_group_name_nw)

        vp_net = ('VLAN_' + network_id + '_' + resource_group_name_nw +
                  VLAN_OWN_TFW)
        tfw_key = vp_net + '_FW_TFW' + device_id
        if tfw_key in nwa_data.keys():
            nwa_data.pop(tfw_key)

        if not l2.check_segment_tfw(network_id, resource_group_name_nw,
                                    nwa_data):
            nwa_data.pop(vp_net)
            nwa_data.pop(vp_net + '_VlanID')
        return True, nwa_data

    @helpers.log_method_call
    def delete_tenant_fw(self, context, **kwargs):
        """Delete Tenant FireWall.

        @param context: contains user information.
        @param kwargs: tenant_id, nwa_tenant_id, nwa_info
        @return: dict of status and msg.
        """
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_info = kwargs.get('nwa_info')

        network_id = nwa_info['network']['id']
        device_id = nwa_info['device']['id']

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
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
            LOG.info(_LI("_update_tenant_fw(disconnect).ret_val=%s") %
                     jsonutils.dumps(
                         ret_val,
                         indent=4,
                         sort_keys=True))
            if result is False:
                LOG.error(_LE("UpdateTenantFW disconnect FAILED"))
            tfw_sgif = "^DEV_.*_" + network_id + '_TYPE$'
            sgif_count = sum(not re.match(tfw_sgif, k) is None
                             for k in nwa_data.keys())
            if sgif_count:
                return self.proxy_tenant.update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data
                )
        elif count == 1:
            # delete tenant fw
            result, ret_val = self._delete_tenant_fw(
                context, nwa_data=nwa_data, **kwargs)
            LOG.info(_LI("_delete_tenant_fw.ret_val=%s"), jsonutils.dumps(
                ret_val,
                indent=4,
                sort_keys=True
            ))
            if result is False:
                return self.proxy_tenant.update_tenant_binding(
                    context, tenant_id, nwa_tenant_id, nwa_data
                )
            nwa_data = ret_val
            # delete tenant fw end.

        else:
            # error
            LOG.error(_LE("count miss match"))
            return self.proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, nwa_data
            )
        return self.nwa_l2_network.terminate(context, **kwargs)

    @helpers.log_method_call
    def setting_nat(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        rc, ret_val = self._setting_nat(context, nwa_data=nwa_data, **kwargs)
        self._update_floatingip_status(rc, context, kwargs['floating']['id'])
        if not rc:
            return None
        else:
            return self.proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, ret_val
            )

    @helpers.log_method_call
    def _setting_nat(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')
        floating = kwargs.get('floating')

        # new code.(neet ut)
        nat_key = 'NAT_' + floating['id']
        if nat_key in nwa_data:
            LOG.debug('already in use NAT key =%s', nat_key)
            return False, None

        vlan_logical_name = nwa_data['NW_' +
                                     floating['floating_network_id'] +
                                     '_nwa_network_name']
        vlan_type = 'PublicVLAN'
        floating_ip = floating['floating_ip_address']
        fixed_ip = floating['fixed_ip_address']
        dev_name = nwa_data['DEV_' + floating['device_id'] + '_TenantFWName']

        # setting nat
        rcode, body = self.client.setting_nat(
            nwa_tenant_id,
            vlan_logical_name,
            vlan_type, fixed_ip, floating_ip, dev_name, data=floating
        )

        if rcode != 200 or body['status'] != 'SUCCESS':
            LOG.debug("SettingNat Error: invalid responce."
                      " rcode=%d status=%s" % (rcode, body))
            return False, None
        else:
            LOG.debug("SettingNat SUCCESS")
            data = floating
            nwa_data['NAT_' + data['id']] = data['device_id']
            nwa_data['NAT_' + data['id'] +
                     '_network_id'] = data['floating_network_id']
            nwa_data['NAT_' + data['id'] +
                     '_floating_ip_address'] = data['floating_ip_address']
            nwa_data['NAT_' + data['id'] +
                     '_fixed_ip_address'] = data['fixed_ip_address']
            return True, nwa_data

    @helpers.log_method_call
    def delete_nat(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id
        )

        rc, ret_val = self._delete_nat(context, nwa_data=nwa_data, **kwargs)
        self._update_floatingip_status(rc, context, kwargs['floating']['id'])
        if not rc:
            return None
        else:
            return self.proxy_tenant.update_tenant_binding(
                context, tenant_id, nwa_tenant_id, ret_val
            )

    @helpers.log_method_call
    def _delete_nat(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')
        floating = kwargs.get('floating')

        vlan_logical_name = nwa_data[
            'NW_' + floating['floating_network_id'] + '_nwa_network_name']
        vlan_type = 'PublicVLAN'
        floating_ip = floating['floating_ip_address']
        fixed_ip = floating['fixed_ip_address']
        dev_name = nwa_data['DEV_' + floating['device_id'] + '_TenantFWName']

        # setting nat
        rcode, body = self.client.delete_nat(
            nwa_tenant_id,
            vlan_logical_name,
            vlan_type, fixed_ip, floating_ip, dev_name, data=floating
        )
        if rcode != 200 or body['status'] != 'SUCCESS':
            LOG.debug("DeleteNat Error: invalid responce."
                      " rcode=%d status=%s" % (rcode, body))
            return False, None
        else:
            LOG.debug("DeleteNat SUCCESS")
            data = floating
            nwa_data.pop('NAT_' + data['id'])
            nwa_data.pop('NAT_' + data['id'] + '_network_id')
            nwa_data.pop('NAT_' + data['id'] + '_floating_ip_address')
            nwa_data.pop('NAT_' + data['id'] + '_fixed_ip_address')
            return True, nwa_data

    def _update_floatingip_status(self, rcode, context, floatingip_id):
        self.nwa_l3_rpc.update_floatingip_status(
            context, floatingip_id,
            constants.FLOATINGIP_STATUS_ACTIVE if rcode else
            constants.FLOATINGIP_STATUS_ERROR
        )
