.. _nwa-devstack:

===============================
DevStack support for NWA plugin
===============================

This DevStack external plugin installs NEC plugin library
so that Neutron NEC NWA plugin can be enabled.

To use this DevStack plugin, add the following to your local.conf::

    enable_plugin networking-nec https://git.openstack.org/openstack/networking-nec [<branch>]

Examples
========

Minimum sample local.conf::

    [[local|localrc]]
    # Enable neutron services
    disable_service n-net
    enable_service neutron q-svc q-agt
    enable_service q-dhcp
    enable_service q-meta

    # NEC plugin
    Q_PLUGIN=nec
    enable_plugin networking-nec https://git.openstack.org/openstack/networking-nec

    # NWA server configurations
    NECNWA_SERVER_URL="http://127.0.0.1:12081"
    NECNWA_ACCESS_KEY_ID="mjivAk6O3G4Ko/0mD8mHUyQwqugEPgTe0FSli8REyN4="
    NECNWA_SECRET_ACCESS_KEY="/3iSORtq1E3F+SQtQg6YN00eM3GUda0EKqWDUV/mvqo="

    # Run neutron-nwa-agent
    enable_plugin nwa-agt

    [[post-config|/etc/neutron/dhcp_agent.ini]]
    [DEFAULT]
    enable_isolated_metadata = True

References
==========

* `DevStack externally hosted plugins`_

.. _DevStack externally hosted plugins: http://docs.openstack.org/developer/devstack/plugins.html#externally-hosted-plugins
