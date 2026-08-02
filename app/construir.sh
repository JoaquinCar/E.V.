#!/usr/bin/env bash
# Arma E.V..app sin Xcode: swiftc + un bundle a mano.
# Un .app de verdad (con su bundle id) es lo que hace que macOS le dé el
# permiso de micrófono limpio, en vez de pelearse con TCC.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
APP="${1:-/Applications/E.V..app}"
NOMBRE="E.V."

echo "▸ compilando…"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -O \
  -o "$APP/Contents/MacOS/EV" \
  "$AQUI/EVMenuBar.swift" \
  -framework AppKit -framework AVFoundation

# Íconos opcionales, uno por estado: apagada.png, dormida.png, escuchando.png,
# pensando.png, hablando.png. El estado que no tenga imagen usa su emoji.
for e in apagada dormida escuchando pensando hablando; do
  if [ -f "$AQUI/$e.png" ]; then
    cp "$AQUI/$e.png" "$APP/Contents/Resources/$e.png"
    echo "  ícono: $e"
  fi
done

echo "▸ armando el bundle…"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$NOMBRE</string>
  <key>CFBundleDisplayName</key><string>$NOMBRE</string>
  <key>CFBundleIdentifier</key><string>local.kino.ev</string>
  <key>CFBundleExecutable</key><string>EV</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <!-- Sin ícono en el Dock: vive solo en la barra de menú -->
  <key>LSUIElement</key><true/>
  <key>NSMicrophoneUsageDescription</key>
  <string>E.V. usa el micrófono para escucharte cuando la llamas por su nombre. Todo se procesa en tu Mac.</string>
</dict>
PLIST
printf '</plist>\n' >> "$APP/Contents/Info.plist"

printf 'APPL????' > "$APP/Contents/PkgInfo"

# Firma ad-hoc: sin esto macOS revoca el permiso de micrófono en cada
# recompilación, porque para TCC sería una app distinta cada vez.
echo "▸ firmando (ad-hoc)…"
codesign --force --deep --sign - "$APP" 2>/dev/null \
  && echo "  firmada" || echo "  sin firmar (el permiso puede repreguntarse)"

echo "✓ listo: $APP"
echo "  ábrela con:  open \"$APP\""
