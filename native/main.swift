// Eigenes App-Fenster: startet den lokalen Python-Teil und zeigt die Oberfläche in einer WebView.
import Cocoa
import WebKit

final class App: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate, WKScriptMessageHandlerWithReply {
    var window: NSWindow!
    var web: WKWebView!
    var server: Process?
    var loaded = false
    var quitting = false
    var buffer = Data()
    var targets: [ObjectIdentifier: URL] = [:]
    let res = Bundle.main.resourceURL!

    lazy var dataDir: URL = {
        if let d = ProcessInfo.processInfo.environment["BRENNWEITEN_DATA"] { return URL(fileURLWithPath: d) }
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("Brennweiten")
    }()

    var pythonPath: String {
        #if arch(arm64)
        return res.appendingPathComponent("runtime/python-arm64/bin/python3").path
        #else
        return res.appendingPathComponent("runtime/python-x86_64/bin/python3").path
        #endif
    }

    func applicationDidFinishLaunching(_ note: Notification) {
        let me = NSRunningApplication.current
        if let id = Bundle.main.bundleIdentifier,
           let other = NSRunningApplication.runningApplications(withBundleIdentifier: id).first(where: { $0 != me }) {
            other.activate(options: [])
            NSApp.terminate(nil)
            return
        }
        buildMenu()
        buildWindow()
        guard prepare() else { quitting = true; NSApp.terminate(nil); return }
        startServer()
    }

    // MARK: Vorbereitung

    func fail(_ title: String, _ text: String) {
        let a = NSAlert()
        a.messageText = title
        a.informativeText = text
        a.alertStyle = .warning
        a.runModal()
    }

    func prepare() -> Bool {
        let path = Bundle.main.bundlePath
        let notarized = Bundle.main.object(forInfoDictionaryKey: "BWNotarized") as? Bool ?? false
        if !notarized && (path.contains("/AppTranslocation/") || !FileManager.default.isWritableFile(atPath: path)) {
            fail("Bitte in „Programme“ verschieben", "Ziehe Brennweiten in den Ordner Programme und starte es dort erneut.")
            return false
        }
        guard FileManager.default.isExecutableFile(atPath: pythonPath) else {
            fail("App unvollständig", "Der eingebaute Programmteil wurde nicht gefunden. Bitte Brennweiten neu installieren.")
            return false
        }
        guard FileManager.default.isExecutableFile(atPath: "/usr/bin/perl") else {
            fail("Perl fehlt", "Das Auslesen der Fotos braucht das in macOS enthaltene Perl.")
            return false
        }
        if !notarized && getxattr(pythonPath, "com.apple.quarantine", nil, 0, 0, 0) >= 0 {
            let a = NSAlert()
            a.messageText = "Eingebaute Programmteile freigeben?"
            a.informativeText = "Brennweiten enthält Python und ExifTool. Die Freigabe gilt nur für diese App. Deine Fotos werden nur gelesen."
            a.addButton(withTitle: "Freigeben")
            a.addButton(withTitle: "Abbrechen")
            guard a.runModal() == .alertFirstButtonReturn else { return false }
            let p = Process()
            p.executableURL = URL(fileURLWithPath: "/usr/bin/xattr")
            p.arguments = ["-dr", "com.apple.quarantine", path]
            try? p.run()
            p.waitUntilExit()
            if p.terminationStatus != 0 {
                fail("Freigabe fehlgeschlagen", "Ziehe Brennweiten in den Ordner Programme und starte es dort erneut.")
                return false
            }
        }
        return true
    }

