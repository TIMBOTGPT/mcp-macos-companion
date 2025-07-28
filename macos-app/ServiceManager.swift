// ServiceManager.swift
// Manages communication with MCP services

import Foundation
import Combine

struct MCPService: Identifiable, Codable {
    let id: String
    let name: String
    let host: String
    let port: Int
    let status: String
    let capabilities: [String]
    let healthEndpoint: String
    let lastHeartbeat: Double
    let metadata: [String: AnyCodable]
    
    var displayName: String {
        switch name {
        case "simple_test_service": return "Test Service"
        case "simple_screen_service": return "Screen Capture"
        case "simple_workflow_service": return "Workflows"
        case "simple_memory_service": return "Memory"
        default: return name.capitalized
        }
    }
    
    var baseURL: String {
        return "http://\(host):\(port)"
    }
    
    enum CodingKeys: String, CodingKey {
        case id = "service_id"
        case name, host, port, status, capabilities
        case healthEndpoint = "health_endpoint"
        case lastHeartbeat = "last_heartbeat"
        case metadata
    }
}

struct AnyCodable: Codable {
    let value: Any
    
    init(_ value: Any) {
        self.value = value
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        
        if let intValue = try? container.decode(Int.self) {
            value = intValue
        } else if let doubleValue = try? container.decode(Double.self) {
            value = doubleValue
        } else if let stringValue = try? container.decode(String.self) {
            value = stringValue
        } else if let boolValue = try? container.decode(Bool.self) {
            value = boolValue
        } else {
            value = try container.decode([String: AnyCodable].self)
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        
        if let intValue = value as? Int {
            try container.encode(intValue)
        } else if let doubleValue = value as? Double {
            try container.encode(doubleValue)
        } else if let stringValue = value as? String {
            try container.encode(stringValue)
        } else if let boolValue = value as? Bool {
            try container.encode(boolValue)
        } else if let dictValue = value as? [String: AnyCodable] {
            try container.encode(dictValue)
        }
    }
}

struct WorkflowExecution: Identifiable, Codable {
    let id: String
    let workflowName: String
    let status: String
    let startedAt: Double
    let completedAt: Double?
    let duration: Double?
    let stepsResults: [WorkflowStep]
    
    enum CodingKeys: String, CodingKey {
        case id = "execution_id"
        case workflowName = "workflow_name"
        case status
        case startedAt = "started_at"
        case completedAt = "completed_at"
        case duration
        case stepsResults = "steps_results"
    }
}

struct WorkflowStep: Codable {
    let stepNumber: Int
    let action: String
    let success: Bool
    
    enum CodingKeys: String, CodingKey {
        case stepNumber = "step_number"
        case action, success
    }
}

struct Screenshot: Identifiable, Codable {
    let id = UUID()
    let timestamp: Double
    let screenshotPath: String
    let fileSize: Int
    let timeAgo: Double
    
    enum CodingKeys: String, CodingKey {
        case timestamp
        case screenshotPath = "screenshot_path"
        case fileSize = "file_size"
        case timeAgo = "time_ago"
    }
    
    var fileName: String {
        URL(fileURLWithPath: screenshotPath).lastPathComponent
    }
    
    var formattedDate: String {
        let date = Date(timeIntervalSince1970: timestamp)
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
    
    var formattedSize: String {
        let kb = Double(fileSize) / 1024
        if kb < 1024 {
            return String(format: "%.1f KB", kb)
        } else {
            let mb = kb / 1024
            return String(format: "%.1f MB", mb)
        }
    }
}

struct MemoryEntry: Identifiable, Codable {
    let id: String
    let content: String
    let category: String
    let timestamp: Double
    let tags: [String]
    let metadata: [String: AnyCodable]
    
