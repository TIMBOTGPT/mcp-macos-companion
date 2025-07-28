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
    private var floatingVoiceWindow = FloatingVoiceWindow()
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMenuBar()
        serviceMonitor.startMonitoring()
    }
    
    private func setupMenuBar() {
        print("🚀 Setting up menu bar...")
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        
        if statusItem != nil {
            print("✅ Status item created successfully")
        } else {
            print("❌ Failed to create status item")
            return
        }
        
        if let button = statusItem?.button {
            // Try a more visible icon and add debugging
            if let image = NSImage(systemSymbolName: "mic.circle", accessibilityDescription: "MCP Companion") {
                button.image = image
                print("✅ Menu bar icon set successfully")
            } else if let image = NSImage(systemSymbolName: "circle.fill", accessibilityDescription: "MCP Companion") {
                button.image = image
                print("⚠️ Using fallback icon")
            } else {
                // Create a simple text-based menu item
                button.title = "🎤"
                print("⚠️ Using text-based menu item")
            }
            button.action = #selector(togglePopover)
            button.target = self
            print("🎯 Menu bar button configured")
        } else {
            print("❌ Failed to create menu bar button")
        }
        
        setupPopover()
    }
    
    private func setupPopover() {
        popover = NSPopover()
        popover?.contentSize = NSSize(width: 400, height: 500)
        popover?.behavior = .transient
        popover?.contentViewController = NSHostingController(rootView: MenuBarContentView(serviceMonitor: serviceMonitor, floatingVoiceWindow: floatingVoiceWindow))
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