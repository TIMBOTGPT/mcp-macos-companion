import SwiftUI
import Foundation

class FloatingVoiceWindow: NSObject, ObservableObject {
    private var window: NSWindow?
    @Published var isShowing = false
    
    func show() {
        if window == nil {
            createWindow()
        }
        
        window?.makeKeyAndOrderFront(nil)
        window?.orderFrontRegardless()
        isShowing = true
    }
    
    func hide() {
        window?.orderOut(nil)
        isShowing = false
    }
    
    func toggle() {
        if isShowing {
            hide()
        } else {
            show()
        }
    }
    
    private func createWindow() {
        let contentView = FloatingVoiceRecordingView { [weak self] in
            self?.hide()
        }
        
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 320, height: 500),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        window?.contentView = NSHostingView(rootView: contentView)
        window?.title = "Voice Recording"
        window?.isReleasedWhenClosed = false
        window?.level = .floating
        window?.isMovableByWindowBackground = true
        window?.titlebarAppearsTransparent = true
        window?.backgroundColor = NSColor.controlBackgroundColor
        
        // Center the window
        window?.center()
        
        // Add close button behavior
        window?.delegate = self
        
        // Make window accept key events
        window?.acceptsMouseMovedEvents = true
        window?.makeFirstResponder(window?.contentView)
    }
}

extension FloatingVoiceWindow: NSWindowDelegate {
    func windowWillClose(_ notification: Notification) {
        isShowing = false
    }
}

struct FloatingVoiceRecordingView: View {
    @State private var isRecording = false
    @State private var isProcessing = false
    @State private var isExecutingCommand = false
    @State private var sessionId: String = ""
    @State private var transcriptionResult: String = ""
    @State private var recordingLevel: Double = 0.0
    @State private var statusMessage: String = "Ready to record"
    @State private var confidence: Double = 0.0
    
    let onClose: () -> Void
    
    var body: some View {
        VStack(spacing: 20) {
            // Recording Status Indicator
            VStack(spacing: 16) {
                // Visual indicator with improved microphone states
                ZStack {
                    Circle()
                        .fill(isRecording ? 
                              LinearGradient(colors: [.red, .pink], startPoint: .topLeading, endPoint: .bottomTrailing) :
                              LinearGradient(colors: [.gray.opacity(0.6), .gray], startPoint: .topLeading, endPoint: .bottomTrailing)
                        )
                        .frame(width: 120, height: 120)
                        .scaleEffect(isRecording ? 1.0 : 1.0)
                        .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: isRecording)
                    
                    Circle()
                        .stroke(Color.white.opacity(0.3), lineWidth: 2)
                        .frame(width: 120, height: 120)
                    
                    // Microphone icon with cross for idle state
                    ZStack {
                        Image(systemName: "mic.fill")
                            .font(.system(size: 45))
                            .foregroundColor(.white)
                            .shadow(radius: 2)
                        
                        // Cross line for idle state (grey microphone with cross)
                        if !isRecording {
                            Rectangle()
                                .fill(Color.red)
                                .frame(width: 60, height: 4)
                                .rotationEffect(.degrees(45))
                                .shadow(radius: 1)
                        }
                    }
                }
                // Add pulsing animation only when recording
                .scaleEffect(isRecording ? (1.0 + sin(Date().timeIntervalSince1970 * 4) * 0.05) : 1.0)
                .animation(isRecording ? .easeInOut(duration: 0.8).repeatForever(autoreverses: true) : .default, value: isRecording)
                
                // Status text with better styling
                Text(statusMessage)
                    .font(.title2)
                    .fontWeight(.medium)
                    .foregroundColor(isRecording ? .red : .primary)
                    .multilineTextAlignment(.center)
                
                // Recording level indicator with improved design
                if isRecording {
                    VStack(spacing: 8) {
                        Text("Microphone Level")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.gray.opacity(0.3))
                                .frame(width: 200, height: 8)
                            
                            RoundedRectangle(cornerRadius: 8)
                                .fill(LinearGradient(
                                    colors: [.green, .yellow, .red],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                ))
                                .frame(width: 200 * recordingLevel, height: 8)
                                .animation(.easeInOut(duration: 0.1), value: recordingLevel)
                        }
                    }
                }
                
