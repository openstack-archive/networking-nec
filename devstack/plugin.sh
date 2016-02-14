NETWORKING_NEC_DIR=$(cd $(dirname $BASH_SOURCE)/.. && pwd)

function source_plugin {
    if [[ "$Q_PLUGIN" == "nec" ]]; then
        source $NETWORKING_NEC_DIR/devstack/lib/nec_plugin
    fi
}

if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
    source_plugin
elif [[ "$1" == "stack" && "$2" == "install" ]]; then
    setup_develop $NETWORKING_NEC_DIR
elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    # It needs to be started before starting neutron-server.
    # run_phase extra is too late because create_neutron_initial_network
    # will be called just after start_neutron_service_and_check.
    start_nwa_agent
elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    :
elif [[ "$1" == "unstack" ]]; then
    source_plugin
elif [[ "$1" == "clean" ]]; then
    source_plugin
fi
