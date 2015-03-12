# devstack-plugins for NEC OpenFlow Neutron plugin integration

As a part of vendor plugins/drivers decomposition work in Kilo,
NEC plugin decomposition has been done.

This devstack external plugin installs NEC plugin library
so that Neutron NEC OpenFlow plugin can be enabled.

To use this devstack plugin, add the following to your local.conf::

    enable_plugin networking-nec https://git.openstack.org/stackforge/networking-nec

## Examples (minimum)

Sample local.conf::

    [[local|localrc]]
    disable_service n-net
    enable_service neutron q-svc q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    enable_service q-lbaas
    enable_service q-fwaas
    enable_service q-vpn

    # NEC plugin
    Q_PLUGIN=nec
    enable_plugin networking-nec https://git.openstack.org/stackforge/networking-nec

    # Trema Sliceable Switch (the following three lines are required at least)
    OFC_DRIVER=trema
    OFC_OFP_PORT=6653
    enable_plugin trema-devstack-plugin https://github.com/nec-openstack/trema-devstack-plugin

    # ProgrammableFlow controller
    #OFC_DRIVER=pfc

## References

http://docs.openstack.org/developer/devstack/plugins.html#externally-hosted-plugins
