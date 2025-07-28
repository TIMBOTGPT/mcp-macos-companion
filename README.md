# MCP macOS Companion - Backend Services

A comprehensive macOS automation system built with Model Context Protocol (MCP) integration, providing workflow orchestration, Claude AI integration, and intelligent voice command processing.

## 🏗️ Architecture Overview

This system consists of multiple interconnected services that work together to provide seamless macOS automation with AI-powered intelligence:

### Core Services

- **Service Registry** (port 8081) - Central service discovery and health monitoring
- **Workflow Orchestrator** (port 8084) - Intelligent workflow execution and cross-service coordination  
- **Claude Service Bridge** (port 8092) - Natural language processing and command interpretation
- **Memory Engine** (port 8082) - Context storage and retrieval system
- **Voice Processing** (port 8085) - Speech-to-text and audio processing

## 🎤 Voice Integration

The system provides sophisticated voice command processing with:

### Intelligent Command Recognition
- **Natural Language Processing**: Commands processed through Claude AI for contextual understanding
- **Speech Recognition Error Handling**: Handles common misinterpretations (e.g., "NAS equality" → "NAS RAID")
- **Multi-Pattern Matching**: Supports various phrasings for the same action

### Supported Voice Commands
- **"Open NAS RAID"** (and variations: "NAS equality", "NAS rate") → Opens network drive
- **"Open 4TB SSD"** → Opens external SSD drive
- **"Open MCP stuff folder"** → Opens project directory
- **"Take a screenshot"** → Captures screen with notification
- **"Search [location] for [files]"** → Intelligent file searching

### Advanced Features
- **Folder Opening with Notifications**: Visual and audio feedback for all operations
- **Smart Path Detection**: Tries multiple common locations for requested items
- **AppleScript Integration**: Enhanced window management and system control
- **Error Recovery**: Graceful fallbacks when primary methods fail

## 🔧 Technical Implementation

### Workflow Orchestration Engine
The `workflow_orchestrator.py` provides:

- **Template-based Workflows**: Predefined automation sequences
- **Parameter Interpolation**: Dynamic value substitution in workflow steps
- **Service Discovery**: Automatic detection and health monitoring of backend services
- **Error Handling**: Robust retry logic and failure recovery
- **Cross-Service Communication**: HTTP-based inter-service messaging

### Claude Integration
The `simple_claude_bridge.py` delivers:

- **Natural Language Understanding**: Commands processed through Claude AI
- **Action Mapping**: Intelligent translation of voice commands to system actions
- **Context Awareness**: Maintains conversation state and user preferences
- **Fallback Responses**: Graceful handling when AI processing is unavailable

## 🚀 Quick Start

### Prerequisites
- macOS 13.0+ (Ventura or later)
- Python 3.8+
- Flask and dependencies
- Access to Claude API (optional, has simulation fallbacks)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/TIMBOTGPT/mcp-macos-companion.git
   cd mcp-macos-companion
   ```

2. **Install dependencies**:
   ```bash
   pip3 install flask flask-cors requests --break-system-packages
   ```

3. **Start the services**:
   ```bash
   # Start service registry first
   python3 services/service_registry.py &
   
   # Start workflow orchestrator
   python3 services/workflow_orchestrator.py &
   
   # Start Claude bridge
   python3 services/simple_claude_bridge.py &
   ```

4. **Test the system**:
   ```bash
   # Test workflow trigger
   curl -X POST http://localhost:8084/trigger \
     -H "Content-Type: application/json" \
     -d '{"trigger_type": "voice_command", "trigger_data": {"command": "take a screenshot"}}'
   ```

### Service Status
Check if all services are running:
```bash
curl http://localhost:8081/services  # Service registry
curl http://localhost:8084/health    # Workflow orchestrator  
curl http://localhost:8092/health    # Claude bridge
```

## 📁 Project Structure

```
mcp-macos-companion/
├── services/                    # Core backend services
│   ├── workflow_orchestrator.py # Main workflow engine
│   ├── simple_claude_bridge.py  # Claude AI integration
│   ├── service_registry.py      # Service discovery
│   ├── memory_engine.py         # Context storage
│   └── ...                      # Additional services
├── workflows/                   # Workflow templates
├── tests/                       # Test scripts
└── README.md                    # This file
```

## 🎯 Key Features

### Intelligent Voice Commands
- **Context-Aware Processing**: Commands understood in natural language
- **Error-Tolerant Recognition**: Handles speech-to-text errors gracefully
- **Multi-Step Workflows**: Complex automation sequences from simple voice commands
- **Visual and Audio Feedback**: Comprehensive user feedback system

### Workflow Automation
- **Template System**: Reusable automation patterns
- **Dynamic Parameters**: Runtime value substitution
- **Service Orchestration**: Coordinates multiple backend services
- **Health Monitoring**: Automatic service health checking and recovery

### macOS Integration
- **AppleScript Control**: Deep system integration for window management
- **Notification System**: Native macOS notifications for operation feedback
- **Finder Integration**: Enhanced file and folder operations
- **System Service Monitoring**: Real-time service status tracking

## 🔗 Related Projects

This backend service works in conjunction with:
- **[MCP Companion Voice App](https://github.com/TIMBOTGPT/mcp-companion-voice-app)**: SwiftUI frontend with voice interface
- **Model Context Protocol**: Integration with MCP ecosystem
- **Claude AI**: Natural language processing capabilities

## 🛠️ Development

### Running in Development Mode
```bash
# Enable debug logging
export FLASK_ENV=development

# Run services with enhanced logging
python3 services/workflow_orchestrator.py
```

### Testing Voice Commands
```bash
# Test screenshot command
curl -X POST http://localhost:8092/process_command \
  -H "Content-Type: application/json" \
  -d '{"command": "take a screenshot"}'

# Test folder opening
curl -X POST http://localhost:8092/process_command \
  -H "Content-Type: application/json" \
  -d '{"command": "open nas raid"}'
```

### Adding New Voice Commands
1. Edit `simple_claude_bridge.py`
2. Add pattern matching in the `process_command` function
3. Implement the corresponding action function
4. Test with curl or the voice app frontend

## 🐛 Troubleshooting

### Common Issues

**Services not starting**:
- Check port availability: `lsof -i :8081-8092`
- Verify Python dependencies: `pip3 list | grep flask`
- Check logs for specific error messages

**Voice commands not working**:
- Ensure Claude bridge is running: `curl http://localhost:8092/health`
- Test direct API calls to isolate issues
- Check AppleScript permissions in System Settings

**Workflow orchestration failing**:
- Verify service registry is accessible: `curl http://localhost:8081/services`
- Check workflow templates for syntax errors
- Review orchestrator logs for parameter interpolation issues

## 📄 License

Private repository - All rights reserved.

## 🤝 Contributing

This is currently a private project. For collaboration opportunities, please contact the repository owner.

---

**Built with ❤️ for macOS automation and AI integration**
