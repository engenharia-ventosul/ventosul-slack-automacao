#!/usr/bin/env bash
# Atalho de conveniência: dá duplo-clique/`./iniciar.sh` e pronto.
set -e
cd "$(dirname "$0")"
python3 bootstrap.py
