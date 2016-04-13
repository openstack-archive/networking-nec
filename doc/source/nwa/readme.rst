==============================
Introduction of NEC NWA plugin
==============================

.. toctree::
   :maxdepth: 1

   Installation <installation>
   Settings <settings>
   DevStack support <devstack>

NWA plugin consists of plugin driver and agent, and both of them are
used to operate OpenStack from NWA made by NEC.

By using the NWA plugin, and you can use NWA's convenience with
mapping the network's physical or logical configuration from
OpenStack.

So the person in charge can change the network configuration which is
occurred such as organization restructuring, more easily with using
NWA GUI.

When a network and a router are operated on OpenStack, NWA executes a
mapping of the most suitable setting automatically, and it's possible
to communicate with other networks or tenant VM (virtual instance)
becomes possible to block off as the network which became independent.
