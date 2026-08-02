// ─────────────────────────────────────────────────────────────
//  E.V. — app de barra de menú
//
//  No reimplementa nada: el motor sigue siendo el script `ev` de bash.
//  Esta app solo lo lanza, lo apaga, y pinta su estado en la barra.
//
//  La comunicación es por archivo (~/ev/.estado) y no por stdout, para que
//  `ev` siga funcionando igual si lo corres a mano desde la terminal.
// ─────────────────────────────────────────────────────────────
import AppKit
import AVFoundation

// MARK: - Estado

enum Estado: String {
    case apagada, dormida, escuchando, pensando, hablando

    var icono: String {
        switch self {
        case .apagada:    return "🌙"
        case .dormida:    return "😴"
        case .escuchando: return "🎙"
        case .pensando:   return "💭"
        case .hablando:   return "🔊"
        }
    }

    var descripcion: String {
        switch self {
        case .apagada:    return "Apagada"
        case .dormida:    return "Dormida — dile «E.V.» o «Ivi»"
        case .escuchando: return "Escuchando…"
        case .pensando:   return "Pensando…"
        case .hablando:   return "Hablando"
        }
    }
}

// MARK: - App

final class EV: NSObject, NSApplicationDelegate {

    private let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private var proceso: Process?
    private var reloj: Timer?

    private var estado: Estado = .apagada
    private var ultimoTexto = ""

    private let casa = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("ev")
    private var archivoEstado: URL { casa.appendingPathComponent(".estado") }

