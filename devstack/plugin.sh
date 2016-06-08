NETWORKING_NEC_DIR=$(cd $(dirname $BASH_SOURCE)/.. && pwd)

function source_plugin {
    if [[ "$Q_PLUGIN" == "nec" ]]; then
        if is_nwa_plugin; then
            source $NETWORKING_NEC_DIR/devstack/lib/nwa_plugin
        else
            source $NETWORKING_NEC_DIR/devstack/lib/nec_plugin
        fi
    fi
}

function is_nwa_plugin {
    if [[ -n "$NECNWA_SERVER_URL" ]]; then
        return 0
    else
        return 1
    fi
}

if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
    source_plugin
elif [[ "$1" == "stack" && "$2" == "install" ]]; then
    setup_develop $NETWORKING_NEC_DIR
elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    if is_nwa_plugin; then
        # This must be done after neutron database is populated and
        # before starting neutron server.
        populate_nwa_database
        # It needs to be started before starting neutron-server.
        # run_phase extra is too late because create_neutron_initial_network
        # will be called just after start_neutron_service_and_check.
        start_nwa_agent
    fi
elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    :
elif [[ "$1" == "unstack" ]]; then
    source_plugin
elif [[ "$1" == "clean" ]]; then
    source_plugin
fi
