// ServicesView.swift
// View for managing and monitoring MCP services

import SwiftUI

struct ServicesView: View {
    @EnvironmentObject var serviceManager: ServiceManager
    
    var body: some View {
        VStack {
            if serviceManager.isLoading {
                ProgressView("Loading services...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if serviceManager.services.isEmpty {
                EmptyStateView()
            } else {
                ServicesListView()
            }
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button("Refresh") {
                    serviceManager.loadServices()
                }
            }
        }
        .alert("Error", isPresented: .constant(serviceManager.errorMessage != nil)) {
            Button("OK") {
                serviceManager.errorMessage = nil
            }
        } message: {
            Text(serviceManager.errorMessage ?? "")
        }
    }
}

struct EmptyStateView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "server.rack")
                .font(.system(size: 60))
                .foregroundColor(.secondary)
            
            Text("No Services Running")
                .font(.title2)
                .fontWeight(.semibold)
            
            Text("Start the MCP services to see them here")
                .foregroundColor(.secondary)
            
            VStack(alignment: .leading, spacing: 8) {
                Text("To start services:")
                    .fontWeight(.medium)
                
                Text("1. Open Terminal")
                Text("2. Navigate to the MCP directory")
                Text("3. Run: ./start_services.sh")
            }
            .padding()
            .background(Color.blue.opacity(0.1))
            .cornerRadius(8)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct ServicesListView: View {
    @EnvironmentObject var serviceManager: ServiceManager
    
    var body: some View {
        ScrollView {
            LazyVGrid(columns: [
                GridItem(.adaptive(minimum: 300))
            ], spacing: 16) {
                ForEach(serviceManager.services) { service in
                    ServiceCard(service: service)
                }
            }
            .padding()
        }
    }
}

struct ServiceCard: View {
    let service: MCPService
    @EnvironmentObject var serviceManager: ServiceManager
    @State private var isExpanded = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Circle()
                    .fill(service.status == "healthy" ? Color.green : Color.red)
                    .frame(width: 12, height: 12)
                
                Text(service.displayName)
                    .font(.headline)
                
                Spacer()
                
                Button(action: {
                    withAnimation(.easeInOut) {
                        isExpanded.toggle()
                    }
                }) {
                    Image(systemName: "chevron.down")
                        .rotationEffect(.degrees(isExpanded ? 180 : 0))
                        .animation(.easeInOut, value: isExpanded)
                }
            }
            
            // Status and basic info
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("Status:")
                        .fontWeight(.medium)
                    Text(service.status.capitalized)
                        .foregroundColor(service.status == "healthy" ? .green : .red)
                }
                
                HStack {
                    Text("Port:")
                        .fontWeight(.medium)
                    Text("\(service.port)")
                        .font(.system(.body, design: .monospaced))
                }
                
                HStack {
                    Text("Capabilities:")
                        .fontWeight(.medium)
                    Text("\(service.capabilities.count)")
                }
            }
            .font(.caption)
            
            // Capabilities tags
            if !service.capabilities.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(service.capabilities, id: \.self) { capability in
                            Text(capability.replacingOccurrences(of: "_", with: " ").capitalized)
                                .font(.caption2)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.blue.opacity(0.2))
                                .cornerRadius(4)
                        }
                    }
                    .padding(.horizontal, 1)
                }
            }
            
            // Expanded details
            if isExpanded {
                Divider()
                
                VStack(alignment: .leading, spacing: 8) {
                    DetailRow(label: "Service ID", value: service.id)
                    DetailRow(label: "Host", value: service.host)
                    DetailRow(label: "Health Endpoint", value: service.healthEndpoint)
                    
                    let lastHeartbeat = Date(timeIntervalSince1970: service.lastHeartbeat)
                    DetailRow(label: "Last Heartbeat", value: RelativeDateTimeFormatter().localizedString(for: lastHeartbeat, relativeTo: Date()))
                    
                    // Service actions
                    HStack(spacing: 12) {
                        Button("Test Health") {
                            testServiceHealth()
                        }
                        .buttonStyle(.bordered)
                        
                        if service.name == "simple_screen_service" {
                            Button("Capture Screenshot") {
                                serviceManager.captureScreenshot()
                            }
                            .buttonStyle(.borderedProminent)
                        }
                        
                        Spacer()
                    }
                }
                .font(.caption)
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(service.status == "healthy" ? Color.green.opacity(0.3) : Color.red.opacity(0.3), lineWidth: 1)
        )
    }
    
    private func testServiceHealth() {
        Task {
            do {
                let url = URL(string: "\(service.baseURL)\(service.healthEndpoint)")!
                let (_, response) = try await URLSession.shared.data(from: url)
                
                if let httpResponse = response as? HTTPURLResponse {
                    print("Health check for \(service.displayName): \(httpResponse.statusCode)")
                }
            } catch {
                print("Health check failed for \(service.displayName): \(error)")
            }
        }
    }
}

struct DetailRow: View {
    let label: String
    let value: String
    
    var body: some View {
        HStack {
            Text(label + ":")
                .fontWeight(.medium)
                .frame(width: 100, alignment: .leading)
            
            Text(value)
                .font(.system(.caption, design: .monospaced))
                .textSelection(.enabled)
                .foregroundColor(.secondary)
            
            Spacer()
        }
    }
}

#Preview {
    ServicesView()
        .environmentObject(ServiceManager())
}
