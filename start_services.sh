#!/bin/bash
# MCP macOS Companion - Service Startup Script
# Starts all services in the correct order

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting MCP macOS Companion Services${NC}"

# Set working directory
cd "/Users/mark/Desktop/MCP STUFF/mcp-macos-companion"

# Activate virtual environment
echo -e "${YELLOW}🐍 Activating virtual environment...${NC}"
source venv/bin/activate

# Change to services directory
cd services

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

# Check basic dependencies (skip ML libraries for now)
echo -e "${YELLOW}📦 Checking dependencies...${NC}"
python3 -c "import flask, requests, numpy, watchdog" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Some dependencies missing. Please check virtual environment setup${NC}"
    exit 1
fi

# Create necessary directories
mkdir -p /Users/mark/.mcp/logs
mkdir -p /Users/mark/.mcp/screenshots

# Function to start a service
start_service() {
    local service_name=$1
    local service_file=$2
    local port=$3
    
    echo -e "${BLUE}Starting ${service_name} on port ${port}...${NC}"
    
    # Check if port is already in use
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        echo -e "${YELLOW}⚠️  Port ${port} already in use, skipping ${service_name}${NC}"
        return
    fi
    
    # Start service in background
    python3 $service_file > "/Users/mark/.mcp/logs/${service_name}.log" 2>&1 &
    local pid=$!
    
    # Wait a moment for service to start
    sleep 2
    
    # Check if service is running
    if kill -0 $pid 2>/dev/null; then
        echo -e "${GREEN}✅ ${service_name} started (PID: ${pid})${NC}"
        echo $pid > "/Users/mark/.mcp/logs/${service_name}.pid"
    else
        echo -e "${RED}❌ Failed to start ${service_name}${NC}"
        echo -e "${RED}Check log: /Users/mark/.mcp/logs/${service_name}.log${NC}"
    fi
}

# Start services in order
echo -e "${BLUE}🔧 Starting core services...${NC}"

start_service "service_registry" "service_registry.py" 8080
echo -e "${YELLOW}⏳ Waiting for service registry to initialize...${NC}"
sleep 3

start_service "memory_engine" "memory_engine.py" 8081
sleep 2

start_service "finder_actions" "finder_actions.py" 8082
sleep 2

start_service "screen_vision" "screen_vision.py" 8083
sleep 2

start_service "workflow_orchestrator" "workflow_orchestrator.py" 8084
sleep 2

start_service "whisper_client" "whisper_client.py" 8085
sleep 2

echo -e "${GREEN}🎉 Service startup complete!${NC}"
echo ""
echo -e "${BLUE}📊 Service Status:${NC}"
echo "Service Registry:     http://localhost:8080/health"
echo "Memory Engine:        http://localhost:8081/health"  
echo "Finder Actions:       http://localhost:8082/health"
echo "Screen Vision:        http://localhost:8083/health"
echo "Workflow Orchestrator: http://localhost:8084/health"
echo "Whisper Client:       http://localhost:8085/health"
echo ""
echo -e "${BLUE}📝 Logs available at:${NC}"
echo "/Users/mark/.mcp/logs/"
echo ""
echo -e "${BLUE}🛑 To stop services:${NC}"
echo "./stop_services.sh"