    func startServer() {
        try? FileManager.default.createDirectory(at: dataDir, withIntermediateDirectories: true)
        let logURL = dataDir.appendingPathComponent("protokoll.txt")
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: pythonPath)
        p.arguments = [res.appendingPathComponent("app/server.py").path]
        p.currentDirectoryURL = dataDir
        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
        env["BRENNWEITEN_DATA"] = dataDir.path
        env["BRENNWEITEN_EXIFTOOL"] = res.appendingPathComponent("runtime/exiftool/exiftool-start").path
        env["BRENNWEITEN_PORT"] = "auto"
        env["BRENNWEITEN_PARENT"] = String(ProcessInfo.processInfo.processIdentifier)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p.environment = env
        let out = Pipe()
        p.standardOutput = out
        if let log = try? FileHandle(forWritingTo: logURL) {
            log.seekToEndOfFile()
            p.standardError = log
        }
        out.fileHandleForReading.readabilityHandler = { [weak self] h in
            let d = h.availableData
            if d.isEmpty { h.readabilityHandler = nil; return }
            DispatchQueue.main.async { self?.received(d) }
        }
        p.terminationHandler = { [weak self] _ in
            DispatchQueue.main.async {
                guard let self = self, !self.quitting else { return }
                self.fail("Brennweiten wurde unerwartet beendet", "Details stehen in \(logURL.path).")
                self.quitting = true
                NSApp.terminate(nil)
            }
        }
        do {
            try p.run()
            server = p
        } catch {
            fail("Brennweiten startet nicht", error.localizedDescription)
            quitting = true
            NSApp.terminate(nil)
        }
    }

    func received(_ d: Data) {
        guard !loaded else { return }
        buffer.append(d)
        let text = String(decoding: buffer, as: UTF8.self)
        guard let r = text.range(of: #"PORT=\d+"#, options: .regularExpression),
              let port = Int(text[r].dropFirst(5)),
              let url = URL(string: "http://127.0.0.1:\(port)/") else { return }
        loaded = true
        web.load(URLRequest(url: url))
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { true }

    func applicationWillTerminate(_ note: Notification) {
        quitting = true
        guard let p = server, p.isRunning else { return }
        p.terminate()
        let end = Date().addingTimeInterval(2)
        while p.isRunning && Date() < end { usleep(50_000) }
        if p.isRunning { kill(p.processIdentifier, SIGKILL) }
    }

    // MARK: Fenster und Menü

    func buildWindow() {
        let cfg = WKWebViewConfiguration()
        cfg.userContentController.addScriptMessageHandler(self, contentWorld: .page, name: "native")
        web = WKWebView(frame: .zero, configuration: cfg)
        web.navigationDelegate = self
        web.uiDelegate = self
        web.setValue(false, forKey: "drawsBackground")
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1320, height: 860),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Brennweiten"
        window.minSize = NSSize(width: 900, height: 600)
        window.contentView = web
        window.center()
        window.setFrameAutosaveName("Hauptfenster")
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func item(_ title: String, _ action: Selector?, _ key: String = "", target: AnyObject? = nil, tag: Int = 0) -> NSMenuItem {
        let m = NSMenuItem(title: title, action: action, keyEquivalent: key)
        m.target = target
        m.tag = tag
        return m
    }

    func buildMenu() {
        let bar = NSMenu()
        func add(_ title: String, _ items: [NSMenuItem]) -> NSMenu {
            let top = NSMenuItem()
            let menu = NSMenu(title: title)
            items.forEach { menu.addItem($0) }
            top.submenu = menu
            bar.addItem(top)
            return menu
        }
        let hide = item("Andere ausblenden", #selector(NSApplication.hideOtherApplications(_:)), "h")
        hide.keyEquivalentModifierMask = [.command, .option]
        _ = add("Brennweiten", [
            item("Über Brennweiten", #selector(NSApplication.orderFrontStandardAboutPanel(_:))), .separator(),
            item("Brennweiten ausblenden", #selector(NSApplication.hide(_:)), "h"), hide, .separator(),
            item("Brennweiten beenden", #selector(NSApplication.terminate(_:)), "q")])
        let redo = item("Wiederholen", Selector(("redo:")), "z")
        redo.keyEquivalentModifierMask = [.command, .shift]
        _ = add("Bearbeiten", [
            item("Widerrufen", Selector(("undo:")), "z"), redo, .separator(),
            item("Ausschneiden", #selector(NSText.cut(_:)), "x"), item("Kopieren", #selector(NSText.copy(_:)), "c"),
            item("Einsetzen", #selector(NSText.paste(_:)), "v"), item("Alles auswählen", #selector(NSText.selectAll(_:)), "a")])
        let tabs = ["Übersicht", "Objektive", "Kameras", "Fototage", "Tabelle", "Objektiv prüfen", "Vergleich", "Kameras & Objektive verwalten", "Datenqualität"]
        _ = add("Ansicht", tabs.enumerated().map { i, t in item(t, #selector(showSection(_:)), String(i + 1), target: self, tag: i) })
        let win = add("Fenster", [
            item("Im Dock ablegen", #selector(NSWindow.performMiniaturize(_:)), "m"),
            item("Zoomen", #selector(NSWindow.performZoom(_:))),
            item("Schließen", #selector(NSWindow.performClose(_:)), "w")])
        NSApp.windowsMenu = win
        let help = add("Hilfe", [
            item("Anleitung", #selector(openGuide), target: self),
            item("Datenordner im Finder zeigen", #selector(openData), target: self),
            item("Lizenzen", #selector(openLicenses), target: self)])
        NSApp.helpMenu = help
        NSApp.mainMenu = bar
    }

    @objc func showSection(_ s: NSMenuItem) {
        let ids = ["auswertung", "objektiv", "kamera", "fototage", "tabelle", "pruefen", "vergleich", "stamm", "qualitaet"]
        web.evaluateJavaScript("document.body.classList.contains('first') || showTab('\(ids[s.tag])')", completionHandler: nil)
    }
    @objc func openGuide() { NSWorkspace.shared.open(res.appendingPathComponent("Anleitung.txt")) }
    @objc func openLicenses() { NSWorkspace.shared.open(res.appendingPathComponent("runtime/LIZENZEN.txt")) }
    @objc func openData() { NSWorkspace.shared.activateFileViewerSelecting([dataDir]) }

    // MARK: Brücke zur Oberfläche

    func userContentController(_ c: WKUserContentController, didReceive message: WKScriptMessage,
                               replyHandler: @escaping (Any?, String?) -> Void) {
        guard message.frameInfo.securityOrigin.host == "127.0.0.1", let b = message.body as? [String: Any],
              let cmd = b["cmd"] as? String else { return replyHandler(nil, "ungültig") }
        switch cmd {
        case "chooseFolders":
            let p = NSOpenPanel()
            p.canChooseDirectories = true
            p.canChooseFiles = false
            p.allowsMultipleSelection = true
            p.prompt = "Auswählen"
            p.message = "Fotoordner auswählen (mehrere mit ⌘-Klick)"
            p.beginSheetModal(for: window) { r in
                replyHandler(r == .OK ? p.urls.map { $0.path } : [String](), nil)
            }
        case "copy":
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(b["text"] as? String ?? "", forType: .string)
            replyHandler(true, nil)
        default:
            replyHandler(nil, "unbekannt")
        }
    }

    // MARK: Navigation und Downloads

    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(a.request.url?.host == "127.0.0.1" || a.request.url?.scheme == "about" ? .allow : .cancel)
    }

    func webView(_ w: WKWebView, decidePolicyFor r: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        let head = (r.response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition") ?? ""
        decisionHandler(head.contains("attachment") ? .download : .allow)
    }

    func webView(_ w: WKWebView, navigationResponse r: WKNavigationResponse, didBecome d: WKDownload) { d.delegate = self }
    func webView(_ w: WKWebView, navigationAction a: WKNavigationAction, didBecome d: WKDownload) { d.delegate = self }

    func download(_ d: WKDownload, decideDestinationUsing r: URLResponse, suggestedFilename name: String,
                  completionHandler: @escaping (URL?) -> Void) {
        let p = NSSavePanel()
        p.nameFieldStringValue = name
        p.beginSheetModal(for: window) { [weak self] res in
            guard res == .OK, let u = p.url else { return completionHandler(nil) }
            try? FileManager.default.removeItem(at: u)   // Ersetzen wurde im Dialog bestätigt
            self?.targets[ObjectIdentifier(d)] = u
            completionHandler(u)
        }
    }

    func downloadDidFinish(_ d: WKDownload) {
        targets[ObjectIdentifier(d)] = nil
        web.evaluateJavaScript("toast('Datei gespeichert')", completionHandler: nil)
    }

    func download(_ d: WKDownload, didFailWithError e: Error, resumeData: Data?) {
        targets[ObjectIdentifier(d)] = nil
        web.evaluateJavaScript("toast('Speichern fehlgeschlagen')", completionHandler: nil)
    }

    // MARK: Dialoge

    func webView(_ w: WKWebView, runJavaScriptAlertPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo,
                 completionHandler: @escaping () -> Void) {
        let a = NSAlert()
        a.messageText = m
        a.beginSheetModal(for: window) { _ in completionHandler() }
    }

    func webView(_ w: WKWebView, runJavaScriptConfirmPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo,
                 completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert()
        a.messageText = m
        a.addButton(withTitle: "OK")
        a.addButton(withTitle: "Abbrechen")
        a.beginSheetModal(for: window) { completionHandler($0 == .alertFirstButtonReturn) }
    }

    func webView(_ w: WKWebView, runJavaScriptTextInputPanelWithPrompt m: String, defaultText t: String?,
                 initiatedByFrame f: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        let a = NSAlert()
        a.messageText = m
        a.addButton(withTitle: "OK")
        a.addButton(withTitle: "Abbrechen")
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 280, height: 24))
        field.stringValue = t ?? ""
        a.accessoryView = field
        a.window.initialFirstResponder = field
        a.beginSheetModal(for: window) { completionHandler($0 == .alertFirstButtonReturn ? field.stringValue : nil) }
    }
}

let application = NSApplication.shared
let delegate = App()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()
