import SwiftUI

struct MenuBarContentView: View {
    @ObservedObject var serviceMonitor: ServiceMonitor
    @ObservedObject var floatingVoiceWindow: FloatingVoiceWindow
    @State private var selectedTab = 0
    
    var body: some View {
        VStack(spacing: 0) {
            // Header with status
            HeaderView(serviceMonitor: serviceMonitor)
            
            // Tab picker
            Picker("", selection: $selectedTab) {
                Text("Status").tag(0)
                Text("Actions").tag(1)
                Text("Workflows").tag(2)
            }
            .pickerStyle(SegmentedPickerStyle())
            .padding(.horizontal)
            
            // Content based on selected tab
            TabView(selection: $selectedTab) {
                ServiceStatusView(serviceMonitor: serviceMonitor)
                    .tag(0)
                
                QuickActionsView(serviceMonitor: serviceMonitor, floatingVoiceWindow: floatingVoiceWindow)
                    .tag(1)
                
                WorkflowsView(serviceMonitor: serviceMonitor)
                    .tag(2)
            }
        }
        .frame(width: 400, height: 500)
    }
}

struct HeaderView: View {
    @ObservedObject var serviceMonitor: ServiceMonitor
    
    var body: some View {
        HStack {
            Circle()
                .fill(serviceMonitor.overallStatus.color)
                .frame(width: 12, height: 12)
            
            VStack(alignment: .leading, spacing: 2) {
                Text("MCP Companion")
                    .font(.headline)
                
                Text(serviceMonitor.overallStatus.description)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            Button(action: {
                serviceMonitor.checkAllServices()
            }) {
                Image(systemName: "arrow.clockwise")
            }
            .buttonStyle(PlainButtonStyle())
        }
        .padding()
        .background(Color.secondary.opacity(0.1))
    }
}