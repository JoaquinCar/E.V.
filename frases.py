#!/usr/bin/env python3
"""
Lee el stream-json de `claude -p` y escupe oraciones completas, una por línea,
ya limpias para que las lea `say`.

Existe para que E.V. empiece a hablar mientras el modelo todavía está
escribiendo: la primera oración sale a los ~2 s en vez de a los ~15 s.
"""
import json
import re
import sys

# Corta después de . ! ? … seguido de espacio o fin.
# Los signos de apertura ¿¡ NO cierran oración.
FIN = re.compile(r'(?<=[.!?…])(?=\s)|(?<=[.!?…])$')

# No cortar en abreviaturas comunes ni en decimales (1.5, Dr., etc.)
NO_CORTAR = re.compile(r'(?:\b[A-ZÁÉÍÓÚÑ][a-z]{0,2}|\b\d+)\.$')

LIMPIEZAS = [
    (re.compile(r'```.*?```', re.S), ''),            # bloques de código
    (re.compile(r'`([^`]*)`'), r'\1'),               # código inline
    (re.compile(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]'), r'\1'),   # wikilinks
    (re.compile(r'\[([^\]]*)\]\([^)]*\)'), r'\1'),   # links markdown
    (re.compile(r'https?://\S+'), ''),               # urls
    (re.compile(r'^\s{0,3}#{1,6}\s*', re.M), ''),    # encabezados
    (re.compile(r'^\s*[-*+]\s+', re.M), ''),         # viñetas
    (re.compile(r'^\s*\d+\.\s+', re.M), ''),         # listas numeradas
    (re.compile(r'\*\*([^*]*)\*\*'), r'\1'),         # negritas
    (re.compile(r'(?<!\w)[*_]([^*_]+)[*_](?!\w)'), r'\1'),    # cursivas
    (re.compile(r'[|>#`~]'), ''),                    # residuos
    (re.compile(r'[\U0001F300-\U0001FAFF☀-➿]'), ''),  # emoji
    (re.compile(r'[ \t]+'), ' '),
]


def limpiar(texto: str) -> str:
    for patron, repl in LIMPIEZAS:
        texto = patron.sub(repl, texto)
    return texto.strip()


def emitir(frase: str) -> None:
    frase = limpiar(frase)
    if frase:
        print(frase, flush=True)   # flush: si no, no hay streaming de verdad


def main() -> None:
    buf = ''
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            evt = json.loads(linea)
        except json.JSONDecodeError:
            continue

        if evt.get('type') != 'stream_event':
            continue
        inner = evt.get('event', {})

        # Aviso de herramienta: leer el vault no genera texto, así que sin esto
        # la espera se siente muerta. Se marca con \x01 para que bash lo pinte
        # pero no lo mande a la voz.
        if inner.get('type') == 'content_block_start':
            bloque = inner.get('content_block', {})
            if bloque.get('type') == 'tool_use':
                nombre = {'Read': 'leyendo el vault',
                          'Glob': 'buscando archivos',
                          'Grep': 'buscando en el vault',
                          'Write': 'escribiendo',
                          'Edit': 'editando'}.get(bloque.get('name'), 'trabajando')
                print('\x01' + nombre, flush=True)
            continue

        if inner.get('type') != 'content_block_delta':
            continue
        delta = inner.get('delta', {})
        if delta.get('type') != 'text_delta':
            continue

        buf += delta.get('text', '')

        # Sacar todas las oraciones completas que ya haya en el buffer
        while True:
            m = FIN.search(buf)
            if not m:
                break
            corte = m.start()
            candidata = buf[:corte + 1]
            # No partir en "Dr." ni en "1." — espera más texto
            if NO_CORTAR.search(candidata.strip()) and len(buf) < 400:
                break
            emitir(candidata)
            buf = buf[corte + 1:].lstrip()

    if buf.strip():
        emitir(buf)


if __name__ == '__main__':
    main()
