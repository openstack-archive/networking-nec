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

from oslo_config import cfg

from neutron.agent.common import config

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
OpenStack_opts = [
    cfg.StrOpt('NeutronDBid',
               help=_("ID to access to Neutron DB.")),
    cfg.StrOpt('NeutronDBpw',
               help=_("Password to access to Neutron DB.")),
]

NWA_opts = [
    cfg.StrOpt('ServerURL',
               help=_("URL for NWA REST API.")),
    cfg.StrOpt('AccessKeyId',
               help=_("Access ID for NWA REST API.")),
    cfg.StrOpt('SecretAccessKey',
               help=_("Secret key for NWA REST API.")),
    cfg.StrOpt('ResourceGroupName',
               help=_(
                   "Resouce Group Name specified at creating tenant NW.")),
    cfg.StrOpt('RegionName',
               help=_("RegionName for DC."),
               default='RegionOne'),
    cfg.IntOpt('ScenarioPollingTimer', default=10,
               help=_("Timer value for polling scenario status.")),
    cfg.IntOpt('ScenarioPollingCount', default=6,
               help=_("Count value for polling scenario status.")),
    cfg.StrOpt('IronicAZPrefix',
               help=_("device_owner's prefix for ironic"),
               default='BM_'),
    cfg.StrOpt('NwaDir',
               help=_("Directory for NWA data files.(deprecated.)")),
    cfg.BoolOpt('PolicyFWDefault',
                default=False,
                help=_('Enable PolicyFWDefault')),
    cfg.StrOpt('ResourceGroup',
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
    cfg.StrOpt('PortMap',
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

UNC_opts = [
    cfg.StrOpt('WebAapiURL',
               help=_("URL for UNC Web API.")),
    cfg.StrOpt('AccessId',
               help=_("Access ID for UNC Web API.")),
    cfg.StrOpt('AccessPw',
               help=_("Access password for UNC Web API.")),
    cfg.IntOpt('ScenarioPollingTimer', default=10,
               help=_("Timer value for polling scenario status.")),
    cfg.IntOpt('ScenarioPollingCount', default=6,
               help=_("Count value for polling scenario status.")),
]

CONF.register_opts(OpenStack_opts, "OpenStack")
CONF.register_opts(NWA_opts, "NWA")
CONF.register_opts(Scenario_opts, "Scenario")
CONF.register_opts(UNC_opts, "UNC")
