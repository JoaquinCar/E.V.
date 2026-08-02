#!/usr/bin/env python3
"""
Demonio de voz neural (Kokoro) para E.V.

Existe como demonio y no como script por oración porque cargar el modelo cuesta
~10 s: si se pagara en cada frase, el streaming no serviría de nada. Aquí se
carga una vez y después cada oración se sintetiza en décimas de segundo.

Protocolo (dos FIFOs, línea por línea):
    entra:  una oración de texto
    sale:   la ruta de un .wav listo para reproducir
Al terminar de cargar el modelo manda 'READY'. Si algo truena manda 'ERROR ...'
y bash cae de vuelta a `say` sin dejar a Kino sin voz.
"""
import atexit
import os
import signal
import sys
import tempfile
import warnings

warnings.filterwarnings('ignore')

FIFO_IN, FIFO_OUT = sys.argv[1], sys.argv[2]
VOZ = os.environ.get('EV_KOKORO_VOICE', 'ef_dora')
# 1.0 = ritmo natural del modelo. Arriba de ~1.4 empieza a atropellarse.
try:
    VELOCIDAD = float(os.environ.get('EV_KOKORO_SPEED', '1.15'))
except ValueError:
    VELOCIDAD = 1.15
LANG = os.environ.get('EV_KOKORO_LANG', 'e')   # 'e' = español en Kokoro
SR = 24000

# El rendezvous de los FIFOs va ANTES de importar torch: así bash no se queda
# bloqueado los ~10 s que tarda la carga y puede seguir escuchando mientras.
fin = open(FIFO_IN, 'r')
fout = open(FIFO_OUT, 'w')


def responder(linea: str) -> None:
    fout.write(linea + '\n')
    fout.flush()


try:
    import soundfile as sf
    from kokoro import KPipeline
    # repo_id explícito: sin él, kokoro imprime un WARNING en cada arranque
    # que se cuela a la terminal y ensucia la conversación.
    pipeline = KPipeline(lang_code=LANG, repo_id='hexgrad/Kokoro-82M')
except Exception as e:                                   # noqa: BLE001
    responder(f'ERROR carga: {type(e).__name__}: {e}')
    sys.exit(1)

tmpdir = tempfile.mkdtemp(prefix='ev_kokoro_')


def limpiar_todo() -> None:
    """El directorio entero se va al salir: antes quedaba uno tirado por sesión."""
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


atexit.register(limpiar_todo)

# atexit NO corre con señales, y bash mata el demonio con SIGTERM al salir.
# Sin esto quedaba un directorio de WAVs tirado por cada sesión.
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

responder('READY')

n = 0
for linea in fin:
    texto = linea.strip()
    if not texto:
        continue
    if texto == '__QUIT__':
        break
    try:
        trozos = []
        for _, _, audio in pipeline(texto, voice=VOZ, speed=VELOCIDAD):
            trozos.append(audio)
        if not trozos:
            responder('ERROR sin audio')
            continue
        if len(trozos) == 1:
            audio = trozos[0]
        else:
            import numpy as np
            audio = np.concatenate(trozos)
        n += 1
        ruta = os.path.join(tmpdir, f'{n:05d}.wav')
        sf.write(ruta, audio, SR)
        responder(ruta)
    except Exception as e:                               # noqa: BLE001
        responder(f'ERROR sintesis: {type(e).__name__}: {e}')
