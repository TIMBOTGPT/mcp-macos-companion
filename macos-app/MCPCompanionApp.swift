// MCP macOS Companion - Main App
// A native SwiftUI app for controlling the MCP services

import SwiftUI
import Combine

@main
struct MCPCompanionApp: App {
    @StateObject private var serviceManager = ServiceManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(serviceManager)
                .frame(minWidth: 800, minHeight: 600)
        }
        .windowResizability(.contentSize)
        
        // Menu bar extras for macOS
        MenuBarExtra("MCP", systemImage: "gearshape.2") {
            MenuBarView()
                .environmentObject(serviceManager)
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var serviceManager: ServiceManager
    @State private var selectedTab = "services"
    
    var body: some View {
        NavigationSplitView {
            // Sidebar
            List(selection: $selectedTab) {
                Section("MCP Companion") {
                    NavigationLink(value: "services") {
                        Label("Services", systemImage: "server.rack")
                    }
                    
                    NavigationLink(value: "workflows") {
                        Label("Workflows", systemImage: "arrow.triangle.branch")
                    }
                    
                    NavigationLink(value: "memory") {
                        Label("Memory", systemImage: "brain.head.profile")
                    }
                    
                    NavigationLink(value: "screenshots") {
                        Label("Screenshots", systemImage: "camera.viewfinder")
                    }
                }
                
                Section("Tools") {
                    NavigationLink(value: "logs") {
                        Label("Logs", systemImage: "list.bullet.rectangle")
                    }
                    
                    NavigationLink(value: "settings") {
                        Label("Settings", systemImage: "gear")
                    }
                }
            }
            .navigationSplitViewColumnWidth(ideal: 200)
        } detail: {
            // Main content
            Group {
                switch selectedTab {
                case "services":
                    ServicesView()
                case "workflows":
                    WorkflowsView()
                case "memory":
                    MemoryView()
                case "screenshots":
                    ScreenshotsView()
                case "logs":
                    LogsView()
                case "settings":
                    SettingsView()
                default:
                    ServicesView()
                }
            }
            .navigationTitle(titleForTab(selectedTab))
        }
        .onAppear {
            serviceManager.startMonitoring()
        }
    }
    
    private func titleForTab(_ tab: String) -> String {
        switch tab {
        case "services": return "Services"
        case "workflows": return "Workflows"
        case "memory": return "Memory"
        case "screenshots": return "Screenshots"
        case "logs": return "Logs"
        case "settings": return "Settings"
        default: return "MCP Companion"
        }
    }
}

struct MenuBarView: View {
    @EnvironmentObject var serviceManager: ServiceManager
    
    var body: some View {
        VStack {
            Text("MCP Services")
                .font(.headline)
            
            Divider()
            
            ForEach(serviceManager.services) { service in
                HStack {
                    Circle()
                        .fill(service.status == "healthy" ? Color.green : Color.red)
                        .frame(width: 8, height: 8)
                    
                    Text(service.displayName)
                        .font(.caption)
                    
                    Spacer()
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 2)
            }
            
            if serviceManager.services.isEmpty {
                Text("No services running")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Divider()
            
            Button("Quick Screenshot") {
                serviceManager.captureScreenshot()
            }
            
            Button("Open Main Window") {
                // This would bring the main window to front
                NSApp.activate(ignoringOtherApps: true)
            }
            
            Divider()
            
            Button("Quit") {
                NSApplication.shared.terminate(nil)
            }
        }
        .padding(8)
        .frame(width: 200)
    }
}

#Preview {
    ContentView()
        .environmentObject(ServiceManager())
}
