============
Installation
============

Requirements
============

OpenFlow controller is required to make NEC OepnFlow plugin work.
A controller needs to support REST API available at `Sliceable Network Management API`_.

The following controllers are available:

* `Trema`_ with `Sliceable Switch`_ (distributed under GPL2)
* `NEC ProgrammableFlow Controller`_ (NEC Commercial Product)

.. _Sliceable Network Management API: https://github.com/trema/apps/wiki/Sliceable-Network-Management-API
.. _NEC ProgrammableFlow Controller: http://www.necam.com/SDN/
.. _Trema: https://github.com/trema/trema
.. _Sliceable Switch: https://github.com/trema/apps/tree/master/sliceable_switch

Running with DevStack
=====================

See :ref:`devstack`

Manual Installation
===================

(Kilo or later) Neutron integration is available.
After the core/vendor decomposition work, the main code is provided
as a separate python module called **networking-nec***,
and the shim code and configuration exist in the Neutron code tree.

The code is maintained at stackforge https://github.com/stackforge/networking-nec

The released versions of Python module is available at https://pypi.python.org/pypi/networking-nec.
To install::

    pip install networking-nec~=2015.1

Note that the version number like '''2015.1''' should
match the corresponding OpenStack release version
(e.g., 2015.1 for Kilo, 2015.2 for Liberty).

Of course, make sure to install Neutron itself.

From Folsom to Juno, NEC OpenFlow plugin was maintained
in the main repo of Neutron https://github.com/openstack/neutron.
