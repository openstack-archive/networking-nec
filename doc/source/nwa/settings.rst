===============================
Setting of NEC NWA plugin
===============================

This section describes the configurations of the releases of NEC NWA plugin.

neutron.conf
============

* **core_plugin**:  Needs to be configured to ``necnwa`` to use NEC NWA
  plugin as core plugin. ::

    core_plugin = necnwa

* **service_plugin**:  Needs to be configured to ``necnwa_router`` to use
  NEC NWA plugin as service plugin. ::

    service_plugin = necnwa_router

plugin specific configuration
=============================

It is usually placed at ``/etc/neutron/plugins/nec/necnwa.ini``.

[ml2] section
-------------

* **type_drivers**: Needs to be configured to ``vlan`` to use NEC NWA
  plugin as type_drivers. ::

    type_drivers = vlan

* **tenant_network_types**: Needs to be configured to ``vlan`` to use
  NEC NWA plugin as tenant_network_types. ::

    tenant_network_types = vlan

* **mechanism_drivers**: Needs to be configured to ``necnwa`` and
  ``openvswitch`` to use NEC NWA plugin as mechanism_drivers. ::

    mechanism_drivers = necnwa,openvswitch

[ml2_type_vlan] section
-----------------------

* **network_vlan_ranges**: Specify the name of an available physical
  network and a range of VIDs on that network available for allocation
  to tenant networks. The physical network should be the same name of
  NWA resource group name. ::

    network_vlan_ranges = OpenStack/DC/APP:1000:2999,OpenStack/DC/HA1:10:2999,OpenStack/DC/HA2:10:2999

[ovs] section
-------------

* **bridge_mappings**: Specify list of <physical_network>:<bridge>
  tuples, each specifying an OVS bridge used by the agent for a
  physical network to which it is connected.  ::

    bridge_mappings = OpenStack/DC/HA1:br-eth1,OpenStack/DC/HA2:br-eth2

[NWA] section
-------------

* **server_url**: The URL of the http/https server listening for NWA
  RESTful API::

    server_url = http://192.168.122.1:12081

* **access_key_id**: The access key ID of NWA RESTful API server.  The
  access key consists of an access key ID and secret access key, which
  are used to sign RESTful API requests that you make to NWA. ::

    access_key_id = mjivAk6O3G4Ko/0mD8mHUyQwqugEPgTe0FSli8REyN4=

* **secret_access_key**: The secret access key of NWA Restful API
  server.  The access key consists of an access key ID and secret
  access key, which are used to sign RESTful API requests that you
  make to NWA. ::

    secret_access_key = /3iSORtq1E3F+SQtQg6YN00eM3GUda0EKqWDUV/mvqo=

* **resource_group_name**: A default rerouce group name when NWA
  tenant is created. ::

    resource_group_name = OpenStack/DC/APP

* **scenario_polling_timer**: Specifies the polling interval of the
  scenario in seconds. ::

    scenario_polling_timer = 5

* **scenario_polling_count**: Specifies the polling counts of the
  scenario. ::

    scenario_polling_count = 300

* **region_name**: A region name (It is the prefix of NWA tenant name). ::

    region_name = T01DC

* **resource_group_file**: Load the table of NWA resource group
  from the file. ::

    resource_group_file = resource_group.json

* **use_necnwa_router**: If you use OpenStack L3 Router insted of NEC NWA Router,
  it set to False. The default value is True. ::

    use_necnwa_router = True

NWA resource group file
=======================

It is usually placed at
"/etc/neutron/plugins/nec/resource_group.json."

This file contains a table of NWA resource group.  The format of the
file is JSON.

The ``physical_network`` is a name of physical network which is used
in neutron.  It should be set to the same value as
``ResourceGroupName`` member.

The ``device_owner`` is the owner of the device in OpenStack.

It is specified as ``compute:AVAILABILITY_ZONE``, the VM that has a
nova boot option ``--available-zone`` is created on the physical
network corresponding with the device owner.

If the option ``--available-zone`` is not specified in nova boot,
regarded as ``compute:None`` has been specified.

All available DHCP agent in OpenStack specifies as ``network:dhcp``.

The ``ResourceGroupName`` is a name of NWA's resource group name.

::

    [
       {
           "physical_network": "OpenStack/DC/HA1",
           "device_owner": "compute:DC01_KVM01_ZONE01",
           "ResourceGroupName": "OpenStack/DC/HA1"
       },
       {
           "physical_network": "OpenStack/DC/HA2",
           "device_owner": "compute:DC01_KVM02_ZONE02",
           "ResourceGroupName": "OpenStack/DC/HA2"
       },
       {
           "physical_network": "OpenStack/DC/HA1",
           "device_owner": "compute:None",
           "ResourceGroupName": "OpenStack/DC/HA1"
       },
       {
           "physical_network": "OpenStack/DC/HA2",
           "device_owner": "compute:None",
           "ResourceGroupName": "OpenStack/DC/HA2"
       },
       {
           "physical_network": "OpenStack/DC/HA1",
           "device_owner": "network:dhcp",
           "ResourceGroupName": "OpenStack/DC/HA1"
       },
       {
           "physical_network": "OpenStack/DC/HA2",
           "device_owner": "network:dhcp",
           "ResourceGroupName": "OpenStack/DC/HA2"
       },
       {
           "physical_network": "OpenStack/DC/APP",
           "device_owner": "network:router_gateway",
           "ResourceGroupName": "OpenStack/DC/APP"
       },
       {
           "physical_network": "OpenStack/DC/APP",
           "device_owner": "network:router_interface",
           "ResourceGroupName": "OpenStack/DC/APP"
       },
    ]
