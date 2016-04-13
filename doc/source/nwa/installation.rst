==============================
Installation of NEC NWA plugin
==============================

Requirements
============

To use the NWA plugin, NWA made by NEC is needed.

After an OpenStack installation, you need to install networking-nec
Python package, configure the physical network by NWA and configure
the NWA plugin.

Running with DevStack
=====================

See :ref:`nwa-devstack`

Manual Installation
===================

The released versions of Python module is available at
https://pypi.python.org/pypi/networking-nec.

To install::

    pip install networking-nec~=2.0

NEC NWA plugin is available from version ``2.0.0`` or later.
The ``2.y.z`` series of networking-nec supports Neutron Mitaka release.
