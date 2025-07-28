import SwiftUI

struct WorkflowEditView: View {
    @State private var workflow: Workflow
    let onSave: (Workflow) -> Void
    @Environment(\.dismiss) private var dismiss
    
    init(workflow: Workflow, onSave: @escaping (Workflow) -> Void) {
        self._workflow = State(initialValue: workflow)
        self.onSave = onSave
    }
    
    var body: some View {
        NavigationView {
            Form {
                Section("Basic Information") {
                    TextField("Workflow Name", text: $workflow.name)
                    TextField("Description", text: $workflow.description, axis: .vertical)
                        .lineLimit(2...4)
                }
                
                Section("Steps") {
                    ForEach(Array(workflow.steps.enumerated()), id: \.offset) { index, step in
                        HStack {
                            TextField("Step \(index + 1)", text: Binding(
                                get: { workflow.steps[index] },
                                set: { workflow.steps[index] = $0 }
                            ))
                            
                            Button("Remove") {
                                workflow.steps.remove(at: index)
                            }
                            .foregroundColor(.red)
                        }
                    }
                    
                    Button("Add Step") {
                        workflow.steps.append("New step")
                    }
                }
                
                Section("Settings") {
                    Toggle("Enabled", isOn: $workflow.isEnabled)
                }
            }
            .navigationTitle("Edit Workflow")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        onSave(workflow)
                        dismiss()
                    }
                }
            }
        }
        .frame(width: 500, height: 400)
    }
}