    var formattedDate: String {
        let date = Date(timeIntervalSince1970: timestamp)
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

@MainActor
class ServiceManager: ObservableObject {
    @Published var services: [MCPService] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var lastUpdate = Date()
    
    private var cancellables = Set<AnyCancellable>()
    private let registryURL = "http://localhost:8080"
    
    private var monitoringTimer: Timer?
    
    func startMonitoring() {
        loadServices()
        
        // Start periodic updates
        monitoringTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { _ in
            Task {
                await self.loadServices()
            }
        }
    }
    
    func stopMonitoring() {
        monitoringTimer?.invalidate()
        monitoringTimer = nil
    }
    
    func loadServices() async {
        isLoading = true
        errorMessage = nil
        
        do {
            let url = URL(string: "\(registryURL)/services")!
            let (data, _) = try await URLSession.shared.data(from: url)
            
            let servicesDict = try JSONDecoder().decode([String: MCPService].self, from: data)
            
            await MainActor.run {
                self.services = Array(servicesDict.values).sorted { $0.name < $1.name }
                self.lastUpdate = Date()
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load services: \(error.localizedDescription)"
                self.isLoading = false
            }
        }
    }
    
    func loadServices() {
        Task {
            await loadServices()
        }
    }
    
    // MARK: - Service Actions
    
    func captureScreenshot() {
        Task {
            do {
                let service = services.first { $0.name == "simple_screen_service" }
                guard let service = service else {
                    await MainActor.run {
                        self.errorMessage = "Screen service not available"
                    }
                    return
                }
                
                let url = URL(string: "\(service.baseURL)/capture")!
                var request = URLRequest(url: url)
                request.httpMethod = "POST"
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                request.httpBody = "{}".data(using: .utf8)
                
                let (_, response) = try await URLSession.shared.data(for: request)
                
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    await MainActor.run {
                        // Success notification could be added here
                        print("Screenshot captured successfully")
                    }
                }
            } catch {
                await MainActor.run {
                    self.errorMessage = "Failed to capture screenshot: \(error.localizedDescription)"
                }
            }
        }
    }
    
    func executeWorkflow(_ workflowName: String) async -> Bool {
        do {
            let service = services.first { $0.name == "simple_workflow_service" }
            guard let service = service else {
                await MainActor.run {
                    self.errorMessage = "Workflow service not available"
                }
                return false
            }
            
            let url = URL(string: "\(service.baseURL)/execute/\(workflowName)")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = "{}".data(using: .utf8)
            
            let (_, response) = try await URLSession.shared.data(for: request)
            
            if let httpResponse = response as? HTTPURLResponse {
                return httpResponse.statusCode == 200
            }
            
            return false
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to execute workflow: \(error.localizedDescription)"
            }
            return false
        }
    }
    
    func loadScreenshots() async -> [Screenshot] {
        do {
            let service = services.first { $0.name == "simple_screen_service" }
            guard let service = service else { return [] }
            
            let url = URL(string: "\(service.baseURL)/list_screenshots")!
            let (data, _) = try await URLSession.shared.data(from: url)
            
            let response = try JSONDecoder().decode([String: [Screenshot]].self, from: data)
            return response["screenshots"] ?? []
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load screenshots: \(error.localizedDescription)"
            }
            return []
        }
    }
    
    func loadMemories() async -> [MemoryEntry] {
        do {
            let service = services.first { $0.name == "simple_memory_service" }
            guard let service = service else { return [] }
            
            let url = URL(string: "\(service.baseURL)/list")!
            let (data, _) = try await URLSession.shared.data(from: url)
            
            let response = try JSONDecoder().decode([String: [MemoryEntry]].self, from: data)
            return response["memories"] ?? []
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load memories: \(error.localizedDescription)"
            }
            return []
        }
    }
    
    func searchMemories(_ query: String) async -> [MemoryEntry] {
        do {
            let service = services.first { $0.name == "simple_memory_service" }
            guard let service = service else { return [] }
            
            let url = URL(string: "\(service.baseURL)/search")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            
            let searchData = ["query": query]
            request.httpBody = try JSONEncoder().encode(searchData)
            
            let (data, _) = try await URLSession.shared.data(for: request)
            
            let response = try JSONDecoder().decode([String: [MemoryEntry]].self, from: data)
            return response["results"] ?? []
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to search memories: \(error.localizedDescription)"
            }
            return []
        }
    }
    
    func loadWorkflowExecutions() async -> [WorkflowExecution] {
        do {
            let service = services.first { $0.name == "simple_workflow_service" }
            guard let service = service else { return [] }
            
            let url = URL(string: "\(service.baseURL)/execution_history")!
            let (data, _) = try await URLSession.shared.data(from: url)
            
            let response = try JSONDecoder().decode([String: [WorkflowExecution]].self, from: data)
            return response["executions"] ?? []
        } catch {
            await MainActor.run {
                self.errorMessage = "Failed to load workflow executions: \(error.localizedDescription)"
            }
            return []
        }
    }
    
    deinit {
        stopMonitoring()
    }
}
