# 🔧 MCP macOS Companion - API Reference Guide

## 📡 **Backend Service Endpoints**

### Service Registry (Port 8080)
**Base URL**: `http://localhost:8080`

#### Health & Status
```http
GET /health
Response: {
  "registered_services": 5,
  "status": "healthy", 
  "timestamp": 1753412919.5867252
}
```

#### Service Management
```http
GET /services
Response: {
  "services": [
    {
      "name": "memory_engine",
      "url": "http://localhost:8081",
      "status": "healthy",
      "last_heartbeat": "2025-07-25T13:08:31"
    }
  ]
}

POST /register
Body: {
  "name": "service_name",
  "url": "http://localhost:port",
  "endpoints": ["/health", "/process"]
}
```

---

### Memory Engine (Port 8081)  
**Base URL**: `http://localhost:8081`

#### Memory Storage
```http
POST /store
Body: {
  "content": "Text content to store",
  "source": "manual|auto|workflow", 
  "context_type": "user_action|screen_capture|file_operation",
  "metadata": {"key": "value"}
}
Response: {
  "memory_id": "mem_1753412931063",
  "status": "stored",
  "embedding_dimensions": 384
}
```

#### Memory Search
```http
POST /search  
Body: {
  "query": "search terms",
  "limit": 10,
  "threshold": 0.7
}
Response: {
  "matches": [
    {
      "memory_id": "mem_123",
      "content": "matching content",
      "similarity": 0.89,
      "timestamp": "2025-07-25T13:08:31"
    }
  ]
}
```

#### Memory Management
```http
GET /memories?limit=20&offset=0
Response: {
  "memories": [...],
  "total": 156,
  "page": 1
}

DELETE /memories/{memory_id}
Response: {"status": "deleted"}
```

---

### Finder Actions (Port 8082)
**Base URL**: `http://localhost:8082`

#### Smart Organization
```http
POST /smart_organize
Body: {
  "directory": "/Users/mark/Downloads",
  "dry_run": false,
  "rules": ["by_type", "by_date", "by_project"]
}
Response: {
  "results": {
    "files_moved": 23,
    "directories_created": 5,
    "actions": [
      {
        "file": "document.pdf",
        "action": "moved",
        "from": "/Users/mark/Downloads/document.pdf",
        "to": "/Users/mark/Downloads/Documents/2025/document.pdf"
      }
    ]
  }
}
```

#### Directory Monitoring
```http
POST /watch_directory
Body: {
  "directory": "/Users/mark/Desktop",
  "auto_organize": true,
  "rules": ["immediate_sort"]
}
Response: {
  "status": "watching_started",
  "directory": "/Users/mark/Desktop",
  "watcher_id": "watch_12345"
}

POST /unwatch_directory  
Body: {"watcher_id": "watch_12345"}
Response: {"status": "watching_stopped"}
```

#### File Information
```http
POST /file_info
Body: {"file_path": "/path/to/file.txt"}
Response: {
  "file_path": "/path/to/file.txt",
  "size": 1024,
  "created": "2025-07-25T10:30:00",
  "modified": "2025-07-25T13:08:31",
  "type": "text",
  "project_category": "development",
  "suggested_location": "/Users/mark/Projects/dev/"
}
```

#### Organization Rules
```http
GET /rules
Response: {
  "rules": [
    {
      "name": "Document Organization",
      "condition": {"file_type": ["pdf", "doc", "txt"]},
      "action": {"move_to": "Documents/{year}/"},
      "priority": 1
    }
  ]
}
```

---

### Screen Vision (Port 8083)
**Base URL**: `http://localhost:8083`

#### Screen Capture & Analysis
```http
POST /capture_screen
Body: {
  "analyze": true,
  "save_screenshot": true,
  "ocr_enabled": true
}
Response: {
  "timestamp": 1753412931.063,
  "screenshot_path": "/Users/mark/.mcp/screenshots/screen_2025-07-25_13-08-31.png",
  "ocr_text": "Extracted text from screen...",
  "detected_elements": [
    {
      "type": "button",
      "text": "Click me",
      "position": {"x": 100, "y": 200},
      "confidence": 0.95
    }
  ],
  "content_hash": "abc123def456"
}
```

#### Content History
```http
GET /content_history?limit=10
Response: {
  "content_history": [
    {
      "timestamp": 1753412931.063,
      "screenshot_path": "/path/to/screenshot.png",
      "ocr_text": "Text preview...",
      "detected_elements_count": 5,
      "content_hash": "abc123"
    }
  ]
}
```

#### Content Search
```http
POST /search_content
Body: {
  "query": "error message",
  "case_sensitive": false
}
Response: {
  "matches": [
    {
      "timestamp": 1753412800.123,
      "screenshot_path": "/path/to/screenshot.png", 
      "matching_text": "...found error message in context...",
      "content_hash": "def789"
    }
  ]
}
```

