#!/usr/bin/env bash
# Genera un mapa compacto del vault para meterlo en el prompt de E.V.
#
# Para qué: sin esto, casi cualquier pregunta la obliga a hacer Glob + Grep
# antes de contestar, y cada ida y vuelta de herramienta cuesta segundos.
# Medido: una pregunta que lee archivos tarda ~7.6 s contra ~2.3 s de una que
# no. Con el mapa en el prompt ya sabe qué existe y dónde, así que muchas
# preguntas las contesta directo y solo abre archivos cuando de verdad
# necesita el contenido.
#
# Se regenera solo cuando el vault cambia (se compara con el archivo más nuevo).
set -uo pipefail

VAULT="${EV_VAULT:-$HOME/Documents/Obsidian Vault}"
DESTINO="${1:-$HOME/ev/.indice}"

cd "$VAULT" 2>/dev/null || exit 0

# ¿Hace falta regenerarlo? Solo si hay algo más nuevo que el índice.
if [ -f "$DESTINO" ]; then
  nuevo=$(find . -name '*.md' -newer "$DESTINO" \
            -not -path './kino-personal/*' -not -path './.git/*' \
            -not -path './.obsidian/*' -print -quit 2>/dev/null)
  [ -z "$nuevo" ] && exit 0
fi

{
  printf '# Mapa del vault (generado, %s)\n\n' "$(date +%F)"
  printf 'Esto es lo que EXISTE y dónde. Úsalo para no andar buscando a ciegas:\n'
  printf 'si la pregunta se contesta sabiendo qué hay, contesta directo. Abre\n'
  printf 'archivos solo cuando de verdad necesites lo que dicen por dentro.\n'
  printf 'Si algo no aparece aquí, probablemente no existe.\n\n'

  find . -type f -name '*.md' \
       -not -path './kino-personal/*' -not -path './.git/*' \
       -not -path './.obsidian/*' -not -path './node_modules/*' \
       2>/dev/null \
  | sed 's|^\./||' | sort \
  | awk -F/ '
      {
        carpeta = ""
        for (i = 1; i < NF; i++) carpeta = carpeta (i > 1 ? "/" : "") $i
        if (carpeta == "") carpeta = "(raíz)"
        nombre = $NF
        sub(/\.md$/, "", nombre)
        if (carpeta != previa) {
          if (previa != "") printf "\n"
          printf "%s/\n  ", carpeta
          previa = carpeta
          primero = 1
        }
        printf "%s%s", (primero ? "" : " · "), nombre
        primero = 0
      }
      END { printf "\n" }
    '
} > "$DESTINO"

printf '%s\n' "$DESTINO"
