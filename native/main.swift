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
    var lang: String = {
        if let s = UserDefaults.standard.string(forKey: "lang"), s == "de" || s == "en" { return s }
        return (Locale.preferredLanguages.first ?? "en").lowercased().hasPrefix("de") ? "de" : "en"
    }()
    func t(_ de: String, _ en: String) -> String { lang == "en" ? en : de }

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
            fail(t("Bitte in „Programme“ verschieben", "Please move to Applications"), t("Ziehe Brennweiten in den Ordner Programme und starte es dort erneut.", "Drag Brennweiten to the Applications folder and open it from there."))
            return false
        }
        guard FileManager.default.isExecutableFile(atPath: pythonPath) else {
            fail(t("App unvollständig", "App incomplete"), t("Der eingebaute Programmteil wurde nicht gefunden. Bitte Brennweiten neu installieren.", "A bundled component was not found. Please reinstall Brennweiten."))
            return false
        }
        guard FileManager.default.isExecutableFile(atPath: "/usr/bin/perl") else {
            fail(t("Perl fehlt", "Perl is missing"), t("Das Auslesen der Fotos braucht das in macOS enthaltene Perl.", "Reading photos requires the Perl included with macOS."))
            return false
        }
        if !notarized && getxattr(pythonPath, "com.apple.quarantine", nil, 0, 0, 0) >= 0 {
            let a = NSAlert()
            a.messageText = t("Eingebaute Programmteile freigeben?", "Allow bundled components?")
            a.informativeText = t("Brennweiten enthält Python und ExifTool. Die Freigabe gilt nur für diese App. Deine Fotos werden nur gelesen.", "Brennweiten includes Python and ExifTool. This permission applies to this app only. Your photos are only read.")
            a.addButton(withTitle: t("Freigeben", "Allow"))
            a.addButton(withTitle: t("Abbrechen", "Cancel"))
            guard a.runModal() == .alertFirstButtonReturn else { return false }
            let p = Process()
            p.executableURL = URL(fileURLWithPath: "/usr/bin/xattr")
            p.arguments = ["-dr", "com.apple.quarantine", path]
            try? p.run()
            p.waitUntilExit()
            if p.terminationStatus != 0 {
                fail(t("Freigabe fehlgeschlagen", "Permission failed"), t("Ziehe Brennweiten in den Ordner Programme und starte es dort erneut.", "Drag Brennweiten to the Applications folder and open it from there."))
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
                self.fail(self.t("Brennweiten wurde unerwartet beendet", "Brennweiten quit unexpectedly"), self.t("Details stehen in \(logURL.path).", "Details are in \(logURL.path)."))
                self.quitting = true
                NSApp.terminate(nil)
            }
        }
        do {
            try p.run()
            server = p
        } catch {
            fail(t("Brennweiten startet nicht", "Brennweiten cannot start"), error.localizedDescription)
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
        cfg.userContentController.addUserScript(WKUserScript(source: "window.BW_NATIVE_LANG='\(lang)';", injectionTime: .atDocumentStart, forMainFrameOnly: true))
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
        let hide = item(t("Andere ausblenden", "Hide Others"), #selector(NSApplication.hideOtherApplications(_:)), "h")
        hide.keyEquivalentModifierMask = [.command, .option]
        _ = add("Brennweiten", [
            item(t("Über Brennweiten", "About Brennweiten"), #selector(NSApplication.orderFrontStandardAboutPanel(_:))), .separator(),
            item(t("Brennweiten ausblenden", "Hide Brennweiten"), #selector(NSApplication.hide(_:)), "h"), hide, .separator(),
            item(t("Brennweiten beenden", "Quit Brennweiten"), #selector(NSApplication.terminate(_:)), "q")])
        let redo = item(t("Wiederholen", "Redo"), Selector(("redo:")), "z")
        redo.keyEquivalentModifierMask = [.command, .shift]
        _ = add(t("Bearbeiten", "Edit"), [
            item(t("Widerrufen", "Undo"), Selector(("undo:")), "z"), redo, .separator(),
            item(t("Ausschneiden", "Cut"), #selector(NSText.cut(_:)), "x"), item(t("Kopieren", "Copy"), #selector(NSText.copy(_:)), "c"),
            item(t("Einsetzen", "Paste"), #selector(NSText.paste(_:)), "v"), item(t("Alles auswählen", "Select All"), #selector(NSText.selectAll(_:)), "a")])
        let tabs = lang == "en" ? ["Overview", "Lenses", "Cameras", "Shooting Days", "Table", "Check a Lens", "Compare", "Manage Cameras & Lenses", "Data Quality"]
            : ["Übersicht", "Objektive", "Kameras", "Fototage", "Tabelle", "Objektiv prüfen", "Vergleich", "Kameras & Objektive verwalten", "Datenqualität"]
        _ = add(t("Ansicht", "View"), tabs.enumerated().map { i, t in item(t, #selector(showSection(_:)), String(i + 1), target: self, tag: i) })
        let win = add(t("Fenster", "Window"), [
            item(t("Im Dock ablegen", "Minimize"), #selector(NSWindow.performMiniaturize(_:)), "m"),
            item(t("Zoomen", "Zoom"), #selector(NSWindow.performZoom(_:))),
            item(t("Schließen", "Close"), #selector(NSWindow.performClose(_:)), "w")])
        NSApp.windowsMenu = win
        let help = add(t("Hilfe", "Help"), [
            item(t("Anleitung", "Guide"), #selector(openGuide), target: self),
            item(t("Datenordner im Finder zeigen", "Show Data Folder in Finder"), #selector(openData), target: self),
            item(t("Lizenzen", "Licenses"), #selector(openLicenses), target: self)])
        NSApp.helpMenu = help
        NSApp.mainMenu = bar
    }

    @objc func showSection(_ s: NSMenuItem) {
        let ids = ["auswertung", "objektiv", "kamera", "fototage", "tabelle", "pruefen", "vergleich", "stamm", "qualitaet"]
        web.evaluateJavaScript("document.body.classList.contains('first') || showTab('\(ids[s.tag])')", completionHandler: nil)
    }
    @objc func openGuide() { NSWorkspace.shared.open(res.appendingPathComponent(lang == "en" ? "Guide.txt" : "Anleitung.txt")) }
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
            p.prompt = t("Auswählen", "Choose")
            p.message = t("Fotoordner auswählen (mehrere mit ⌘-Klick)", "Choose photo folders (⌘-click for several)")
            p.beginSheetModal(for: window) { r in
                replyHandler(r == .OK ? p.urls.map { $0.path } : [String](), nil)
            }
        case "lang":
            if let l = b["lang"] as? String, l == "de" || l == "en" {
                if (b["save"] as? Bool) != false { UserDefaults.standard.set(l, forKey: "lang") }
                if l != lang { lang = l; buildMenu() }
            }
            replyHandler(true, nil)
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
        a.addButton(withTitle: t("Abbrechen", "Cancel"))
        a.beginSheetModal(for: window) { completionHandler($0 == .alertFirstButtonReturn) }
    }

    func webView(_ w: WKWebView, runJavaScriptTextInputPanelWithPrompt m: String, defaultText t: String?,
                 initiatedByFrame f: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        let a = NSAlert()
        a.messageText = m
        a.addButton(withTitle: "OK")
        a.addButton(withTitle: self.t("Abbrechen", "Cancel"))
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