#### Monitoring Control
```http
POST /start_monitoring
Response: {"status": "monitoring_started"}

POST /stop_monitoring  
Response: {"status": "monitoring_stopped"}

GET /triggers
Response: {
  "triggers": [
    {
      "name": "Error Detection",
      "condition": {"text_contains": "error"},
      "action": {"store_context": "error_detected"},
      "active": true
    }
  ]
}
```

---

### Workflow Orchestrator (Port 8084)
**Base URL**: `http://localhost:8084`

#### Workflow Templates
```http
GET /templates
Response: {
  "organize_and_screenshot": {
    "name": "Organize & Screenshot",
    "description": "Organize files and capture screen",
    "steps": [
      "organize_downloads",
      "capture_screen", 
      "save_to_memory"
    ]
  },
  "daily_cleanup": {
    "name": "Daily Cleanup",
    "description": "Clean desktop and organize files",
    "steps": [
      "clean_desktop",
      "organize_downloads",
      "archive_old_files"
    ]
  }
}
```

#### Workflow Execution  
```http
POST /execute
Body: {
  "workflow_id": "organize_and_screenshot",
  "parameters": {
    "directory": "/Users/mark/Downloads",
    "notify_completion": true
  }
}
Response: {
  "execution_id": "exec_1753412931",
  "status": "started",
  "estimated_duration": "30 seconds"
}

GET /execution/{execution_id}/status
Response: {
  "execution_id": "exec_1753412931",
  "status": "completed|running|failed", 
  "progress": 100,
  "steps_completed": 3,
  "total_steps": 3,
  "results": [...]
}
```

#### Workflow Management
```http
POST /create_workflow
Body: {
  "name": "Custom Workflow",
  "description": "Description here",
  "steps": ["step1", "step2", "step3"]
}

PUT /workflows/{workflow_id}
Body: {
  "name": "Updated name",
  "steps": ["updated_steps"]
}

DELETE /workflows/{workflow_id}
Response: {"status": "deleted"}
```

#### Service Integration
```http
GET /services
Response: {
  "available_services": [
    {
      "name": "memory_engine",
      "url": "http://localhost:8081",
      "capabilities": ["store", "search", "analyze"]
    }
  ]
}

POST /refresh_services
Response: {
  "status": "refreshed",
  "services_found": 4
}
```

---

### Whisper Client Mock (Port 8085)
**Base URL**: `http://localhost:8085`

#### Audio Transcription (Mock)
```http
POST /transcribe
Body: {
  "audio_file": "base64_encoded_audio_data",
  "language": "en",
  "model": "whisper-1"
}
Response: {
  "transcription": "[MOCK] This is a simulated transcription",
  "confidence": 0.95,
  "language": "en",
  "duration": 5.2,
  "status": "mock_mode"
}
```

#### Health Status
```http
GET /health
Response: {
  "status": "healthy",
  "service": "whisper_client_mock", 
  "port": 8085,
  "timestamp": 1753412931.063,
  "mode": "mock"
}
```

---

## 📱 **SwiftUI App Integration**

### Quick Actions API Calls
The SwiftUI app uses these specific endpoints:

```swift
// Screen Capture
POST http://localhost:8083/capture_screen
Body: {"analyze": true}

// File Organization  
POST http://localhost:8082/smart_organize
Body: {"directory": "/Users/mark/Downloads"}

// Memory Storage
POST http://localhost:8081/store  
Body: {
  "content": "User requested context save",
  "source": "manual",
  "context_type": "user_action"
}

// Workflow Execution
POST http://localhost:8084/execute
Body: {"workflow_id": "organize_and_screenshot"}
```

### Service Health Monitoring
```swift
// Health check for all services
let services = [8080, 8081, 8082, 8083, 8084, 8085]
for port in services {
    let response = try await URLSession.shared.data(from: URL(string: "http://localhost:\(port)/health")!)
}
```

---

## 🔧 **Error Handling**

### Common HTTP Status Codes
- **200 OK**: Request successful
- **400 Bad Request**: Invalid request data
- **404 Not Found**: Endpoint doesn't exist  
- **500 Internal Server Error**: Service error
- **503 Service Unavailable**: Service down

### Error Response Format
```json
{
  "error": "Error description",
  "code": "ERROR_CODE",
  "timestamp": "2025-07-25T13:08:31",
  "details": {
    "additional": "context"
  }
}
```

---

## 🚀 **Testing Commands**

### Health Check All Services
```bash
curl http://localhost:8080/health  # Service Registry
curl http://localhost:8081/health  # Memory Engine
curl http://localhost:8082/health  # Finder Actions  
curl http://localhost:8083/health  # Screen Vision
curl http://localhost:8084/health  # Workflow Orchestrator
curl http://localhost:8085/health  # Whisper Client
```

### Test Core Functionality
```bash
# Test screen capture
curl -X POST http://localhost:8083/capture_screen \
  -H "Content-Type: application/json" \
  -d '{"analyze": true}'

# Test file organization
curl -X POST http://localhost:8082/smart_organize \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/mark/Downloads"}'

# Test memory storage  
curl -X POST http://localhost:8081/store \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "source": "api_test"}'
```

This API reference provides complete documentation for integrating with all MCP Companion services.