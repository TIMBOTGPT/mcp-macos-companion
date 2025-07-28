import SwiftUI
import UserNotifications

struct WorkflowsView: View {
    @ObservedObject var serviceMonitor: ServiceMonitor
    @State private var workflows: [Workflow] = []
    @State private var isLoading = false
    @State private var selectedWorkflow: Workflow?
    
    var body: some View {
        VStack {
            if isLoading {
                ProgressView("Loading workflows...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(workflows) { workflow in
                            WorkflowCard(
                                workflow: workflow,
                                onExecute: { executeWorkflow(workflow) },
                                onEdit: { selectedWorkflow = workflow }
                            )
                        }
                        
                        // Add new workflow button
                        Button("Create New Workflow") {
                            createNewWorkflow()
                        }
                        .buttonStyle(ActionButtonStyle(color: .blue))
                        .padding(.top)
                    }
                    .padding()
                }
            }
        }
        .onAppear {
            loadWorkflows()
            requestNotificationPermission()
        }
        .sheet(item: $selectedWorkflow) { workflow in
            WorkflowEditView(workflow: workflow) { updatedWorkflow in
                updateWorkflow(updatedWorkflow)
            }
        }
    }
    
    private func loadWorkflows() {
        isLoading = true
        
        Task {
            do {
                let data = try await fetchWorkflows()
                await MainActor.run {
                    self.workflows = data
                    self.isLoading = false
                }
            } catch {
                await MainActor.run {
                    self.workflows = getSampleWorkflows()
                    self.isLoading = false
                }
            }
        }
    }
    
    private func fetchWorkflows() async throws -> [Workflow] {
        guard let url = URL(string: "http://localhost:8084/templates") else {
            throw URLError(.badURL)
        }
        
        let (data, _) = try await URLSession.shared.data(from: url)
        
        // Handle the response as a generic JSON object first
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw URLError(.cannotParseResponse)
        }
        
        // Convert to workflows
        return json.compactMap { (key, value) -> Workflow? in
            guard let workflowData = value as? [String: Any] else { return nil }
            
            return Workflow(
                id: key,
                name: workflowData["name"] as? String ?? key,
                description: workflowData["description"] as? String ?? "No description",
                steps: workflowData["steps"] as? [String] ?? []
            )
        }
    }
    
    private func executeWorkflow(_ workflow: Workflow) {
        Task {
            do {
                let url = URL(string: "http://localhost:8084/execute")!
                var request = URLRequest(url: url)
                request.httpMethod = "POST"
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                
                let body = ["workflow_id": workflow.id]
                request.httpBody = try JSONSerialization.data(withJSONObject: body)
                
                let (_, response) = try await URLSession.shared.data(for: request)
                
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    await MainActor.run {
                        showNotification("Workflow '\(workflow.name)' executed successfully")
                    }
                }
            } catch {
                await MainActor.run {
                    showNotification("Failed to execute workflow: \(error.localizedDescription)")
                }
            }
        }
    }
    
    private func createNewWorkflow() {
        let newWorkflow = Workflow(
            id: UUID().uuidString,
            name: "New Workflow",
            description: "Describe what this workflow does",
            steps: ["Step 1", "Step 2"]
        )
        selectedWorkflow = newWorkflow
    }
    
    private func updateWorkflow(_ workflow: Workflow) {
        if let index = workflows.firstIndex(where: { $0.id == workflow.id }) {
            workflows[index] = workflow
        } else {
            workflows.append(workflow)
        }
    }
    
    private func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { granted, error in
            if let error = error {
                print("Notification permission error: \(error)")
            }
        }
    }
    
    private func showNotification(_ message: String) {
        let content = UNMutableNotificationContent()
        content.title = "MCP Companion"
        content.body = message
        content.sound = .default
        
        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil
        )
        
        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("Failed to show notification: \(error)")
            }
        }
    }
    
    private func getSampleWorkflows() -> [Workflow] {
        [
            Workflow(
                id: "organize_and_screenshot",
                name: "Organize & Screenshot",
                description: "Organize files and take a screenshot",
                steps: ["Organize Downloads", "Capture Screen", "Save to Memory"]
            ),
            Workflow(
                id: "daily_cleanup",
                name: "Daily Cleanup",
                description: "Clean desktop and organize recent files",
                steps: ["Clean Desktop", "Organize Downloads", "Archive Old Files"]
            )
        ]
    }
}