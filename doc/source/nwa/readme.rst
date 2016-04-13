==============================
Introduction of NEC NWA plugin
==============================

.. toctree::
   :maxdepth: 1

   Installation <installation>
   Settings <settings>
   DevStack support <devstack>

NWA plugin consists of plugin driver and agent to operate the NWA made
by NEC from OpenStack.

NWA is a product of NEC which manages network equipment of Firewall
and Load Balancer unitarily from Windows GUI.

By using the NWA plugin, and you can use NWA's convenience with
mapping the network's physical or logical configuration from
OpenStack.

So the person in charge can change the network configuration which is
occurred such as organization restructuring, more easily with using
GUI.

If you define the network physical configuration on NWA's GUI,
OpenStack recognizes as logical router(Firewall) or Load Balancer.

When a network and a router are operated on OpenStack, NWA executes a
mapping of the most suitable setting automatically, and it's possible
to communicate with other networks or tenant VM (virtual instance)
becomes possible to block off as the network which became independent.
