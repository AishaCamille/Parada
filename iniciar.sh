#!/usr/bin/env sh
# Atalho de inicialização no Linux: carrega a demonstração por padrão.
PARADA_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
exec sh "$PARADA_SCRIPT_DIR/carregar_linux.sh" "$@"