                // Processing indicator with better styling
                if isProcessing {
                    HStack(spacing: 12) {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .blue))
                            .scaleEffect(0.8)
                        Text("Processing speech...")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(12)
                }
                
                // Command execution indicator
                if isExecutingCommand {
                    HStack(spacing: 12) {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .green))
                            .scaleEffect(0.8)
                        Text("Executing command...")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                    .background(Color.green.opacity(0.1))
                    .cornerRadius(12)
                }
            }
            
            // Transcription Results with improved styling
            if !transcriptionResult.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Image(systemName: "text.bubble")
                            .foregroundColor(.blue)
                        Text("Transcription")
                            .font(.headline)
                            .foregroundColor(.primary)
                    }
                    
                    ScrollView {
                        Text(transcriptionResult)
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.secondary.opacity(0.08))
                            .cornerRadius(12)
                            .font(.body)
                    }
                    .frame(maxHeight: 100)
                    
                    if confidence > 0 {
                        HStack(spacing: 8) {
                            Image(systemName: "gauge")
                                .foregroundColor(.secondary)
                            Text("Confidence:")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            ZStack(alignment: .leading) {
                                RoundedRectangle(cornerRadius: 4)
                                    .fill(Color.gray.opacity(0.3))
                                    .frame(height: 6)
                                
                                RoundedRectangle(cornerRadius: 4)
                                    .fill(confidence > 0.7 ? Color.green : confidence > 0.4 ? Color.yellow : Color.red)
                                    .frame(width: 100 * confidence, height: 6)
                            }
                            .frame(width: 100)
                            
                            Text("\(Int(confidence * 100))%")
                                .font(.caption)
                                .fontWeight(.medium)
                        }
                    }
                }
                .padding(.horizontal)
            }
            
            Spacer()
            
            // Record Button with improved styling
            Button(action: {
                if isRecording {
                    stopRecording()
                } else {
                    startRecording()
                }
            }) {
                HStack(spacing: 12) {
                    Image(systemName: isRecording ? "stop.circle.fill" : "mic.circle.fill")
                        .font(.title2)
                    Text(isRecording ? "Stop Recording" : "Start Recording")
                        .font(.headline)
                        .fontWeight(.medium)
                }
                .foregroundColor(.white)
                .padding(.horizontal, 24)
                .padding(.vertical, 12)
                .background(
                    LinearGradient(
                        colors: isRecording ? [.red, .pink] : [.blue, .cyan],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .cornerRadius(25)
                .shadow(color: (isRecording ? Color.red : Color.blue).opacity(0.3), radius: 8, x: 0, y: 4)
            }
            .buttonStyle(PlainButtonStyle())
            .disabled(isProcessing || isExecutingCommand)
            .scaleEffect(isProcessing ? 0.95 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: isProcessing)
            
            // Keyboard shortcuts hint
            VStack(spacing: 4) {
                HStack(spacing: 12) {
                    HStack(spacing: 4) {
                        Text("⏎")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(.secondary)
                        Text("Stop")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                    
                    HStack(spacing: 4) {
                        Text("⎵")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(.secondary)
                        Text("Start/Stop")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                    
                    HStack(spacing: 4) {
                        Text("⎋")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundColor(.secondary)
                        Text("Close")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Color.secondary.opacity(0.1))
                .cornerRadius(8)
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(
            LinearGradient(
                colors: [Color.clear, Color.blue.opacity(0.05)],
                startPoint: .top,
                endPoint: .bottom
            )
        )
        .onAppear {
            checkVoiceService()
        }
        .background(KeyEventHandling { keyEvent in
            handleKeyEvent(keyEvent)
        })
    }
    
    private func handleKeyEvent(_ event: NSEvent) {
        switch event.keyCode {
        case 36: // Return/Enter key
            if isRecording {
                stopRecording()
            }
        case 49: // Space key
            if !isProcessing && !isExecutingCommand {
                if isRecording {
                    stopRecording()
                } else {
                    startRecording()
                }
            }
        case 53: // Escape key
            onClose()
        default:
            break
        }
    }
    
    // Voice service functions
    private func checkVoiceService() {
        Task {
            do {
                let url = URL(string: "http://localhost:8085/health")!
                let (_, response) = try await URLSession.shared.data(from: url)
                
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    await MainActor.run {
                        statusMessage = "Voice service ready"
                    }
                } else {
                    await MainActor.run {
                        statusMessage = "Voice service unavailable"
                    }
                }
            } catch {
                await MainActor.run {
                    statusMessage = "Voice service error"
                }
            }
        }
    }
    
    private func startRecording() {
        Task {
            do {
                let url = URL(string: "http://localhost:8085/recording/start")!
                var request = URLRequest(url: url)
                request.httpMethod = "POST"
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                
                let (data, response) = try await URLSession.shared.data(for: request)
                
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    let result = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                    
                    await MainActor.run {
                        if let success = result?["success"] as? Bool, success,
                           let id = result?["session_id"] as? String {
                            sessionId = id
                            isRecording = true
                            statusMessage = "Recording in progress..."
                            transcriptionResult = ""
                            confidence = 0.0
                            
                            simulateMicLevel()
                        }
                    }
                }
            } catch {
                await MainActor.run {
                    statusMessage = "Failed to start recording"
                }
            }
        }
    }
    
    private func stopRecording() {
        Task {
            do {
                let url = URL(string: "http://localhost:8085/recording/stop/\(sessionId)")!
                var request = URLRequest(url: url)
                request.httpMethod = "POST"
                
                let (_, response) = try await URLSession.shared.data(for: request)
                
                await MainActor.run {
                    isRecording = false
                    isProcessing = true
                    statusMessage = "Processing speech..."
                    recordingLevel = 0.0
                }
                
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    try await Task.sleep(nanoseconds: 3_000_000_000)
                    await getTranscriptionResult()
                }
            } catch {
                await MainActor.run {
                    isProcessing = false
                    statusMessage = "Failed to stop recording"
                }
            }
        }
    }
    
    private func getTranscriptionResult() async {
        do {
            let url = URL(string: "http://localhost:8085/recording/status/\(sessionId)")!
            let (data, response) = try await URLSession.shared.data(from: url)
            
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                let result = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                
                await MainActor.run {
                    isProcessing = false
                    
                    if let transcriptionData = result?["result"] as? [String: Any],
                       let text = transcriptionData["text"] as? String {
                        
                        if text.isEmpty {
                            transcriptionResult = "No speech detected. Please try speaking closer to the microphone."
                            statusMessage = "No speech detected"
                        } else {
                            transcriptionResult = text
                            statusMessage = "Transcription complete"
                            
                            if let conf = transcriptionData["confidence"] as? Double {
                                confidence = conf
                            }
                            
                            // Send transcribed text to MCP workflow orchestrator
                            sendToWorkflowOrchestrator(text: text)
                        }
                    } else {
                        transcriptionResult = "Processing failed"
                        statusMessage = "Processing failed"
                    }
                }
            }
        } catch {
            await MainActor.run {
                isProcessing = false
                statusMessage = "Failed to get results"
            }
        }
    }
    
    private func simulateMicLevel() {
        Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { timer in
            if isRecording {
                recordingLevel = Double.random(in: 0.2...0.9)
            } else {
                timer.invalidate()
                recordingLevel = 0.0
            }
        }
    }
    
    private func sendToWorkflowOrchestrator(text: String) {
        Task {
            await MainActor.run {
                isExecutingCommand = true
                statusMessage = "Executing command..."
            }
            
            do {
                // Send voice command to workflow orchestrator
                let url = URL(string: "http://localhost:8084/trigger")!
                var request = URLRequest(url: url)
                request.httpMethod = "POST"
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                
                let payload = [
                    "trigger_type": "voice_command",
                    "trigger_data": [
                        "command": text,
                        "source": "voice_recording",
                        "timestamp": ISO8601DateFormatter().string(from: Date())
                    ]
                ]
                
                request.httpBody = try JSONSerialization.data(withJSONObject: payload)
                
                let (data, response) = try await URLSession.shared.data(for: request)
                
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    if let responseData = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        await MainActor.run {
                            isExecutingCommand = false
                            statusMessage = "Command executed successfully"
                        }
                        print("Voice command sent to orchestrator: \(responseData)")
                    }
                } else {
                    await MainActor.run {
                        isExecutingCommand = false
                        statusMessage = "Command processing failed"
                    }
                }
            } catch {
                await MainActor.run {
                    isExecutingCommand = false
                    statusMessage = "Failed to send command"
                }
                print("Error sending to orchestrator: \(error)")
            }
        }
    }
}

// MARK: - Keyboard Event Handling
struct KeyEventHandling: NSViewRepresentable {
    let onKeyEvent: (NSEvent) -> Void
    
    func makeNSView(context: Context) -> KeyEventView {
        let view = KeyEventView()
        view.onKeyEvent = onKeyEvent
        return view
    }
    
    func updateNSView(_ nsView: KeyEventView, context: Context) {
        nsView.onKeyEvent = onKeyEvent
    }
}

class KeyEventView: NSView {
    var onKeyEvent: ((NSEvent) -> Void)?
    
    override var acceptsFirstResponder: Bool { true }
    
    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        window?.makeFirstResponder(self)
    }
    
    override func keyDown(with event: NSEvent) {
        onKeyEvent?(event)
        super.keyDown(with: event)
    }
}