    // Ítems que cambian de texto en vivo
    private let itemEstado = NSMenuItem(title: "", action: nil, keyEquivalent: "")
    private let itemTexto  = NSMenuItem(title: "", action: nil, keyEquivalent: "")
    private let itemToggle = NSMenuItem(title: "Despertar", action: #selector(alternar),
                                        keyEquivalent: "")

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)   // sin ícono en el Dock

        // Pedir el micrófono desde la app y no desde el script: así macOS
        // atribuye el permiso a este bundle, y los procesos hijos (sox) lo
        // heredan. Es justo lo que no se podía hacer con un launchd suelto.
        AVCaptureDevice.requestAccess(for: .audio) { _ in }

        construirMenu()
        pintar()

        reloj = Timer.scheduledTimer(withTimeInterval: 0.4, repeats: true) { [weak self] _ in
            self?.leerEstado()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        apagar()
    }

    // MARK: Menú

    private func construirMenu() {
        let menu = NSMenu()

        itemEstado.isEnabled = false
        itemTexto.isEnabled = false
        itemTexto.isHidden = true

        menu.addItem(itemEstado)
        menu.addItem(itemTexto)
        menu.addItem(.separator())

        itemToggle.target = self
        itemToggle.keyEquivalent = "e"
        menu.addItem(itemToggle)

        let ronda = NSMenuItem(title: "Ronda del vault ahora",
                               action: #selector(correrRonda), keyEquivalent: "r")
        ronda.target = self
        menu.addItem(ronda)

        menu.addItem(.separator())

        let bitacora = NSMenuItem(title: "Abrir bitácora de hoy",
                                  action: #selector(abrirBitacora), keyEquivalent: "b")
        bitacora.target = self
        menu.addItem(bitacora)

        let perfil = NSMenuItem(title: "Abrir su memoria (PERFIL.md)",
                                action: #selector(abrirPerfil), keyEquivalent: "")
        perfil.target = self
        menu.addItem(perfil)

        let personalidad = NSMenuItem(title: "Editar personalidad (EV.md)",
                                      action: #selector(abrirPersonalidad), keyEquivalent: "")
        personalidad.target = self
        menu.addItem(personalidad)

        menu.addItem(.separator())

        let salir = NSMenuItem(title: "Salir de E.V.",
                               action: #selector(salir), keyEquivalent: "q")
        salir.target = self
        menu.addItem(salir)

        item.menu = menu
    }

    private func pintar() {
        item.button?.title = estado.icono
        itemEstado.title = estado.descripcion
        itemToggle.title = (estado == .apagada) ? "Despertar" : "Dormir"

        if ultimoTexto.isEmpty {
            itemTexto.isHidden = true
        } else {
            itemTexto.isHidden = false
            let t = ultimoTexto.count > 60
                ? String(ultimoTexto.prefix(60)) + "…"
                : ultimoTexto
            itemTexto.title = "“\(t)”"
        }
    }

    // MARK: Estado desde el archivo

    private func leerEstado() {
        // Si el proceso murió por su cuenta, reflejarlo.
        if let p = proceso, !p.isRunning {
            proceso = nil
            estado = .apagada
            ultimoTexto = ""
            pintar()
            return
        }
        guard proceso != nil,
              let crudo = try? String(contentsOf: archivoEstado, encoding: .utf8)
        else { return }

        let linea = crudo.trimmingCharacters(in: .whitespacesAndNewlines)
        let partes = linea.split(separator: "|", maxSplits: 1,
                                 omittingEmptySubsequences: false)
        guard let nombre = partes.first,
              let nuevo = Estado(rawValue: String(nombre)) else { return }

        let texto = partes.count > 1 ? String(partes[1]) : ""
        guard nuevo != estado || texto != ultimoTexto else { return }

        estado = nuevo
        // En "dormida" no se arrastra lo último dicho: ensucia el menú.
        ultimoTexto = (nuevo == .dormida || nuevo == .apagada) ? "" : texto
        pintar()
    }

    // MARK: Acciones

    @objc private func alternar() {
        proceso == nil ? encender() : apagar()
    }

    private func encender() {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        // -lc para heredar el PATH del login: whisper-cli y sox viven en brew.
        p.arguments = ["-lc", "exec \"$HOME/ev/ev\" --escucha"]
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        p.standardInput = FileHandle.nullDevice

        do {
            try p.run()
            proceso = p
            estado = .dormida
        } catch {
            alerta("No pude arrancar E.V.", error.localizedDescription)
            estado = .apagada
        }
        pintar()
    }

    private func apagar() {
        guard let p = proceso else { return }
        p.terminate()                    // SIGTERM: el trap de `ev` limpia solo
        proceso = nil
        estado = .apagada
        ultimoTexto = ""
        pintar()
    }

    @objc private func correrRonda() {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = ["-lc", "exec \"$HOME/ev/ronda\""]
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        try? p.run()   // tarda ~1 min y avisa por notificación; no se espera
    }

    @objc private func abrirBitacora() {
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd"
        let hoy = casa.appendingPathComponent("memory/\(f.string(from: Date())).md")
        abrir(hoy, siNoExiste: "Todavía no hay bitácora de hoy.")
    }

    @objc private func abrirPerfil() {
        abrir(casa.appendingPathComponent("memory/PERFIL.md"),
              siNoExiste: "No encuentro PERFIL.md.")
    }

    @objc private func abrirPersonalidad() {
        abrir(casa.appendingPathComponent("EV.md"),
              siNoExiste: "No encuentro EV.md. Copia EV.example.md primero.")
    }

    @objc private func salir() {
        apagar()
        NSApp.terminate(nil)
    }

    // MARK: Utilidades

    private func abrir(_ url: URL, siNoExiste aviso: String) {
        if FileManager.default.fileExists(atPath: url.path) {
            NSWorkspace.shared.open(url)
        } else {
            alerta(aviso, url.path)
        }
    }

    private func alerta(_ titulo: String, _ detalle: String) {
        let a = NSAlert()
        a.messageText = titulo
        a.informativeText = detalle
        a.alertStyle = .warning
        NSApp.activate(ignoringOtherApps: true)
        a.runModal()
    }
}

let app = NSApplication.shared
let delegado = EV()
app.delegate = delegado
app.run()
