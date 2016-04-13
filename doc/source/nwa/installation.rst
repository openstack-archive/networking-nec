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

    pip install networking-nec~=2016.4

Note that the version number like '''2016.4''' should match the
corresponding OpenStack release version (e.g., 2016.4 for Mitaka).

