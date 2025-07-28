import Foundation
import Combine
import SwiftUI

struct MCPService {
    let name: String
    let port: Int
    let endpoint: String
    var isHealthy: Bool = false
    var lastChecked: Date = Date()
    
    var url: URL {
        URL(string: "http://localhost:\(port)\(endpoint)")!
    }
}

class ServiceMonitor: ObservableObject {
    @Published var services: [MCPService] = [
        MCPService(name: "Service Registry", port: 8080, endpoint: "/health"),
        MCPService(name: "Memory Engine", port: 8081, endpoint: "/health"),
        MCPService(name: "Finder Actions", port: 8082, endpoint: "/health"),
        MCPService(name: "Screen Vision", port: 8083, endpoint: "/health"),
        MCPService(name: "Workflow Orchestrator", port: 8084, endpoint: "/health"),
        MCPService(name: "Whisper Client", port: 8085, endpoint: "/health")
    ]
    
    @Published var overallStatus: SystemStatus = .unknown
    private var cancellables = Set<AnyCancellable>()
    private var healthCheckTimer: Timer?
    
    enum SystemStatus {
        case healthy, degraded, critical, unknown
        
        var color: Color {
            switch self {
            case .healthy: return .green
            case .degraded: return .yellow
            case .critical: return .red
            case .unknown: return .gray
            }
        }
        
        var description: String {
            switch self {
            case .healthy: return "All Systems Operational"
            case .degraded: return "Some Services Down"
            case .critical: return "Critical Issues"
            case .unknown: return "Checking Status..."
            }
        }
    }
    
    func startMonitoring() {
        // Initial health check
        checkAllServices()
        
        // Set up periodic health checks every 30 seconds
        healthCheckTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { _ in
            self.checkAllServices()
        }
    }
    
    func stopMonitoring() {
        healthCheckTimer?.invalidate()
        healthCheckTimer = nil
    }
    
    func checkAllServices() {
        let group = DispatchGroup()
        
        for i in 0..<services.count {
            group.enter()
            checkServiceHealth(at: i) {
                group.leave()
            }
        }
        
        group.notify(queue: .main) {
            self.updateOverallStatus()
        }
    }
    
    private func checkServiceHealth(at index: Int, completion: @escaping () -> Void) {
        let service = services[index]
        
        URLSession.shared.dataTask(with: service.url) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self = self else {
                    completion()
                    return
                }
                
                let isHealthy: Bool
                if let httpResponse = response as? HTTPURLResponse {
                    isHealthy = httpResponse.statusCode == 200
                } else {
                    isHealthy = false
                }
                
                self.services[index].isHealthy = isHealthy
                self.services[index].lastChecked = Date()
                completion()
            }
        }.resume()
    }
    
    private func updateOverallStatus() {
        let healthyCount = services.filter { $0.isHealthy }.count
        let totalCount = services.count
        
        switch healthyCount {
        case totalCount:
            overallStatus = .healthy
        case 0:
            overallStatus = .critical
        default:
            overallStatus = .degraded
        }
    }
    
    func restartAllServices() {
        // This would trigger a script to restart all services
        let script = """
        cd "/Users/mark/Desktop/MCP STUFF/mcp-macos-companion"
        source venv/bin/activate
        python -m src.run_all_services
        """
        
        executeShellScript(script)
    }
    
    private func executeShellScript(_ script: String) {
        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = ["-c", script]
        
        do {
            try task.run()
        } catch {
            print("Failed to execute script: \(error)")
        }
    }
}