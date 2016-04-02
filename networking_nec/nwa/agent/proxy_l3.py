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

from networking_nec._i18n import _LE, _LW
from networking_nec.common import utils
from networking_nec.nwa.agent import proxy_l2 as l2
from networking_nec.nwa.agent import proxy_tenant as tenant_util
from networking_nec.nwa.common import constants as nwa_const
from networking_nec.nwa.common import exceptions as nwa_exc
from networking_nec.nwa.l2.rpc import nwa_l2_server_api
from networking_nec.nwa.l2.rpc import tenant_binding_api
from networking_nec.nwa.l3.rpc import nwa_l3_server_api
from networking_nec.nwa.nwalib import data_utils


LOG = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class AgentProxyL3(object):

    def __init__(self, agent_top, client,
                 tenant_fw_create_hook=None,
                 tenant_fw_delete_hook=None,
                 tenant_fw_connect_hook=None,
                 tenant_fw_disconnect_hook=None):
        self.nwa_tenant_rpc = tenant_binding_api.TenantBindingServerRpcApi(
            topics.PLUGIN)
        self.nwa_l2_rpc = nwa_l2_server_api.NwaL2ServerRpcApi(topics.PLUGIN)
        self.nwa_l3_rpc = nwa_l3_server_api.NwaL3ServerRpcApi(topics.L3PLUGIN)
        self.agent_top = agent_top
        self.client = client
        self.tenant_fw_create_hook = tenant_fw_create_hook
        self.tenant_fw_delete_hook = tenant_fw_delete_hook
        self.tenant_fw_connect_hook = tenant_fw_connect_hook
        self.tenant_fw_disconnect_hook = tenant_fw_disconnect_hook

    @property
    def proxy_tenant(self):
        return self.agent_top.proxy_tenant

    @property
    def proxy_l2(self):
        return self.agent_top.proxy_l2

    @helpers.log_method_call
    @tenant_util.catch_exception_and_update_tenant_binding
    def create_tenant_fw(self, context, **kwargs):
        nwa_data = self.proxy_l2.ensure_l2_network(context, **kwargs)
        device_id = kwargs['nwa_info']['device']['id']
        network_id = kwargs['nwa_info']['network']['id']
        dev_key = data_utils.get_device_key(device_id)
        net_key = data_utils.get_device_net_key(device_id, network_id)
        if dev_key not in nwa_data:
            nwa_data = self._create_tenant_fw(nwa_data, context, **kwargs)
        elif net_key not in nwa_data:
            nwa_data = self._update_tenant_fw(
                context, connect='connect', nwa_data=nwa_data, **kwargs)
        else:
            LOG.warning(_LW("unknown device."))

        if not nwa_data:
            raise nwa_exc.AgentProxyException(value=kwargs['nwa_data'])
        ret = self.proxy_tenant.update_tenant_binding(
            context,
            kwargs['tenant_id'], kwargs['nwa_tenant_id'],
            nwa_data
        )
        resource_group_name_nw = kwargs['nwa_info']['resource_group_name_nw']
        vlan_id = data_utils.get_vp_net_vlan_id(nwa_data, network_id,
                                                resource_group_name_nw,
                                                nwa_const.NWA_DEVICE_TFW)

        self.nwa_l2_rpc.update_port_state_with_notifier(
            context,
            device_id,
            self.agent_top.agent_id,
            kwargs['nwa_info']['port']['id'],
            {
                api.PHYSICAL_NETWORK: kwargs['nwa_info']['physical_network'],
                api.NETWORK_TYPE: n_constants.TYPE_VLAN,
                api.SEGMENTATION_ID: vlan_id
            },
            network_id
        )
        return ret

    @utils.log_method_return_value
    def _create_tenant_fw(self, nwa_data, context, **kwargs):
        device_id = kwargs['nwa_info']['device']['id']
        network_id = kwargs['nwa_info']['network']['id']
        rcode, body = self.client.l3.create_tenant_fw(
            kwargs['nwa_tenant_id'],
            kwargs['nwa_info']['resource_group_name'],
            kwargs['nwa_info']['port']['ip'],
            data_utils.get_vlan_logical_name(nwa_data, network_id),
            kwargs['nwa_info']['network']['vlan_type']
        )
        if rcode != 200 or body['status'] != 'SUCCEED':
            return None

        LOG.debug("CreateTenantFW SUCCEED.")

        tfw_name = body['resultdata']['TenantFWName']
        resource_group_name_nw = kwargs['nwa_info']['resource_group_name_nw']

        data_utils.set_tfw_device_data(nwa_data, device_id,
                                       tfw_name, kwargs['nwa_info'])
        data_utils.set_tfw_interface_data(nwa_data, device_id, network_id,
                                          resource_group_name_nw,
                                          tfw_name, kwargs['nwa_info'])
        vlan_id = data_utils.get_vlan_id(network_id, nwa_data,
                                         body['resultdata'])
        data_utils.set_vp_net_data(nwa_data, network_id,
                                   resource_group_name_nw,
                                   nwa_const.NWA_DEVICE_TFW,
                                   vlan_id)

        if self.tenant_fw_create_hook:
            self.tenant_fw_create_hook(context, tfw_name, **kwargs)
        return nwa_data

    @utils.log_method_return_value
    def _update_tenant_fw(self, context, **kwargs):
        connect = kwargs.get('connect')
        try:
            if connect == 'connect':
                self._update_tenant_fw_connect(context, **kwargs)
            else:                   # connect == 'disconnect'
                self._update_tenant_fw_disconnect(context, **kwargs)
        except nwa_exc.AgentProxyException:
            return
        return kwargs['nwa_data']

    def _update_tenant_fw_connect(self, context, **kwargs):
        nwa_data = kwargs.get('nwa_data')

        device_id = kwargs['nwa_info']['device']['id']
        network_id = kwargs['nwa_info']['network']['id']

        rcode, body = self.client.l3.update_tenant_fw(
            kwargs['nwa_tenant_id'],
            data_utils.get_tfw_device_name(nwa_data, device_id),
            kwargs['nwa_info']['port']['ip'],
            data_utils.get_vlan_logical_name(nwa_data, network_id),
            kwargs['nwa_info']['network']['vlan_type'],
            connect='connect')

        if rcode != 200 or body['status'] != 'SUCCEED':
            raise nwa_exc.AgentProxyException(value=None)

        LOG.debug("UpdateTenantFW succeed.")
        resource_group_name_nw = kwargs['nwa_info']['resource_group_name_nw']
        tfw_name = body['resultdata']['TenantFWName']

        data_utils.set_tfw_interface_data(nwa_data, device_id, network_id,
                                          resource_group_name_nw,
                                          tfw_name, kwargs['nwa_info'])
        vlan_id = data_utils.get_vlan_id(network_id, nwa_data,
                                         body['resultdata'])
        data_utils.set_vp_net_data(nwa_data, network_id,
                                   resource_group_name_nw,
                                   nwa_const.NWA_DEVICE_TFW,
                                   vlan_id)

        if self.tenant_fw_connect_hook:
            self.tenant_fw_connect_hook(context, tfw_name, **kwargs)
        return nwa_data

    @helpers.log_method_call
    def _update_tenant_fw_disconnect(self, context, **kwargs):
        """Update Tenant FW

        @param context: contains user information.
        @param kwargs:
        @return: nwa_data
        @raise AgentProxyException
        """
        nwa_data = kwargs.get('nwa_data')

        device_id = kwargs['nwa_info']['device']['id']
        network_id = kwargs['nwa_info']['network']['id']
        device_name = data_utils.get_tfw_device_name(nwa_data, device_id)

        if self.tenant_fw_disconnect_hook:
            self.tenant_fw_disconnect_hook(context, device_name, **kwargs)

        rcode, body = self.client.l3.update_tenant_fw(
            kwargs['nwa_tenant_id'],
            device_name,
            kwargs['nwa_info']['port']['ip'],
            data_utils.get_vlan_logical_name(nwa_data, network_id),
            kwargs['nwa_info']['network']['vlan_type'],
            connect='disconnect'
        )
        if rcode != 200 or body['status'] != 'SUCCEED':
            LOG.error(_LE("UpdateTenantFW(disconnect) FAILED."))
            info = {'status': 'FAILED',
                    'msg': 'UpdateTenantFW(disconnect) FAILED.'}
            raise nwa_exc.AgentProxyException(value=info)

        LOG.debug("UpdateTenantFW(disconnect) SUCCEED.")
        resource_group_name_nw = kwargs['nwa_info']['resource_group_name_nw']

        data_utils.strip_interface_data(nwa_data, device_id, network_id,
                                        resource_group_name_nw)
        data_utils.strip_tfw_data_if_exist(nwa_data, device_id, network_id,
                                           resource_group_name_nw)

        if not l2.check_segment_tfw(network_id, resource_group_name_nw,
                                    nwa_data):
            data_utils.strip_vp_net_data(nwa_data, network_id,
                                         resource_group_name_nw,
                                         nwa_const.NWA_DEVICE_TFW)
        return nwa_data

    @helpers.log_method_call
    def _delete_tenant_fw(self, context, **kwargs):
        """Delete Tenant FW

        @param context: contains user information.
        @param kwargs: nwa_tenant_id, nwa_tenant_id, nwa_info, nwa_data
        @return: resutl(succeed = True, other = False), data(nwa_data or None)
        """
        nwa_data = kwargs.get('nwa_data')
        nwa_info = kwargs['nwa_info']

        network_id = nwa_info['network']['id']
        device_id = nwa_info['device']['id']

        device_name = data_utils.get_tfw_device_name(nwa_data, device_id)
        if self.tenant_fw_delete_hook:
            self.tenant_fw_delete_hook(context, device_name, **kwargs)

        rcode, body = self.client.l3.delete_tenant_fw(
            kwargs['nwa_tenant_id'],
            device_name,
            'TFW'
        )
        if rcode != 200 or body['status'] != 'SUCCEED':
            msg = _LE("DeleteTenantFW %s."), body['status']
            LOG.error(msg)
            raise nwa_exc.AgentProxyException(value=nwa_data)

        LOG.debug("DeleteTenantFW SUCCEED.")

        resource_group_name_nw = nwa_info['resource_group_name_nw']
        # delete recode
        data_utils.strip_device_data(nwa_data, device_id)
        data_utils.strip_interface_data(nwa_data, device_id, network_id,
                                        resource_group_name_nw)
        data_utils.strip_tfw_data_if_exist(nwa_data, device_id, network_id,
                                           resource_group_name_nw)

        if not l2.check_segment_tfw(network_id, resource_group_name_nw,
                                    nwa_data):
            data_utils.strip_vp_net_data(nwa_data, network_id,
                                         resource_group_name_nw,
                                         nwa_const.NWA_DEVICE_TFW)
        return nwa_data

    @utils.log_method_return_value
    @helpers.log_method_call
    @tenant_util.catch_exception_and_update_tenant_binding
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
            ret_val = self._update_tenant_fw(
                context,
                nwa_data=nwa_data,
                connect='disconnect',
                **kwargs
            )
            if not ret_val:
                LOG.error(_LE("UpdateTenantFW disconnect FAILED"))
            tfw_sgif = re.compile("^DEV_.*_" + network_id + '_TYPE$')
            sgif_count = len([k for k in nwa_data if tfw_sgif.match(k)])
            if sgif_count:
                raise nwa_exc.AgentProxyException(value=nwa_data)
            nwa_data = ret_val
        elif count == 1:
            # raise AgentProxyException if fail
            nwa_data = self._delete_tenant_fw(
                context, nwa_data=nwa_data, **kwargs)
        else:
            LOG.error(_LE("count miss match"))
            raise nwa_exc.AgentProxyException(value=nwa_data)

        return self.proxy_l2._terminate_l2_network(context,
                                                   nwa_data, **kwargs)

    @helpers.log_method_call
    def setting_nat(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        fip_id = kwargs['floating']['id']

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id)

        try:
            ret_val = self._setting_nat(context, nwa_data=nwa_data, **kwargs)
        except nwa_exc.AgentProxyException:
            self.nwa_l3_rpc.update_floatingip_status(
                context, fip_id, constants.FLOATINGIP_STATUS_ERROR)
            return

        self.nwa_l3_rpc.update_floatingip_status(
            context, fip_id, constants.FLOATINGIP_STATUS_ACTIVE)
        return self.proxy_tenant.update_tenant_binding(
            context, tenant_id, nwa_tenant_id, ret_val)

    @helpers.log_method_call
    def _setting_nat(self, context, **kwargs):
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')
        floating = kwargs.get('floating')

        # new code.(neet ut)
        nat_key = 'NAT_' + floating['id']
        if nat_key in nwa_data:
            LOG.debug('already in use NAT key =%s', nat_key)
            raise nwa_exc.AgentProxyException(value=None)

        vlan_logical_name = data_utils.get_vlan_logical_name(
            nwa_data, floating['floating_network_id'])
        dev_name = data_utils.get_tfw_device_name(nwa_data,
                                                  floating['device_id'])

        # setting nat
        rcode, body = self.client.l3.setting_nat(
            nwa_tenant_id,
            vlan_logical_name, 'PublicVLAN',
            floating['fixed_ip_address'],
            floating['floating_ip_address'], dev_name, data=floating
        )

        if rcode != 200 or body['status'] != 'SUCCEED':
            LOG.debug("SettingNat Error: invalid responce."
                      " rcode=%d status=%s" % (rcode, body))
            raise nwa_exc.AgentProxyException(value=None)
        else:
            LOG.debug("SettingNat SUCCEED")
            data_utils.set_floatingip_data(nwa_data, floating)
            return nwa_data

    @helpers.log_method_call
    def delete_nat(self, context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        fip_id = kwargs['floating']['id']

        nwa_data = self.nwa_tenant_rpc.get_nwa_tenant_binding(
            context, tenant_id, nwa_tenant_id)

        try:
            ret_val = self._delete_nat(context, nwa_data=nwa_data, **kwargs)
        except nwa_exc.AgentProxyException:
            self.nwa_l3_rpc.update_floatingip_status(
                context, fip_id, constants.FLOATINGIP_STATUS_ERROR)
            return

        self.nwa_l3_rpc.update_floatingip_status(
            context, fip_id, constants.FLOATINGIP_STATUS_DOWN)
        return self.proxy_tenant.update_tenant_binding(
            context, tenant_id, nwa_tenant_id, ret_val)

    @helpers.log_method_call
    def _delete_nat(self, context, **kwargs):
        nwa_data = kwargs.get('nwa_data')
        floating = kwargs.get('floating')

        vlan_logical_name = data_utils.get_vlan_logical_name(
            nwa_data, floating['floating_network_id'])
        dev_name = data_utils.get_tfw_device_name(nwa_data,
                                                  floating['device_id'])

        # setting nat
        rcode, body = self.client.l3.delete_nat(
            kwargs.get('nwa_tenant_id'),
            vlan_logical_name, 'PublicVLAN',
            floating['fixed_ip_address'],
            floating['floating_ip_address'], dev_name, data=floating)

        if rcode != 200 or body['status'] != 'SUCCEED':
            LOG.debug("DeleteNat Error: invalid responce."
                      " rcode=%d status=%s" % (rcode, body))
            raise nwa_exc.AgentProxyException(value=None)
        else:
            LOG.debug("DeleteNat SUCCEED")
            data_utils.strip_floatingip_data(nwa_data, floating)
            return nwa_data
