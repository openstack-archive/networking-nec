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

from sqlalchemy.orm import exc as sa_exc

from neutron.api.rpc.handlers import dhcp_rpc
from neutron.api.rpc.handlers import metadata_rpc
from neutron.api.rpc.handlers import securitygroups_rpc
from neutron.common import constants as q_const
from neutron.common import rpc as n_rpc
from neutron.common import topics
from neutron.db import agents_db
from neutron.db import api as db_api
from neutron.db import models_v2
from neutron.extensions import l3
from neutron.extensions import multiprovidernet as mpnet
from neutron.extensions import portbindings
from neutron.extensions import portsecurity as psec
from neutron.extensions import providernet as provider
from neutron import manager
from neutron.plugins.common import constants as plugin_constants
from neutron.plugins.ml2 import db as db_ml2
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2 import models as models_ml2
from neutron.plugins.ml2 import plugin as ml2_plugin
from neutron.plugins.ml2 import rpc
from oslo_log import log as logging
import oslo_messaging
from oslo_serialization import jsonutils

from networking_nec._i18n import _LE, _LI, _LW
from networking_nec.plugins.necnwa.agent import necnwa_agent_rpc
from networking_nec.plugins.necnwa.db import api as necnwa_api

LOG = logging.getLogger(__name__)


class NECNWATenantBindingServerRpcApi(object):
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

    def get_nwa_tenant_binding(self, context, tenant_id, nwa_tenant_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'get_nwa_tenant_binding',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id
        )

    def add_nwa_tenant_binding(self, context, tenant_id,
                               nwa_tenant_id, nwa_data):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'add_nwa_tenant_binding',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data
        )

    def set_nwa_tenant_binding(self, context, tenant_id,
                               nwa_tenant_id, nwa_data):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'set_nwa_tenant_binding',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id,
            nwa_data=nwa_data
        )

    def delete_nwa_tenant_binding(self, context, tenant_id,
                                  nwa_tenant_id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'delete_nwa_tenant_binding',
            tenant_id=tenant_id,
            nwa_tenant_id=nwa_tenant_id
        )

    def update_tenant_rpc_servers(self, context, rpc_servers):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'update_tenant_rpc_servers',
            servers=rpc_servers
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

    def update_floatingip_status(self, context, floatingip_id, status):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'update_floatingip_status',
            floatingip_id=floatingip_id,
            status=status
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

    def create_fwaas_ids(self, context, tfw):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'create_fwaas_ids',
            tfw=tfw,
        )

    def delete_fwaas_ids(self, context, tfw):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'delete_fwaas_ids',
            tfw=tfw,
        )

    def get_fwaas_id(self, context, tfw, type):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'get_fwaas_id',
            tfw=tfw,
            type=type
        )

    def clear_fwaas_id(self, context, tfw, type, id):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'clear_fwaas_id',
            tfw=tfw,
            type=type,
            id=id
        )

    def blk_clear_fwaas_ids(self, context, tfw, ids):
        cctxt = self.client.prepare()
        return cctxt.call(
            context,
            'blk_clear_fwaas_ids',
            tfw=tfw,
            ids=ids
        )


