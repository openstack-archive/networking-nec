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

from neutron.agent.common import config
from oslo_config import cfg

from networking_nec._i18n import _

agent_opts = [
    cfg.IntOpt('polling_interval', default=2,
               help=_("The number of seconds the agent will wait between "
                      "polling for local device changes.")),
]

cfg.CONF.register_opts(agent_opts, "AGENT")
config.register_agent_state_opts_helper(cfg.CONF)

# shortcuts
CONF = cfg.CONF
AGENT = cfg.CONF.AGENT

# nwa.ini
NWA_opts = [
    cfg.StrOpt('server_url',
               help=_("URL for NWA REST API.")),
    cfg.StrOpt('access_key_id',
               help=_("Access ID for NWA REST API.")),
    cfg.StrOpt('secret_access_key',
               help=_("Secret key for NWA REST API.")),
    cfg.StrOpt('resource_group_name',
               help=_(
                   "Resouce Group Name specified at creating tenant NW.")),
    cfg.StrOpt('region_name',
               help=_("RegionName for DC."),
               default='RegionOne'),
    cfg.IntOpt('scenario_polling_first_timer', default=2,
               help=_("Timer value for the first scenario status polling.")),
    cfg.IntOpt('scenario_polling_timer', default=10,
               help=_("Timer value for polling scenario status.")),
    cfg.IntOpt('scenario_polling_count', default=6,
               help=_("Count value for polling scenario status.")),
    cfg.StrOpt('ironic_az_prefix',
               help=_("The prefix name of device_owner used in ironic"),
               default='BM_'),
    cfg.BoolOpt('use_setting_fw_policy',
                default=False,
                help=_('Using setting_fw_policy as default')),
    cfg.StrOpt('resource_group_file',
               help=_("JSON file which defines relations between "
                      "physical network of OpenStack and NWA.")),
    cfg.StrOpt('port_map_file',
               help=_("JSON file which defines relations between "
                      "each NIC of baremetal server and PFS port.")),
    cfg.StrOpt('resource_group',
               deprecated_for_removal=True,
               deprecated_reason='In favor of resource_group_file option.',
               help=_("""
        Relations between physical network of OpenStack and NWA.
        ex)
        [
           {
               "physical_network": "physnet1",
               "ResourceGroupName":"Core/Hypervisor/HV-RG01"
           },
           { ... },
        ]""")),
    cfg.StrOpt('port_map',
               deprecated_for_removal=True,
               deprecated_reason='In favor of port_map_file option.',
               help=_("""Relations between each NIC of BM server and PFS port.
        ex)
        [
            {
               "controller_id": "PFC_POD02",
               "logical_port_id": "SD-POD02_01",
               "mac_address":"94:DE:80:12:9C:D4",
               "pfs_port":"PP-cccc-0000-0000-2222-GBE0/1"
            }, { ... },
        ]""")),
    cfg.StrOpt('lbaas_driver',
               help=_("LBaaS Driver Name")),
    cfg.StrOpt('fwaas_driver',
               help=_("Firewall Driver Name")),
]

Scenario_opts = [
    cfg.StrOpt('CreateTenantFW',
               help=_("Scenario ID for the scenario CreateTenantFW.")),
    cfg.StrOpt('CreateTenantNW',
               help=_("Scenario ID for the scenario CreateTenantNW.")),
    cfg.StrOpt('CreateVLAN',
               help=_("Scenario ID for the scenario CreateVLAN.")),
    cfg.StrOpt('CreateGeneralDev',
               help=_(
                   "Scenario ID for the scenario CreateGeneralDev.")),
    cfg.StrOpt('UpdateTenantFW',
               help=_("Scenario ID for the scenario UpdateTenantFW.")),
    cfg.StrOpt('SettingNAT',
               help=_("Scenario ID for the scenario SettingNAT.")),
]

CONF.register_opts(NWA_opts, "NWA")
CONF.register_opts(Scenario_opts, "Scenario")
