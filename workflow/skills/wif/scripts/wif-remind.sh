#!/usr/bin/env bash
WIF_NOTE_KIND=reminder exec bash "$(dirname "${BASH_SOURCE[0]}")/wif-note.sh" "$@"
