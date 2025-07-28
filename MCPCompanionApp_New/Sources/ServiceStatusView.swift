import SwiftUI

struct ServiceStatusView: View {
    @ObservedObject var serviceMonitor: ServiceMonitor
    
    var body: some View {
        ScrollView {
            LazyVStack(spacing: 8) {
                ForEach(serviceMonitor.services.indices, id: \.self) { index in
                    ServiceRowView(service: serviceMonitor.services[index])
                }
                
                Divider()
                    .padding(.vertical)
                
                // Control buttons
                VStack(spacing: 12) {
                    Button("Restart All Services") {
                        serviceMonitor.restartAllServices()
                    }
                    .buttonStyle(ActionButtonStyle(color: .orange))
                    
                    Button("Open Service Registry") {
                        openURL("http://localhost:8080/services")
                    }
                    .buttonStyle(ActionButtonStyle(color: .blue))
                    
                    Button("View Logs") {
                        openTerminalWithLogs()
                    }
                    .buttonStyle(ActionButtonStyle(color: .gray))
                }
            }
            .padding()
        }
    }
    
    private func openURL(_ urlString: String) {
        if let url = URL(string: urlString) {
            NSWorkspace.shared.open(url)
        }
    }
    
    private func openTerminalWithLogs() {
        let script = """
        tell application "Terminal"
            activate
            do script "cd '/Users/mark/Desktop/MCP STUFF/mcp-macos-companion' && tail -f logs/*.log"
        end tell
        """
        
        if let scriptObject = NSAppleScript(source: script) {
            scriptObject.executeAndReturnError(nil)
        }
    }
}

struct ServiceRowView: View {
    let service: MCPService
    
    var body: some View {
        HStack {
            Circle()
                .fill(service.isHealthy ? Color.green : Color.red)
                .frame(width: 8, height: 8)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(service.name)
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                Text("Port \(service.port)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 2) {
                Text(service.isHealthy ? "Online" : "Offline")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(service.isHealthy ? .green : .red)
                
                Text(RelativeDateTimeFormatter().localizedString(for: service.lastChecked, relativeTo: Date()))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.secondary.opacity(0.1))
        .cornerRadius(8)
    }
}

struct ActionButtonStyle: ButtonStyle {
    let color: Color
    
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(.white)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(color.opacity(configuration.isPressed ? 0.8 : 1.0))
            .cornerRadius(6)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
    }
}