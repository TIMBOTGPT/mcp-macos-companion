import SwiftUI
import Foundation

struct VoiceRecordingView: View {
    @State private var isRecording = false
    @State private var isProcessing = false
    @State private var sessionId: String = ""
    @State private var transcriptionResult: String = ""
    @State private var recordingLevel: Double = 0.0
    @State private var statusMessage: String = "Ready to record"
    @State private var confidence: Double = 0.0
    @Environment(\.presentationMode) var presentationMode
    
    var body: some View {
        VStack(spacing: 20) {
            // Header
            HStack {
                Button("Cancel") {
                    if isRecording {
                        stopRecording()
                    }
                    presentationMode.wrappedValue.dismiss()
                }
                Spacer()
                Text("Voice Recording")
                    .font(.headline)
                Spacer()
                Button("Done") {
                    presentationMode.wrappedValue.dismiss()
                }
                .disabled(isRecording || isProcessing)
            }
            .padding()
            
            Spacer()
            
            // Recording Status Indicator
            VStack(spacing: 16) {
                // Visual indicator
                Circle()
                    .fill(isRecording ? Color.red : Color.gray)
                    .frame(width: 100, height: 100)
                    .scaleEffect(isRecording ? 1.2 : 1.0)
                    .opacity(isRecording ? 0.8 : 0.4)
                    .animation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true), value: isRecording)
                    .overlay(
                        Image(systemName: isRecording ? "mic.fill" : "mic")
                            .font(.system(size: 40))
                            .foregroundColor(.white)
                    )
                
                // Status text
                Text(statusMessage)
                    .font(.title2)
                    .foregroundColor(isRecording ? .red : .primary)
                
                // Recording level indicator
                if isRecording {
                    VStack {
                        Text("Microphone Level")
                            .font(.caption)
                        
                        ProgressView(value: recordingLevel, total: 1.0)
                            .progressViewStyle(LinearProgressViewStyle(tint: .green))
                            .frame(width: 200)
                    }
                }
                
                // Processing indicator
                if isProcessing {
                    HStack {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle())
                        Text("Processing speech...")
                    }
                }
            }
            
            Spacer()
            
            // Transcription Results
            if !transcriptionResult.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Transcription:")
                        .font(.headline)
                    
                    ScrollView {
                        Text(transcriptionResult)
                            .padding()
                            .background(Color.secondary.opacity(0.1))
                            .cornerRadius(8)
                    }
                    .frame(maxHeight: 120)
                    
                    if confidence > 0 {
                        HStack {
                            Text("Confidence:")
                            ProgressView(value: confidence, total: 1.0)
                                .progressViewStyle(LinearProgressViewStyle(tint: confidence > 0.7 ? .green : confidence > 0.4 ? .yellow : .red))
                            Text("\(Int(confidence * 100))%")
                        }
                        .font(.caption)
                    }
                }
                .padding()
            }
            
            Spacer()
            
            // Record Button
            Button(action: {
                if isRecording {
                    stopRecording()
                } else {
                    startRecording()
                }
            }) {
                HStack {
                    Image(systemName: isRecording ? "stop.circle.fill" : "mic.circle.fill")
                    Text(isRecording ? "Stop Recording" : "Start Recording")
                }
                .font(.title2)
                .foregroundColor(.white)
                .padding()
                .background(isRecording ? Color.red : Color.blue)
                .cornerRadius(10)
            }
            .disabled(isProcessing)
            
            Spacer()
        }
        .onAppear {
            checkVoiceService()
        }
    }
    
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
                            statusMessage = "Recording... (tap to stop)"
                            transcriptionResult = ""
                            confidence = 0.0
                            
                            // Simulate microphone level animation
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
                    // Wait for processing
                    try await Task.sleep(nanoseconds: 3_000_000_000) // 3 seconds
                    
                    // Get results
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
}

#Preview {
    VoiceRecordingView()
}