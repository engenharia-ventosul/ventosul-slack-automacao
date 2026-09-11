#!/usr/bin/env bash
# Roda toda a suíte de testes (não precisa do Slack real nem de rede).
set -e
cd "$(dirname "$0")"
python3 -m unittest discover -s tests -v
