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

from neutron.common import rpc as n_rpc
from neutron.plugins.ml2 import driver_api as api
import oslo_messaging


class NwaL2ServerRpcApi(object):

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self, topic):
        target = oslo_messaging.Target(topic=topic,
                                       version=self.BASE_RPC_API_VERSION)
        self.client = n_rpc.get_client(target)

    def get_nwa_network_by_port_id(self, context, port_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'get_nwa_network_by_port_id',
            port_id=port_id
        )

    def get_nwa_network_by_subnet_id(self, context, subnet_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'get_nwa_network_by_subnet_id',
            subnet_id=subnet_id
        )

    def get_nwa_network(self, context, network_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'get_nwa_network',
            network_id=network_id
        )

    def get_nwa_networks(self, context, tenant_id, nwa_tenant_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'get_nwa_networks',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id
        )

    def update_port_state_with_notifier(self, context, device, agent_id,
                                        port_id, segment, network_id):
        physical_network = segment[api.PHYSICAL_NETWORK]
        network_type = segment[api.NETWORK_TYPE]
        segmentation_id = segment[api.SEGMENTATION_ID]

        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'update_port_state_with_notifier',
            device=device,
            agent_id=agent_id,
            port_id=port_id,
            network_id=network_id,
            network_type=network_type,
            segmentation_id=segmentation_id,
            physical_network=physical_network
        )

    def release_dynamic_segment_from_agent(self, context, physical_network,
                                           network_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'release_dynamic_segment_from_agent',
            network_id=network_id,
            physical_network=physical_network
        )
