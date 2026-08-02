# E.V.

**Un asistente de voz que vive en tu terminal, conoce tus notas y no cuesta un peso.**

*A local-first voice assistant for your Obsidian vault. Speech-to-text, LLM and
text-to-speech all run on your machine — no API keys, no subscriptions beyond
the one you already have. Docs in Spanish; the code speaks Spanish too.*

---

## Cómo empezó esto

Salí del cine un sábado en la noche. Acababa de ver a Peter Parker hablarle a
E.V. —la IA que él mismo se construyó, no la que heredó de Tony Stark— y me
quedé con esa idea encima.

Llegué a mi casa pensando que iba a costar dinero. Que necesitaba una API, una
suscripción más, algo de OpenAI. Resulta que no: mi Mac ya traía la voz, Whisper
corre local, y la parte cara —el cerebro— ya la estaba pagando.

Terminé como a la una de la mañana. Esto es lo que salió.

```
$ ev
E.V. lista · voz: Kokoro ef_dora (neural, local) · sesión nueva
manos libres: habla y se corta sola
cualquier tecla la interrumpe mientras habla · 'adiós' o Ctrl-C para salir

🎙  habla…
  tú → oye, ¿qué tengo pendiente del proyecto?
     leyendo el vault…
🔊 E.V. Una sola cosa: la fase cero, que lleva seis días esperando.
        Es un pip install y dos llamadas. ¿La arrancamos?
```

No presionas nada para hablar. Empiezas, y cuando te callas ella arranca sola.
Si se está extendiendo de más, cualquier tecla la calla.

## Qué hace

- **Te escucha** — micrófono siempre listo, corta sola cuando terminas de hablar
- **Conoce tus notas** — las lee de verdad antes de contestar, no inventa
- **Te contesta con voz** — neural y local, no la voz robótica del sistema
- **Empieza a hablar mientras piensa** — la primera oración sale a los ~4 s
- **Se deja interrumpir** — como cualquier conversación decente
- **Escribe en tus notas** — le dictas y guarda, con reglas para no romper nada
- **Lanza agentes** — *"avienta tres que revisen estas carpetas"*
- **Se acuerda de ti** — mantiene un archivo de memoria entre días

## Por qué cuesta cero

| Pieza | Con qué | Costo |
|---|---|---|
| Escuchar | `whisper.cpp` local, sobre la GPU | $0 |
| Grabar | `sox` | $0 |
| Pensar | `claude -p` con tu suscripción de Claude Code | ya lo pagas |
| Hablar | Kokoro-82M neural local (caída a `say`) | $0 |

Lo único que no es gratis es la suscripción de Claude Code, y si estás leyendo
esto probablemente ya la tienes. **No hay API keys en ningún lado.** Nada de lo
que dices sale de tu máquina salvo la pregunta misma.

> Nota honesta: las suscripciones Pro y Max están bloqueadas para harnesses de
> terceros desde abril de 2026. Esto no es un truco para saltarse eso — E.V.
> invoca el CLI oficial de Claude Code, que es exactamente para lo que existe.

## Instalación

Necesitas una Mac con Apple Silicon y el CLI de Claude Code ya instalado.

```bash
git clone https://github.com/JoaquinCar/E.V..git ~/ev
cd ~/ev

# escuchar y grabar
brew install whisper-cpp sox

# voz neural (opcional — sin esto usa la voz del sistema)
brew install espeak-ng python@3.12
python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt

# modelo de Whisper (~465 MB)
mkdir -p models && curl -L -o models/ggml-small.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin

# tu personalidad
cp EV.example.md EV.md          # edítalo: aquí va quién eres tú
cp memory/PERFIL.example.md memory/PERFIL.md

ln -s ~/ev/ev ~/.local/bin/ev
```

La primera vez macOS te va a pedir permiso de micrófono para la terminal.
Acéptalo o vas a grabar silencio.

**Configura `EV.md` antes de nada.** Es el archivo que la define: qué carpetas
tienes, quién eres, cómo quieres que te hable. Sin eso es genérica.

## Uso

```bash
ev                    # conversación por voz, manos libres
ev --escucha          # dormida hasta que digas su nombre
ev "pregunta"         # escribes, contesta con voz
ev -m "pregunta"      # mudo, solo texto
ev --nuevo            # olvida el hilo del día
```

### Modo despertador

```bash
$ ev --escucha
😴 dormida — di «E.V.» o «Ivi» para despertarla

   ·  y entonces le dije que no                 ← te oye, te ignora
👂 despierta
  tú → ¿qué tengo pendiente?
```

Responde a **E.V.** o a **Ivi**, y aguanta las variantes que Whisper suele
producir. Puedes decir solo su nombre y esperar el "¿Sí?", o soltarlo todo de
corrido: *"E.V., ¿qué tengo pendiente?"*.

Tras tres silencios seguidos se vuelve a dormir sola.

**Cuesta 0.1% de CPU y 4 MB de RAM mientras duerme.** Whisper solo corre cuando
hay sonido de verdad; el resto del tiempo solo hay un `rec` esperando.

### App de barra de menú

Si no te late tener una terminal abierta solo para que te escuche:

```bash
./app/construir.sh ~/Applications/E.V..app
open ~/Applications/E.V..app
```

Queda un ícono junto al reloj que cambia según lo que esté haciendo:
**🌙** apagada · **😴** dormida · **🎙** escuchando · **💭** pensando · **🔊** hablando.

Clic para despertarla o dormirla. El menú también abre la bitácora del día, su
memoria y su personalidad, y dispara una ronda.

