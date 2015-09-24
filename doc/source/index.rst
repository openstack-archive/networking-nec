.. networking-nec documentation master file, created by
   sphinx-quickstart on Tue Jul  9 22:26:36 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

===================================================
Neutron plugins/drivers for NEC networking products
===================================================

``networking-nec`` library provides Neutron plugins/drivers
for `NEC SDN`_ networking products` (mainly OpenFlow related at now)
and `Trema`_ `Sliceable Switch`_ (reference implementation).

In 2015.1 release (Kilo development cycle) in OpenStack, Neutron
community decided to decompose vendor plugins/drivers from the neutron
code repo to address many pain points. NEC OpenFlow Neutron plugin is
maintained in a separate module.

* Documentation: https://wiki.openstack.org/wiki/Neutron/NEC_OpenFlow_Plugin
* Source:

  * http://git.openstack.org/cgit/stackforge/networking-nec
  * https://github.com/stackforge/networking-nec

* Bugs: http://bugs.launchpad.net/networking-nec
* Free software: Apache license

User Guide
----------

.. toctree::
   :maxdepth: 2

   Introduction <readme>
   installation
   settings
   DevStack support <devstack>
   contributing

.. _NEC SDN: http://www.necam.com/SDN/
.. _Trema: https://github.com/trema/trema
.. _Sliceable Switch: https://github.com/trema/apps/tree/master/sliceable_switch
