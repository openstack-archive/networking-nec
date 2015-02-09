NETWORKING_NEC_DIR=$(cd $(dirname $BASH_SOURCE)/.. && pwd)

function install_networking_nec {
    setup_develop $NETWORKING_NEC_DIR
}

if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
    install_networking_nec
fi
