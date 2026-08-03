#!/usr/bin/env python3
"""
Mantiene UN proceso de `claude` vivo entre turnos.

Por qué: arrancar `claude -p` cuesta ~3-6 s cada vez. Medido con el modelo más
rápido, sin prompt y sin herramientas, un turno mínimo tardaba 5.7 s — casi
todo era arranque, no pensar. Con el proceso vivo esa parte se paga una sola
vez, al principio.

Usa `--input-format stream-json`: se le mandan turnos por stdin y contesta por
stdout sin morirse.

Protocolo con bash (dos FIFOs, línea por línea):
    entra:  la pregunta, en una línea
    sale:   una oración limpia por línea, y \\x04 cuando el turno termina
            (las líneas que empiezan con \\x01 son avisos de herramienta)
Manda 'READY' cuando el proceso ya está arriba. Si algo truena manda
'ERROR ...' y bash se regresa solo a lanzar un `claude` por turno.
"""
import json
import os
import signal
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frases import FIN, NO_CORTAR, limpiar  # noqa: E402

FIFO_IN, FIFO_OUT = sys.argv[1], sys.argv[2]
FIN_DE_TURNO = '\x04'

fin = open(FIFO_IN, 'r')
fout = open(FIFO_OUT, 'w')


def responder(linea: str) -> None:
    fout.write(linea + '\n')
    fout.flush()


def construir_comando() -> list:
    cmd = ['claude', '-p',
           '--input-format', 'stream-json',
           '--output-format', 'stream-json',
           '--include-partial-messages', '--verbose']

    reanudar = os.environ.get('EV_RESUME', '')
    if reanudar:
        cmd += ['--resume', reanudar]
    else:
        cmd += ['--session-id', os.environ['EV_SESSION']]

    sistema = os.environ.get('EV_SYSTEM_PROMPT', '')
    if sistema:
        cmd += ['--append-system-prompt', sistema]

    herramientas = os.environ.get('EV_TOOLS', '').split()
    if herramientas:
        cmd += ['--allowedTools', *herramientas]

    vetado = [v for v in os.environ.get('EV_DENY', '').split('\n') if v.strip()]
    if vetado:
        cmd += ['--disallowedTools', *vetado]

    modelo = os.environ.get('EV_MODEL_NAME', '')
    if modelo:
        cmd += ['--model', modelo]
    return cmd


try:
    proc = subprocess.Popen(
        construir_comando(),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=open(os.environ.get('EV_ERRLOG', os.devnull), 'a'),
        text=True, bufsize=1,
        cwd=os.environ.get('EV_VAULT', os.getcwd()))
except Exception as e:                                   # noqa: BLE001
    responder(f'ERROR arranque: {type(e).__name__}: {e}')
    sys.exit(1)


def cerrar(*_):
    try:
        proc.terminate()
    except Exception:                                    # noqa: BLE001
        pass
    os._exit(0)


signal.signal(signal.SIGTERM, cerrar)
signal.signal(signal.SIGINT, cerrar)

HERRAMIENTAS_ES = {
    'Read': 'leyendo el vault', 'Glob': 'buscando archivos',
    'Grep': 'buscando en el vault', 'Write': 'escribiendo',
    'Edit': 'editando', 'Task': 'lanzando agentes',
    'Bash': 'en la terminal', 'WebSearch': 'buscando en internet',
    'WebFetch': 'leyendo una página', 'Skill': 'usando una skill',
}


def leer_turno() -> None:
    """Consume la salida de claude hasta el fin del turno, emitiendo oraciones."""
    buf = ''
    for linea in proc.stdout:
        linea = linea.strip()
        if not linea:
            continue
        try:
            evt = json.loads(linea)
        except json.JSONDecodeError:
            continue

        # Fin del turno: soltar lo que quede en el buffer y avisar.
        if evt.get('type') == 'result':
            if buf.strip():
                t = limpiar(buf)
                if t:
                    responder(t)
            responder(FIN_DE_TURNO)
            return

        if evt.get('type') != 'stream_event':
            continue
        inner = evt.get('event', {})

        if inner.get('type') == 'content_block_start':
            bloque = inner.get('content_block', {})
            if bloque.get('type') == 'tool_use':
                responder('\x01' + HERRAMIENTAS_ES.get(bloque.get('name'),
                                                       'trabajando'))
            continue

        if inner.get('type') != 'content_block_delta':
            continue
        delta = inner.get('delta', {})
        if delta.get('type') != 'text_delta':
            continue

        buf += delta.get('text', '')
        while True:
            m = FIN.search(buf)
            if not m:
                break
            corte = m.start()
            candidata = buf[:corte + 1]
            if NO_CORTAR.search(candidata.strip()) and len(buf) < 400:
                break
            t = limpiar(candidata)
            if t:
                responder(t)
            buf = buf[corte + 1:].lstrip()

    # stdout se cerró: claude murió.
    responder('ERROR claude terminó')
    responder(FIN_DE_TURNO)


responder('READY')

for pregunta in fin:
    pregunta = pregunta.strip()
    if not pregunta or pregunta == '__QUIT__':
        break
    try:
        proc.stdin.write(json.dumps({
            'type': 'user',
            'message': {'role': 'user',
                        'content': [{'type': 'text', 'text': pregunta}]},
        }) + '\n')
        proc.stdin.flush()
    except Exception as e:                               # noqa: BLE001
        responder(f'ERROR envío: {type(e).__name__}: {e}')
        responder(FIN_DE_TURNO)
        break
    leer_turno()

cerrar()