class NECNWAServerRpcCallbacks(rpc.RpcCallbacks):

    RPC_VERSION = '1.0'

    @property
    def l3plugin(self):
        if not hasattr(self, '_l3plugin'):
            self._l3plugin = manager.NeutronManager.get_service_plugins()[
                plugin_constants.L3_ROUTER_NAT]
        return self._l3plugin

    def get_device_details(self, rpc_context, **kwargs):
        """Agent requests device details."""
        agent_id = kwargs.get('agent_id')
        device = kwargs.get('device')
        host = kwargs.get('host')
        # cached networks used for reducing number of network db calls
        # for server internal usage only
        cached_networks = kwargs.get('cached_networks')
        LOG.debug("Device %(device)s details requested by agent "
                  "%(agent_id)s with host %(host)s",
                  {'device': device, 'agent_id': agent_id, 'host': host})

        plugin = manager.NeutronManager.get_plugin()
        port_id = plugin._device_to_port_id(device)
        port_context = plugin.get_bound_port_context(rpc_context,
                                                     port_id,
                                                     host,
                                                     cached_networks)
        if not port_context:
            LOG.warning(_LW("Device %(device)s requested by agent "
                            "%(agent_id)s not found in database"),
                        {'device': device, 'agent_id': agent_id})
            return {'device': device}

        segment = port_context.bottom_bound_segment

        port = port_context.current
        # caching information about networks for future use
        if cached_networks is not None:
            if port['network_id'] not in cached_networks:
                cached_networks[port['network_id']] = (
                    port_context.network.current)
        if not segment:
            LOG.warning(_LW("Device %(device)s requested by agent "
                            "%(agent_id)s on network %(network_id)s not "
                            "bound, vif_type: %(vif_type)s"),
                        {'device': device,
                         'agent_id': agent_id,
                         'network_id': port['network_id'],
                         'vif_type': port[portbindings.VIF_TYPE]})
            return {'device': device}

        elif segment['segmentation_id'] == 0:
            LOG.warning(_LW("Device %(device)s requested by agent "
                            "%(agent_id)s, segment %(segment_id)s has "
                            "network %(network_id)s not no segment from NWA"),
                        {'device': device, 'agent_id': agent_id,
                         'segment_id': segment['id'],
                         'network_id': port['network_id']})
            return {'device': device}

        if (not host or host == port_context.host):
            new_status = (q_const.PORT_STATUS_BUILD if port['admin_state_up']
                          else q_const.PORT_STATUS_DOWN)
            if (
                    port['status'] != new_status and
                    port['status'] != q_const.PORT_STATUS_ACTIVE
            ):
                plugin.update_port_status(rpc_context,
                                          port_id,
                                          new_status,
                                          host)

        entry = {'device': device,
                 'network_id': port['network_id'],
                 'port_id': port_id,
                 'mac_address': port['mac_address'],
                 'admin_state_up': port['admin_state_up'],
                 'network_type': segment[api.NETWORK_TYPE],
                 'segmentation_id': segment[api.SEGMENTATION_ID],
                 'physical_network': segment[api.PHYSICAL_NETWORK],
                 'fixed_ips': port['fixed_ips'],
                 'device_owner': port['device_owner'],
                 'allowed_address_pairs': port['allowed_address_pairs'],
                 'port_security_enabled': port.get(psec.PORTSECURITY, True),
                 'profile': port[portbindings.PROFILE]}
        LOG.debug("Returning: %s", entry)
        return entry

    def _get_device_details(self, rpc_context, **kwargs):
        """Agent requests device details."""
        agent_id = kwargs.get('agent_id')
        device = kwargs.get('device')
        host = kwargs.get('host')
        LOG.debug("Device %(device)s details requested by agent "
                  "%(agent_id)s with host %(host)s",
                  {'device': device, 'agent_id': agent_id, 'host': host})

        plugin = manager.NeutronManager.get_plugin()
        port_id = plugin._device_to_port_id(device)
        port_context = plugin.get_bound_port_context(rpc_context,
                                                     port_id,
                                                     host)
        if not port_context:
            LOG.warning(_LW("Device %(device)s requested by agent "
                            "%(agent_id)s not found in database"),
                        {'device': device, 'agent_id': agent_id})
            return {'device': device}

        port = port_context.current

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            segments = db_ml2.get_network_segments(session, port['network_id'],
                                                   filter_dynamic=True)
            if not segments:
                LOG.warning(_LW("Device %(device)s requested by agent "
                                "%(agent_id)s has network %(network_id)s not "
                                "no segment"),
                            {'device': device, 'agent_id': agent_id,
                             'network_id': port['network_id']})
                return {'device': device}
            elif len(segments) != 1:
                LOG.warning(_LW("Device %(device)s requested by agent "
                                "%(agent_id)s has network %(network_id)s not "
                                "no segment size miss mach"),
                            {'device': device, 'agent_id': agent_id,
                             'network_id': port['network_id']})
                return {'device': device}
            elif segments[0]['segmentation_id'] == 0:
                LOG.warning(_LW("Device %(device)s requested by agent "
                                "%(agent_id)s, segment %(segment_id)s has "
                                "network %(network_id)s not "
                                "no segment from NWA"),
                            {'device': device, 'agent_id': agent_id,
                             'segment_id': segments[0]['id'],
                             'network_id': port['network_id']})
                return {'device': device}

            binding = necnwa_api.ensure_port_binding(session, port_id)

            if not binding.segment_id:
                LOG.warning(_LW("Device %(device)s requested by agent "
                                "%(agent_id)s on network %(network_id)s not "
                                "bound, vif_type: %(vif_type)s"),
                            {'device': device,
                             'agent_id': agent_id,
                             'network_id': port['network_id'],
                             'vif_type': binding.vif_type})
                return {'device': device}

        port = port_context.current

        new_status = (q_const.PORT_STATUS_BUILD if port['admin_state_up']
                      else q_const.PORT_STATUS_DOWN)

        if (
                port['status'] != new_status and
                port['status'] != q_const.PORT_STATUS_ACTIVE
        ):
            plugin.update_port_status(rpc_context,
                                      port_id,
                                      new_status,
                                      host)

        entry = {'device': device,
                 'network_id': port['network_id'],
                 'port_id': port_id,
                 'mac_address': port['mac_address'],
                 'admin_state_up': port['admin_state_up'],
                 'network_type': segments[0]['network_type'],
                 'segmentation_id': segments[0]['segmentation_id'],
                 'physical_network': segments[0]['physical_network'],
                 'fixed_ips': port['fixed_ips'],
                 'device_owner': port['device_owner'],
                 'profile': port[portbindings.PROFILE]}
        LOG.debug("Returning: %s", entry)
        return entry

    def update_device_up(self, rpc_context, **kwargs):
        """Device is up on agent."""

        agent_id = kwargs.get('agent_id')  # noqa
        # device = kwargs.get('device')

        # plugin = manager.NeutronManager.get_plugin()
        # port_id = plugin._device_to_port_id(device)

        return

    def get_nwa_network_by_port_id(self, rpc_context, **kwargs):
        plugin = manager.NeutronManager.get_plugin()
        port_id = kwargs.get('port_id')
        port = plugin.get_port(rpc_context, port_id)

        network = plugin.get_network(rpc_context, port['network_id'])

        return network

    def get_nwa_network_by_subnet_id(self, rpc_context, **kwargs):
        plugin = manager.NeutronManager.get_plugin()
        subnet_id = kwargs.get('subnet_id')
        subnet = plugin.get_subnet(rpc_context, subnet_id)

        network = plugin.get_network(rpc_context, subnet['network_id'])

        return network

    def get_nwa_network(self, rpc_context, **kwargs):
        plugin = manager.NeutronManager.get_plugin()
        net_id = kwargs.get('network_id')
        network = plugin.get_network(rpc_context, net_id)

        return network

    def get_nwa_networks(self, rpc_context, **kwargs):
        plugin = manager.NeutronManager.get_plugin()
        networks = plugin.get_networks(rpc_context)

        return networks

    def get_nwa_tenant_binding(self, rpc_context, **kwargs):
        """get nwa_tenant_binding from neutorn db.

        @param rpc_context: rpc context.
        @param kwargs: tenant_id, nwa_tenant_id
        @return: success = dict of nwa_tenant_binding, error = dict of empty.
        """
        LOG.debug("context=%s, kwargs=%s" % (rpc_context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        LOG.debug("tenant_id=%s, nwa_tenant_id=%s" %
                  (tenant_id, nwa_tenant_id))
        session = db_api.get_session()
        with session.begin(subtransactions=True):
            recode = necnwa_api.get_nwa_tenant_binding(
                session, tenant_id, nwa_tenant_id
            )
            if recode is not None:
                LOG.debug(
                    "nwa_data=%s", jsonutils.dumps(
                        recode.value_json, indent=4, sort_keys=True)
                )
                return recode.value_json

        return dict()

    def add_nwa_tenant_binding(self, rpc_context, **kwargs):
        """get nwa_tenant_binding from neutorn db.

        @param rpc_context: rpc context.
        @param kwargs: tenant_id, nwa_tenant_id
        @return: dict of status
        """

        LOG.debug("context=%s, kwargs=%s" % (rpc_context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            if necnwa_api.add_nwa_tenant_binding(
                    session,
                    tenant_id,
                    nwa_tenant_id,
                    nwa_data
            ):
                return {'status': 'SUCCESS'}

        return {'status': 'FAILED'}

    def set_nwa_tenant_binding(self, rpc_context, **kwargs):
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')
        nwa_data = kwargs.get('nwa_data')
        LOG.debug("tenant_id=%s, nwa_tenant_id=%s" %
                  (tenant_id, nwa_tenant_id))
        LOG.debug(
            "nwa_data=%s", jsonutils.dumps(nwa_data, indent=4, sort_keys=True)
        )

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            if necnwa_api.set_nwa_tenant_binding(
                    session,
                    tenant_id,
                    nwa_tenant_id,
                    nwa_data
            ):
                return {'status': 'SUCCESS'}

        return {'status': 'FAILED'}

    def delete_nwa_tenant_binding(self, rpc_context, **kwargs):
        LOG.debug("context=%s, kwargs=%s" % (rpc_context, kwargs))
        tenant_id = kwargs.get('tenant_id')
        nwa_tenant_id = kwargs.get('nwa_tenant_id')

        session = db_api.get_session()
        with session.begin(subtransactions=True):
            if necnwa_api.del_nwa_tenant_binding(
                    session,
                    tenant_id,
                    nwa_tenant_id
            ):
                return {'status': 'SUCCESS'}

        return {'status': 'FAILED'}

    def update_tenant_rpc_servers(self, rpc_context, **kwargs):
        ret = {'servers': []}

        servers = kwargs.get('servers')
        plugin = manager.NeutronManager.get_plugin()
        session = db_api.get_session()

        with session.begin(subtransactions=True):
            queues = necnwa_api.get_nwa_tenant_queues(session)
            for queue in queues:
                tenant_ids = [server['tenant_id'] for server in servers]
                if queue.tenant_id in tenant_ids:
                    LOG.info(_LI("RPC Server active(tid=%s)") %
                             queue.tenant_id)
                    continue
                else:
                    # create rpc server for tenant
                    LOG.debug("create_server: tid=%s", queue.tenant_id)
                    plugin.nwa_rpc.create_server(
                        rpc_context, queue.tenant_id
                    )
                    ret['servers'].append({'tenant_id': queue.tenant_id})

        return ret

    def release_dynamic_segment_from_agent(self, context, **kwargs):
        network_id = kwargs.get('network_id')
        physical_network = kwargs.get('physical_network')

        session = db_api.get_session()
        del_segment = db_ml2.get_dynamic_segment(
            session, network_id, physical_network=physical_network,
        )
        if del_segment:
            LOG.debug("release_dynamic_segment segment_id=%s" %
                      del_segment['id'])
            db_ml2.delete_network_segment(session, del_segment['id'])

    def update_port_state_with_notifier(self, rpc_context, **kwargs):
        device = kwargs.get('device')
        agent_id = kwargs.get('agent_id')
        port_id = kwargs.get('port_id')
        network_id = kwargs.get('network_id')
        network_type = kwargs.get('network_type')
        segmentation_id = kwargs.get('segmentation_id')
        physical_network = kwargs.get('physical_network')

        LOG.debug("device %(device)s "
                  "agent_id %(agent_id)s "
                  "port_id %(port_id)s "
                  "segmentation_id %(segmentation_id)d "
                  "physical_network %(physical_network)s ",
                  {'device': device, 'agent_id': agent_id,
                   'port_id': port_id,
                   'segmentation_id': segmentation_id,
                   'physical_network': physical_network})

        # 1 update segment
        session = db_api.get_session()
        with session.begin(subtransactions=True):
            try:
                query = (session.query(models_ml2.NetworkSegment).
                         filter_by(network_id=network_id))
                query = query.filter_by(physical_network=physical_network)
                query = query.filter_by(is_dynamic=True)
                record = query.one()
                record.segmentation_id = segmentation_id
            except sa_exc.NoResultFound:
                pass

        # 2 change port state
        plugin = manager.NeutronManager.get_plugin()
        plugin.update_port_status(
            rpc_context,
            port_id,
            q_const.PORT_STATUS_ACTIVE
        )

        # 3 serch db from port_id
        session = db_api.get_session()
        port = None
        with session.begin(subtransactions=True):
            try:
                port_db = (session.query(models_v2.Port).
                           enable_eagerloads(False).
                           filter(models_v2.Port.id.startswith(port_id)).
                           one())
                port = plugin._make_port_dict(port_db)
            except sa_exc.NoResultFound:
                LOG.error(_LE("Can't find port with port_id %s"),
                          port_id)
            except sa_exc.MultipleResultsFound:
                LOG.error(_LE("Multiple ports have port_id starting with %s"),
                          port_id)
        # 4 send notifier
        if port is not None:
            LOG.debug("notifier port_update %s, %s, %s" %
                      (network_type, segmentation_id, physical_network))
            plugin.notifier.port_update(
                rpc_context, port,
                network_type,
                segmentation_id,
                physical_network
            )

        return {}

    def create_fwaas_ids(self, context, tfw):
        session = db_api.get_session()
        result = necnwa_api.create_fwaas_ids(
            session, tfw
        )
        return {'result': result}

    def delete_fwaas_ids(self, context, tfw):
        session = db_api.get_session()
        result = necnwa_api.delete_fwaas_ids(
            session, tfw
        )
        return {'result': result}

    def get_fwaas_id(self, context, tfw, type):
        session = db_api.get_session()
        id = necnwa_api.get_fwaas_id(
            session, tfw, type
        )
        LOG.debug("tfw=%s, type=%s id=%d" % (tfw, type, id))
        return {
            'id': id,
            'result': False if id == 0 else True,
        }

    def clear_fwaas_id(self, context, tfw, type, id):
        session = db_api.get_session()
        ret = necnwa_api.clear_fwaas_ids(
            session, tfw, type
        )
        return {
            'id': id,
            'result': ret,
        }

    def blk_clear_fwaas_ids(self, context, tfw, ids):
        session = db_api.get_session()
        ret = necnwa_api.blk_clear_fwaas_ids(
            session, tfw, ids
        )
        return {
            'result': ret,
        }

    def update_floatingip_status(self, context, floatingip_id, status):
        '''Update operational status for a floating IP.'''
        with context.session.begin(subtransactions=True):
            LOG.debug('New status for floating IP {}: {}'.format(
                floatingip_id, status))
            try:
                self.l3plugin.update_floatingip_status(context,
                                                       floatingip_id,
                                                       status)
            except l3.FloatingIPNotFound:
                LOG.debug("Floating IP: %s no longer present.",
                          floatingip_id)


class NECNWACorePlugin(ml2_plugin.Ml2Plugin):

    def __init__(self):
        super(NECNWACorePlugin, self).__init__()
        self._nwa_agent_rpc_setup()

    def _nwa_agent_rpc_setup(self):
        self.nwa_rpc = necnwa_agent_rpc.NECNWAAgentApi(
            necnwa_agent_rpc.NWA_AGENT_TOPIC
        )
        self.nwa_proxies = dict()

    def start_rpc_listeners(self):
        self.endpoints = [NECNWAServerRpcCallbacks(self.notifier,
                                                   self.type_manager),
                          securitygroups_rpc.SecurityGroupServerRpcCallback(),
                          dhcp_rpc.DhcpRpcCallback(),
                          agents_db.AgentExtRpcCallback(),
                          metadata_rpc.MetadataRpcCallback()]

        self.topic = topics.PLUGIN
        self.conn = n_rpc.create_connection(new=True)
        self.conn.create_consumer(self.topic, self.endpoints,
                                  fanout=False)
        return self.conn.consume_in_threads()

    def _extend_network_dict_provider(self, context, network):
        if 'id' not in network:
            LOG.debug("Network has no id")
            network[provider.NETWORK_TYPE] = None
            network[provider.PHYSICAL_NETWORK] = None
            network[provider.SEGMENTATION_ID] = None
            return

        id = network['id']
        segments = db_ml2.get_network_segments(
            context.session, id, filter_dynamic=True)

        if not segments:
            LOG.debug("Network %s has no segments", id)
            network[provider.NETWORK_TYPE] = None
            network[provider.PHYSICAL_NETWORK] = None
            network[provider.SEGMENTATION_ID] = None
        elif len(segments) > 1:
            network[mpnet.SEGMENTS] = [
                {provider.NETWORK_TYPE: segment[api.NETWORK_TYPE],
                 provider.PHYSICAL_NETWORK: segment[api.PHYSICAL_NETWORK],
                 provider.SEGMENTATION_ID: segment[api.SEGMENTATION_ID]}
                for segment in segments]
        else:
            segment = segments[0]
            network[provider.NETWORK_TYPE] = segment[api.NETWORK_TYPE]
            network[provider.PHYSICAL_NETWORK] = segment[api.PHYSICAL_NETWORK]
            network[provider.SEGMENTATION_ID] = segment[api.SEGMENTATION_ID]

    def get_network(self, context, id, fields=None):
        session = context.session

        with session.begin(subtransactions=True):
            network = self._get_network(context, id)
            result = self._make_network_dict(network, fields)
            self._extend_network_dict_provider(context, result)

        return self._fields(result, fields)

    def get_networks(self, context, filters=None, fields=None,
                     sorts=None, limit=None, marker=None, page_reverse=False):
        return super(
            NECNWACorePlugin,
            self
        ).get_networks(context, filters, None, sorts,
                       limit, marker, page_reverse)

    def _create_nwa_agent_tenant_queue(self, context, tenant_id):
        if (
                self._is_alive_nwa_agent(context) and
                necnwa_api.get_nwa_tenant_queue(
                    context.session,
                    tenant_id
                ) is None
        ):
            self.nwa_rpc.create_server(context, tenant_id)
            necnwa_api.add_nwa_tenant_queue(context.session, tenant_id)
        else:
            LOG.warning(_LW('%s is not alive.') %
                        necnwa_agent_rpc.NWA_AGENT_TYPE)

    def create_network(self, context, network):
        result = super(NECNWACorePlugin,
                       self).create_network(context, network)
        self._create_nwa_agent_tenant_queue(context, context.tenant_id)
        return result

    def delete_network(self, context, id):
        result = super(NECNWACorePlugin,
                       self).delete_network(context, id)
        return result

    def create_port(self, context, port):
        result = super(NECNWACorePlugin,
                       self).create_port(context, port)

        return result

    def get_nwa_topics(self, context, tid):
        topics = []
        rss = self.nwa_rpc.get_nwa_rpc_servers(context)
        if isinstance(rss, dict) and rss.get('nwa_rpc_servers'):
            topics = [t.get('topic') for t in rss['nwa_rpc_servers']
                      if t.get('tenant_id') == tid]
        return topics

    def get_nwa_proxy(self, tid, context=None):
        if tid not in self.nwa_proxies.keys():
            self.nwa_proxies[tid] = necnwa_agent_rpc.NECNWAProxyApi(
                necnwa_agent_rpc.NWA_AGENT_TOPIC, tid
            )
            if context:
                self._create_nwa_agent_tenant_queue(context, tid)
                topics = self.get_nwa_topics(context, tid)
                if len(topics) == 1:
                    LOG.info(_LI('NWA tenant queue: new topic is %s'),
                             str(topics[0]))
                else:
                    LOG.warning(_LW('NWA tenant queue is not created. tid=%s'),
                                tid)
        LOG.debug('proxy tid=%s', tid)
        return self.nwa_proxies[tid]

    def _is_alive_nwa_agent(self, context):
        agents = self.get_agents(
            context,
            filters={'agent_type': [necnwa_agent_rpc.NWA_AGENT_TYPE]}
        )
        return any(agent['alive'] for agent in agents)
