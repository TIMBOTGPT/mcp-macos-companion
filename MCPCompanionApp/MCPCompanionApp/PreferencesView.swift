import SwiftUI

struct PreferencesView: View {
    @State private var autoStartServices = true
    @State private var enableNotifications = true
    @State private var healthCheckInterval = 30.0
    @State private var logLevel = "INFO"
    
    private let logLevels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    
    var body: some View {
        TabView {
            GeneralPreferencesView(
                autoStartServices: $autoStartServices,
                enableNotifications: $enableNotifications
            )
            .tabItem {
                Image(systemName: "gear")
                Text("General")
            }
            
            ServicesPreferencesView(
                healthCheckInterval: $healthCheckInterval,
                logLevel: $logLevel,
                logLevels: logLevels
            )
            .tabItem {
                Image(systemName: "server.rack")
                Text("Services")
            }
            
            AboutPreferencesView()
                .tabItem {
                    Image(systemName: "info.circle")
                    Text("About")
                }
        }
        .frame(width: 500, height: 400)
    }
}

struct GeneralPreferencesView: View {
    @Binding var autoStartServices: Bool
    @Binding var enableNotifications: Bool
    
    var body: some View {
        Form {
            Section("Startup") {
                Toggle("Auto-start services on launch", isOn: $autoStartServices)
                Text("Automatically start all MCP services when the app launches")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Section("Notifications") {
                Toggle("Enable notifications", isOn: $enableNotifications)
                Text("Show system notifications for workflow completions and service status changes")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Section("Menu Bar") {
                Button("Launch at Login") {
                    toggleLaunchAtLogin()
                }
                .buttonStyle(ActionButtonStyle(color: .blue))
                
                Text("Add MCP Companion to your login items")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding()
    }
    
    private func toggleLaunchAtLogin() {
        let script = """
        tell application "System Events"
            make login item at end with properties {path:"/Applications/MCP Companion.app", hidden:false}
        end tell
        """
        
        if let scriptObject = NSAppleScript(source: script) {
            scriptObject.executeAndReturnError(nil)
        }
    }
}

struct ServicesPreferencesView: View {
    @Binding var healthCheckInterval: Double
    @Binding var logLevel: String
    let logLevels: [String]
    
    var body: some View {
        Form {
            Section("Health Monitoring") {
                VStack(alignment: .leading) {
                    Text("Health check interval: \(Int(healthCheckInterval)) seconds")
                    Slider(value: $healthCheckInterval, in: 10...300, step: 10)
                }
                
                Text("How often to check if services are running properly")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Section("Logging") {
                Picker("Log Level", selection: $logLevel) {
                    ForEach(logLevels, id: \.self) { level in
                        Text(level).tag(level)
                    }
                }
                .pickerStyle(MenuPickerStyle())
                
                Text("Controls how much detail is logged by the services")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Section("Service Locations") {
                VStack(alignment: .leading, spacing: 8) {
                    ServiceLocationRow(name: "Service Registry", port: 8080)
                    ServiceLocationRow(name: "Memory Engine", port: 8081)
                    ServiceLocationRow(name: "Finder Actions", port: 8082)
                    ServiceLocationRow(name: "Screen Vision", port: 8083)
                    ServiceLocationRow(name: "Workflow Orchestrator", port: 8084)
                    ServiceLocationRow(name: "Whisper Client", port: 8085)
                }
            }
        }
        .padding()
    }
}

struct ServiceLocationRow: View {
    let name: String
    let port: Int
    
    var body: some View {
        HStack {
            Text(name)
                .font(.caption)
            Spacer()
            Text("localhost:\(port)")
                .font(.caption)
                .foregroundColor(.secondary)
                .textSelection(.enabled)
        }
    }
}

struct AboutPreferencesView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "brain.head.profile")
                .font(.system(size: 64))
                .foregroundColor(.blue)
            
            Text("MCP macOS Companion")
                .font(.title)
                .fontWeight(.bold)
            
            Text("Version 1.0.0")
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            Text("An intelligent automation system for macOS that provides screen monitoring, file organization, memory storage, and workflow orchestration capabilities.")
                .multilineTextAlignment(.center)
                .padding()
            
            VStack(spacing: 8) {
                Button("Visit Project on GitHub") {
                    if let url = URL(string: "https://github.com/your-username/mcp-macos-companion") {
                        NSWorkspace.shared.open(url)
                    }
                }
                .buttonStyle(ActionButtonStyle(color: .blue))
                
                Button("View Documentation") {
                    if let url = URL(string: "https://docs.mcp-companion.dev") {
                        NSWorkspace.shared.open(url)
                    }
                }
                .buttonStyle(ActionButtonStyle(color: .green))
            }
            
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}