Son ~250 líneas de Swift con AppKit y **no necesita Xcode** — se compila con
`swiftc` y se arma el bundle a mano. La app **no reimplementa nada**: lanza el
mismo script `ev` y lee su estado de un archivo, así que si prefieres la
terminal todo sigue funcionando igual.

Un detalle que resuelve más de lo que parece: un `.app` con su propio bundle id
recibe el permiso de micrófono **limpio y una sola vez**. Un servicio de
`launchd` suelto se pelea con TCC; la app no. Por eso ésta era la forma
correcta, y no un demonio invisible.

### Rondas proactivas

Que ella te busque a ti, no al revés:

```bash
ronda                    # una revisión ahora
ronda --instalar 08:00   # diaria a esa hora (launchd)
ronda --quitar
```

Revisa tus notas y te manda una notificación de macOS con **máximo tres cosas**
que valgan la pena. Edita `RONDA.md` para decidir de qué te avisa.

Si no hay nada real que decir responde `SIN NOVEDAD` y **no te notifica**. Una
alerta que no aporta enseña a ignorar las siguientes.

Ajustes por variable de entorno:

```bash
EV_PAUSA=2.5 ev             # más tiempo antes de cortarte (default 1.5 s)
EV_MIN_AMP=0.04 ev          # sube si tu cuarto es ruidoso
EV_KOKORO_VOICE=em_alex ev  # voz masculina
EV_KOKORO_SPEED=1.3 ev      # más rápida (default 1.15; arriba de 1.4 se atropella)
EV_TTS=say ev               # usa la voz del sistema
```

## Cómo funciona

```
  micrófono ──▶ sox ──▶ whisper.cpp ──▶ claude -p ──▶ Kokoro ──▶ bocina
              corta      transcribe      lee tus       sintetiza
            por silencio   (Metal)        notas        por oración
                                              │
                                        ┌─────┴─────┐
                                     git snapshot  bitácora
```

Cinco piezas:

- **`ev`** — el bucle. Bash, ~350 líneas.
- **`frases.py`** — parte el stream de Claude en oraciones completas conforme
  llegan, para que empiece a hablar antes de terminar de pensar.
- **`kokoro_daemon.py`** — la voz neural, como demonio con dos FIFOs. Cargar el
  modelo cuesta 3 s; si se pagara por oración, el streaming no serviría.
- **`EV.md`** — la personalidad. No es documentación, es el prompt.
- **`vetado.txt`** — lo que no puede ejecutar.

### Las tres capas de seguridad

E.V. puede correr comandos y escribir en tus notas. Eso da miedo, y con razón:
la entrada es voz transcrita, y Whisper a veces oye cosas que nadie dijo.

1. **Lista negra** (`vetado.txt`) — patrones prohibidos. Es por prefijo, así que
   es defensa en profundidad, **no un muro**.
2. **Confirmación hablada** — en modo headless no existe el "¿estás seguro?", así
   que la conversación misma hace de confirmación: antes de algo irreversible lo
   dice y cierra su turno.
3. **Respaldo automático a git** — cada turno que toque tus notas queda como un
   commit firmado por `E.V.`. Ésta es la red que sí atrapa.

```bash
git log --oneline    # qué hizo, turno por turno
git revert HEAD      # deshacer lo último
```

## Cosas que aprendí a golpes

Las dejo escritas porque me costaron la noche.

**Sox le escribe a la terminal por la puerta de atrás.** Corría `rec` en segundo
plano y presionabas ENTER para parar. Pero con un TTY real, sox pinta su medidor
de nivel directo en `/dev/tty`, saltándose `>/dev/null`, y de paso se come el
ENTER. La solución no fue silenciarlo: fue quitar el ENTER y cortar por silencio.

**Una función no puede imprimir y devolver por el mismo canal.** `escuchar()`
devolvía la transcripción por stdout… e imprimía "🎙 habla…" por stdout. El
texto de la interfaz se pegaba a lo que decías y todo eso le llegaba al modelo.
Toda la UI se fue a stderr.

**Whisper alucina con el silencio.** Le das ruido de cuarto y se inventa frases
hechas — un "¿Estás ahí?" que nadie dijo. Ahora mide la amplitud antes de
molestarse en transcribir.

**`--session-id` crea, `--resume` continúa.** No son intercambiables. Usar el
primero dos veces te da `Session ID already in use` en el segundo turno.

**El orden de los efectos de sox importa.** `trim` va antes que `silence`. Al
revés, si nunca hablas se queda esperando el primer sonido para siempre.

**Un trap que limpia pero no sale es peor que no tener trap.** Ctrl-C borraba el
directorio temporal y el script seguía corriendo con los archivos ya muertos.

**Las voces de Siri no se pueden usar.** Ni con `say` ni con `AVSpeechSynthesizer`
— 180 voces visibles, cero de Siri. Apple las tiene bajo llave. Por eso Kokoro.

**Un hilo de chat eterno se pudre.** Cada turno reenvía toda la historia. Ahora
rota diario, y lo que vale la pena recordar vive en un archivo de memoria
destilada, no en la transcripción.

## Lo que le falta

- Palabra de activación — decir "E.V." y que despierte sola
- Barge-in por voz en vez de por tecla (necesita cancelación de eco)
- Modo proactivo: que ella te hable a ti
- Acceso desde el celular

## Créditos

Se para sobre hombros ajenos:
[whisper.cpp](https://github.com/ggerganov/whisper.cpp) ·
[Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) ·
[SoX](https://sox.sourceforge.net/) ·
[Claude Code](https://claude.com/claude-code)

Y la idea original es de Peter Parker, técnicamente.

## Licencia

MIT. Haz lo que quieras con esto.
