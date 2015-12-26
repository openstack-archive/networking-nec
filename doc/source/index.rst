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

* Documentation:

  * http://pythonhosted.org/networking-nec/
  * https://wiki.openstack.org/wiki/Neutron/NEC_OpenFlow_Plugin

* Source:

  * http://git.openstack.org/cgit/openstack/networking-nec
  * https://github.com/openstack/networking-nec

* Bugs: http://bugs.launchpad.net/networking-nec
* License: Apache License 2.0

.. warning::

   The current plugin, NEC OpenFlow plugin, is deprecated in
   OpenStack Liberty release (2015.2).
   A new driver for NEC NWA (Network Automation) product is coming.
   Note that the production support will be continued based
   on the production support policy.

.. note::

   In 2015.1 release (Kilo development cycle) in OpenStack, Neutron
   community decided to decompose vendor plugins/drivers from the neutron
   code repo to address many pain points. NEC OpenFlow Neutron plugin is
   maintained in a separate module.

User Guide
----------

.. toctree::
   :maxdepth: 2

   Introduction <readme>
   installation
   settings

Developers Guide
----------------

.. toctree::
   :maxdepth: 2

   DevStack support <devstack>
   tips
   contributing


.. _NEC SDN: http://www.necam.com/SDN/
.. _Trema: https://github.com/trema/trema
.. _Sliceable Switch: https://github.com/trema/apps/tree/master/sliceable_switch
