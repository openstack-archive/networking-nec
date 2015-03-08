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
elif [[ "$1" == "unstack" ]]; then
    source_plugin
elif [[ "$1" == "clean" ]]; then
    source_plugin
fi
