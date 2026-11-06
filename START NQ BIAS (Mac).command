#!/bin/bash
cd "$(dirname "$0")" || exit 1
export PYTHONUTF8=1

if [ ! -f .venv/installed.ok ]; then
  echo
  echo "  Første gang: setter opp programmet. Dette tar 1–3 minutter..."
  echo
  PY=""
  for c in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)' 2>/dev/null; then
      PY="$c"; break
    fi
  done
  if [ -z "$PY" ]; then
    echo "  Fant ikke Python 3.10 eller nyere."
    echo "  1. Nettsiden python.org åpnes nå. Last ned og installer Python."
    echo "  2. Dobbeltklikk på denne filen igjen."
    open "https://www.python.org/downloads/"
    read -p "  Trykk Enter for å lukke"
    exit 1
  fi
  rm -rf .venv
  if "$PY" -m venv .venv && .venv/bin/python -m pip install --upgrade pip -q && .venv/bin/python -m pip install -r requirements.txt; then
    touch .venv/installed.ok
    echo; echo "  Ferdig installert!"; echo
  else
    rm -rf .venv
    echo; echo "  Installasjonen feilet. Sjekk nettforbindelsen og dobbeltklikk på filen igjen."
    read -p "  Trykk Enter for å lukke"
    exit 1
  fi
fi

.venv/bin/python nqbias.py --menu
