import Foundation

struct Workflow: Identifiable, Codable {
    let id: String
    var name: String
    var description: String
    var steps: [String]
    var isEnabled: Bool = true
    var lastExecuted: Date?
    
    init(id: String, name: String, description: String, steps: [String]) {
        self.id = id
        self.name = name
        self.description = description
        self.steps = steps
    }
}

import SwiftUI

struct WorkflowCard: View {
    let workflow: Workflow
    let onExecute: () -> Void
    let onEdit: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(workflow.name)
                        .font(.headline)
                        .foregroundColor(.primary)
                    
                    Text(workflow.description)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(2)
                }
                
                Spacer()
                
                Circle()
                    .fill(workflow.isEnabled ? Color.green : Color.gray)
                    .frame(width: 8, height: 8)
            }
            
            // Steps preview
            VStack(alignment: .leading, spacing: 2) {
                Text("Steps:")
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(.secondary)
                
                ForEach(Array(workflow.steps.prefix(3).enumerated()), id: \.offset) { index, step in
                    Text("\(index + 1). \(step)")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                
                if workflow.steps.count > 3 {
                    Text("+ \(workflow.steps.count - 3) more steps")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .italic()
                }
            }
            
            HStack {
                Button("Execute") {
                    onExecute()
                }
                .buttonStyle(CompactButtonStyle(color: .blue))
                
                Button("Edit") {
                    onEdit()
                }
                .buttonStyle(CompactButtonStyle(color: .gray))
                
                Spacer()
                
                if let lastExecuted = workflow.lastExecuted {
                    Text("Last: \(RelativeDateTimeFormatter().localizedString(for: lastExecuted, relativeTo: Date()))")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding()
        .background(Color.secondary.opacity(0.1))
        .cornerRadius(12)
    }
}

struct CompactButtonStyle: ButtonStyle {
    let color: Color
    
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.caption)
            .foregroundColor(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(color.opacity(configuration.isPressed ? 0.8 : 1.0))
            .cornerRadius(4)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
    }
}