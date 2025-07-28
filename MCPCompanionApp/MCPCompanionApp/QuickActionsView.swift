import SwiftUI

struct QuickActionsView: View {
    @ObservedObject var serviceMonitor: ServiceMonitor
    @State private var isExecuting = false
    @State private var lastActionResult: String = ""
    @State private var showingVoiceRecording = false
    
    var body: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                // Screen Actions
                ActionSection(title: "Screen Actions") {
                    ActionButton(
                        title: "Capture Screen",
                        icon: "camera.viewfinder",
                        color: .blue
                    ) {
                        executeAction("capture_screen")
                    }
                    
                    ActionButton(
                        title: "OCR Current Screen",
                        icon: "text.viewfinder",
                        color: .green
                    ) {
                        executeAction("ocr_screen")
                    }
                }
                
                // File Actions
                ActionSection(title: "File Management") {
                    ActionButton(
                        title: "Organize Downloads",
                        icon: "folder.badge.gearshape",
                        color: .orange
                    ) {
                        executeAction("organize_downloads")
                    }
                    
                    ActionButton(
                        title: "Clean Desktop",
                        icon: "trash",
                        color: .red
                    ) {
                        executeAction("clean_desktop")
                    }
                }
                
                // Voice Actions
                ActionSection(title: "Voice & Speech") {
                    ActionButton(
                        title: "Voice Recording",
                        icon: "mic.circle.fill",
                        color: .pink
                    ) {
                        showingVoiceRecording = true
                    }
                    
                    ActionButton(
                        title: "Voice Test Interface",
                        icon: "waveform.circle",
                        color: .cyan
                    ) {
                        openVoiceInterface()
                    }
                }
                
                // Memory Actions
                ActionSection(title: "Memory & Search") {
                    ActionButton(
                        title: "Search Memories",
                        icon: "magnifyingglass.circle",
                        color: .purple
                    ) {
                        openMemorySearch()
                    }
                    
                    ActionButton(
                        title: "Save Current Context",
                        icon: "brain.head.profile",
                        color: .indigo
                    ) {
                        executeAction("save_context")
                    }
                }
                
                // Results display
                if !lastActionResult.isEmpty {
                    ResultView(result: lastActionResult)
                }
            }
            .padding()
        }
        .disabled(isExecuting)
        .sheet(isPresented: $showingVoiceRecording) {
            VoiceRecordingView()
        }
        .overlay(
            Group {
                if isExecuting {
                    ProgressView("Executing...")
                        .progressViewStyle(CircularProgressViewStyle())
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color.black.opacity(0.3))
                }
            }
        )
    }
    
    private func executeAction(_ action: String) {
        isExecuting = true
        lastActionResult = ""
        
        Task {
            do {
                let result = try await performAction(action)
                await MainActor.run {
                    lastActionResult = result
                    isExecuting = false
                }
            } catch {
                await MainActor.run {
                    lastActionResult = "Error: \(error.localizedDescription)"
                    isExecuting = false
                }
            }
        }
    }
    
    private func performAction(_ action: String) async throws -> String {
        switch action {
        case "capture_screen":
            return try await callAPI("http://localhost:8083/capture_screen", method: "POST")
        case "ocr_screen":
            return try await callAPI("http://localhost:8083/capture_screen", method: "POST")
        case "organize_downloads":
            return try await callAPIWithBody("http://localhost:8082/smart_organize", body: ["directory": "/Users/mark/Downloads"])
        case "clean_desktop":
            return try await callAPIWithBody("http://localhost:8082/smart_organize", body: ["directory": "/Users/mark/Desktop"])
        case "save_context":
            return try await callAPIWithBody("http://localhost:8081/store", body: ["content": "User requested context save", "source": "manual", "context_type": "user_action"])
        case "start_voice_recording":
            return try await callAPI("http://localhost:8085/recording/start", method: "POST")
        default:
            return "Unknown action"
        }
    }
    
    private func callAPIWithBody(_ urlString: String, body: [String: Any]) async throws -> String {
        guard let url = URL(string: urlString) else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return String(data: data, encoding: .utf8) ?? "Success"
    }
    
    private func callAPI(_ urlString: String, method: String) async throws -> String {
        guard let url = URL(string: urlString) else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return String(data: data, encoding: .utf8) ?? "Success"
    }
    
    private func openMemorySearch() {
        let url = URL(string: "http://localhost:8081/search")!
        NSWorkspace.shared.open(url)
    }
    
    private func openVoiceInterface() {
        let url = URL(fileURLWithPath: "/Users/mark/Desktop/MCP STUFF/mcp-macos-companion/services/voice_test_interface.html")
        NSWorkspace.shared.open(url)
    }
}