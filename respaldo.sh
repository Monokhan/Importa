#!/usr/bin/env bash
# Respaldo consistente de la base de datos (funciona con la app corriendo, modo WAL)
set -euo pipefail
DB="${IMPORTA_DB:-${IMPORTO_DB:-${CHILEIMPORT_DB:-importa.db}}}"
[ -f "$DB" ] || DB="chileimport.db"      # base de una versión anterior
mkdir -p respaldos
python3 -c "
import sqlite3, sys, datetime
origen = sqlite3.connect(sys.argv[1])
destino = sqlite3.connect('respaldos/importa_%s.db' % datetime.date.today())
origen.backup(destino); destino.close(); origen.close()
print('Respaldo creado en respaldos/')
" "$DB"
