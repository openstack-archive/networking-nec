.. networking-nec documentation master file, created by
   sphinx-quickstart on Tue Jul  9 22:26:36 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

===========================================
Neutron plugins for NEC networking products
===========================================

``networking-nec`` library provides Neutron plugins/drivers
for `NEC SDN <http://www.necam.com/SDN/>`_ networking products`.

* Documentation: http://networking-nec.readthedocs.org/
* Source: http://git.openstack.org/cgit/openstack/networking-nec
* Bugs: http://bugs.launchpad.net/networking-nec
* License: Apache License 2.0

NEC NWA plugin
==============

In Mitaka release, NWA plugin was added as a new integration layer
with NEC NWA (Network Automation) product.
NWA plugin consists of layer-2 core plugin and layer-3 service plugin.

.. toctree::
   :maxdepth: 1

   nwa/readme
   nwa/installation
   nwa/settings
   nwa/devstack

NEC OpenFlow plugin
===================

NEC OpenFlow plugin in Liberty or older releases supported
`NEC ProgrammableFlow controller <http://www.necam.com/SDN/>`_ and
`Trema <https://github.com/trema/trema>`_
`Sliceable Switch <https://github.com/trema/apps/tree/master/sliceable_switch>`_
(as reference implementation).

.. warning::

   NEC OpenFlow plugin was deprecated in OpenStack Liberty release (2015.2)
   and removed during Mitaka development cycle.
   Note that the production support will be continued based
   on the production support policy.

.. toctree::
   :maxdepth: 1

   openflow/readme
   openflow/installation
   openflow/settings
   openflow/devstack

Developers Guide
================

.. toctree::
   :maxdepth: 2

   tips
   contributing
