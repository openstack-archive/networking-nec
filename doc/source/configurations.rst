=============
Configuration
=============

This section describes the configurations of the releases maintained by OpenStack community (i.e., Juno, Kilo).

neutron.conf
============

* **core_plugin**:  Needs to be configured to ``neutron.plugins.nec.nec_plugin.NECPluginV2`` to use NEC OpenFlow plugin as core plugin.::

    core_plugin = neutron.plugins.nec.nec_plugin.NECPluginV2

* **service_plugins**: NEC OpenFlow plugin provides L3 router feature as part of the core plugin.
  Thus L3 router service plugin should **NOT** be contained in **service_plugin**.
  Other service plugins (LBaaS, FWaaS, VPNaaS, metering) are verified to work with NEC OpenFlow plugin.

plugin specific configuration
=============================

It is usually placed at ``/etc/neutron/plugins/nec/nec.ini``.

Section ``[OFC]`` is configurations specific to NEC OpenFlow plugin.
We describe ``[OFC]`` section first and then describe other sections.

[OFC] section
-------------

Features of North-bound REST API of OpenFlow controller

* **driver**: Shortcut name or full class path of OpenFlow controller driver.
  The appropriate driver needs to be specified depending on your back-end OpenFlow controller.
  The following drivers are available. The default value is ``trema``.

  * NEC ProgrammableFlow OpenFlow controller

    * **pfc** : Alias for the latest ProgrammableFlow release. **pfc_v51** since Icehouse, **pfc_v5** since Havana.
    * **pfc_v51** : ProgrammableFlow Controller V5.1. Supported since Icehouse
    * **pfc_v5** : ProgrammableFlow Controller V5.0. Supported since Havana.
    * **pfc_v4** : ProgrammableFlow Controller V4.0.
    * **pfc_v3** : ProgrammableFlow Controller V3.0.

  * Trema Sliceable Switch

    * **trema**: Trema Slieable Switch. Alias for **trema_port**.
    * **trema_port** : Virtual networks are identified based on OpenFlow port. Each port of virtual network is identified by datapath_id, port_no and (optional) vlan_id.
    * **trema_portmac** : Similar to **trema_port**. In addition MAC address is also considered when identify a port of virtual network.
    * **trema_mac** : Virtual networks are identified based on received MAC address.

* **enable_packet_filter**: Specified whether NEC plugin specific PacketFilter extension is enabled. This features is supported in all OpenStack releases for Trema Sliceable Switch and since Icehouse for ProgrammableFlow Controller. The default value is ``true``.
* **support_packet_filter_on_ofc_router**: Support packet filter features on OFC router interface. ProgrammableFlow Controller v5 does not support the packet filter on OFC router interface, so this parameter should be set to ``false``. Otherwise it is recommended to set this to ``true``. The default value is ``true``. (Since Juno)

REST API endpoint of OpenFlow controller

* **host**: Host IP address of OpenFlow Controller where its north-bound REST API is listening to. Example: `` 127.0.0.1``
* **port**: Port number of OpenFlow Controller where its north0bound REST API is listening to. Example: ``8888``
* **api_max_attempts** (default: 3): Maximum attempts per OFC API request. NEC plugin retries API request to OFC when OFC returns ServiceUnavailable (503). **The value must be greater than 0.** (Since Icehouse)
* **path_prefix** (default: empty string): Base URL of OpenFlow Controller REST API. It is prepended to a path of each API request. (Since Icehouse)

SSL configuration for OpenFlow controller north bound API. It is only available for ProgrammableFlow Controller.

* **use_ssl** (default: ``false``): Specify whether SSL is used to connection a back-end OpenFlow controller or not.
* **key_file**: Key file
* **cert_file**: Certificate file
* **insecure_ssl** (default: ``false``): Disable SSL certificate verification. (Since Icehouse)

[ovs] section
-------------

* **integration_bridge** (default: ``br-int``) : This is the name of the OVS integration bridge. There is one per hypervisor. The integration bridge acts as a virtual "patch port". All VM VIFs are attached to this bridge and then "patched" according to their network connectivity. Recommend not to change this parameter unless you have a good reason to.

[agent] section
---------------

* **root_helper**: Recommended to be configured to ``sudo /usr/local/bin/neutron-rootwrap /etc/neutron/rootwrap.conf``. In Kilo, this parameter no longer has the meaning.
* **polling_interval** (default: 2): Agent's polling interval in seconds

[securitygroup] section
-----------------------

* **firewall_driver**: Firewall driver for realizing neutron security group function. Needs to configured to ``neutron.agent.linux.iptables_firewall.OVSHybridIptablesFirewallDriver``
* **enable_security_group** (default: true): Controls if neutron security group is enabled or not. It should be false when you use nova security group.

[provider] section
------------------

NEC OpenFlow plugin supported multiple back-end for router implementation.

* **default_router_provider** (default: ``l3-agent``): Default router provider to use. ``l3-agent`` or ``openflow`` can be specified.
* **router_providers** (default: ``l3-agent,openflow``): List of enabled router providers. If a configured OpenFlow backed does not support router implementation, ``openflow`` provider will be disabled automatically and all routers will be created using l3-agent.

Neutron service agent
=====================

Various neutron agents which plug interfaces to an integration bridge have a configuration parameter **interface_driver**.
**interface_driver** and **ovs_use_veth** need to be configured to ``OVSInterfaceDriver`` to make NEC OpenFlow plugin work.

::

    interface_driver = quantum.agent.linux.interface.OVSInterfaceDriver
    ovs_use_veth = True

Such agents are:

* DHCP agent (/etc/neutron/dhcp_agent.ini)
* L3 agent (/etc/neutron/l3_agent.ini)
* LBaaS HAProxy agent (/etc/neutron/services/loadbalancer/haproxy/lbaas_agent.ini)
* Neutron Debug command **neutron-debug** (/etc/neutron/debug.ini)

Nova configuration
==================

No configuration specific to this plugin.

