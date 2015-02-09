# devstack-plugins for NEC OpenFlow Neutron plugin integration

As a part of vendor plugins/drivers decomposition work in Kilo,
NEC plugin decomposition is under work (as experimental).

This devstack external plugin installs NEC plugin library
so that Neutron NEC OpenFlow plugin can be enabled.

To use this devstack plugin, add the following to your local.conf::

    enable_plugin networking-nec https://github.com/nec-openstack/networking-nec.git master

## Examples

Sample local.conf::

    [[local|localrc]]
    #OFFLINE=True
    RECLONE=True
    
    NEUTRON_REPO=https://github.com/nec-openstack/neutron.git
    NEUTRON_BRANCH=nec-split
    
    disable_service heat h-api h-api-cfn h-api-cw h-eng
    
    KEYSTONE_TOKEN_FORMAT=UUID
    PRIVATE_NETWORK_NAME=net1
    PUBLIC_NETWORK_NAME=ext_net
    
    disable_service n-net
    enable_service neutron q-svc q-agt
    enable_service q-dhcp
    enable_service q-l3
    enable_service q-meta
    enable_service q-lbaas
    enable_service q-fwaas
    enable_service q-vpn
    enable_service q-metering
    
    # NEC plugin specific
    
    Q_PLUGIN=nec
    enable_plugin networking-nec https://github.com/nec-openstack/networking-nec.git master
    #GRE_REMOTE_IPS=10.56.51.252:10.56.51.210:10.56.51.153
    #GRE_LOCAL_IP=10.56.51.252
    #OVS_INTERFACE=eth1
    OFC_DRIVER=trema
    if [ "$OFC_DRIVER" = "trema" ]; then
      enable_plugin trema/devstack-plugins /home/ubuntu/devstack-plugins trema
      OFC_OFP_PORT=6653
      #TREMA_LOG_LEVEL=debug
    fi
    
    # DevStack configuration
    
    LOGDIR=$DEST/logs
    SCREEN_LOGDIR=$LOGDIR
    SCREEN_HARDSTATUS="%{= rw} %H %{= wk} %L=%-w%{= bw}%30L> %n%f %t*%{= wk}%+Lw%-17< %-=%{= gk} %y/%m    /%d %c"
    LOGFILE=$LOGDIR/devstack.log
    LOGDAYS=1
    
    ADMIN_PASSWORD=pass
    MYSQL_PASSWORD=stackdb
    RABBIT_PASSWORD=stackqueue
    SERVICE_PASSWORD=$ADMIN_PASSWORD
    SERVICE_TOKEN=xyzpdqlazydog
    
    [[post-config|/etc/neutron/dhcp_agent.ini]]
    [DEFAULT]
    enable_isolated_metadata = True

## References

http://docs.openstack.org/developer/devstack/plugins.html#externally-hosted-plugins
