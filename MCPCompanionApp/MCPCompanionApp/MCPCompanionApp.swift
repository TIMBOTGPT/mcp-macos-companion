import SwiftUI
import Foundation
import Combine

@main
struct MCPCompanionApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        Settings {
            PreferencesView()
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem?
    private var popover: NSPopover?
    private var serviceMonitor = ServiceMonitor()
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMenuBar()
        serviceMonitor.startMonitoring()
    }
    
    private func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        
        if let button = statusItem?.button {
            button.image = NSImage(systemSymbolName: "brain.head.profile", accessibilityDescription: "MCP Companion")
            button.action = #selector(togglePopover)
            button.target = self
        }
        
        setupPopover()
    }
    
    private func setupPopover() {
        popover = NSPopover()
        popover?.contentSize = NSSize(width: 400, height: 500)
        popover?.behavior = .transient
        popover?.contentViewController = NSHostingController(rootView: MenuBarContentView(serviceMonitor: serviceMonitor))
    }
    
    @objc private func togglePopover() {
        guard let button = statusItem?.button, let popover = popover else { return }
        
        if popover.isShown {
            popover.performClose(nil)
        } else {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        }
    }
}