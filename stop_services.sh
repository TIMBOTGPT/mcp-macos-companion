#!/bin/bash
# MCP macOS Companion - Service Stop Script
# Gracefully stops all running services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping MCP macOS Companion Services${NC}"

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="/Users/mark/.mcp/logs/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        if kill -0 $pid 2>/dev/null; then
            echo -e "${YELLOW}Stopping ${service_name} (PID: ${pid})...${NC}"
            
            # Try graceful shutdown first
            kill -TERM $pid
            sleep 2
            
            # Check if still running
            if kill -0 $pid 2>/dev/null; then
                echo -e "${YELLOW}Force stopping ${service_name}...${NC}"
                kill -KILL $pid
                sleep 1
            fi
            
            # Verify stopped
            if ! kill -0 $pid 2>/dev/null; then
                echo -e "${GREEN}✅ ${service_name} stopped${NC}"
                rm "$pid_file"
            else
                echo -e "${RED}❌ Failed to stop ${service_name}${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  ${service_name} not running (stale PID file)${NC}"
            rm "$pid_file"
        fi
    else
        echo -e "${YELLOW}⚠️  No PID file found for ${service_name}${NC}"
    fi
}

# Stop services in reverse order
echo -e "${BLUE}🔧 Stopping services...${NC}"

stop_service "workflow_orchestrator"
stop_service "screen_vision"
stop_service "finder_actions" 
stop_service "memory_engine"
stop_service "service_registry"

# Kill any remaining Python processes that might be our services
echo -e "${YELLOW}🧹 Cleaning up any remaining processes...${NC}"

# Look for our specific service processes
pkill -f "service_registry.py" 2>/dev/null
pkill -f "memory_engine.py" 2>/dev/null  
pkill -f "finder_actions.py" 2>/dev/null
pkill -f "screen_vision.py" 2>/dev/null
pkill -f "workflow_orchestrator.py" 2>/dev/null

sleep 1

# Check for any services still running on our ports
echo -e "${BLUE}📊 Checking ports:${NC}"
for port in 8080 8081 8082 8083 8084; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}⚠️  Port $port still in use${NC}"
    else
        echo -e "${GREEN}✅ Port $port free${NC}"
    fi
done

echo ""
echo -e "${GREEN}🎉 Service shutdown complete!${NC}"
echo -e "${BLUE}📝 Logs preserved at: /Users/mark/.mcp/logs/${NC}"
echo ""
echo -e "${BLUE}🚀 To restart services:${NC}"
echo "./start_services.sh"
