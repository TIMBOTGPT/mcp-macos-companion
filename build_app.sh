#!/bin/bash

# MCP Companion App Build & Launch Script

PROJECT_DIR="/Users/mark/Desktop/MCP STUFF/mcp-macos-companion"
APP_DIR="$PROJECT_DIR/MCPCompanionApp"
XCODE_PROJECT="$APP_DIR/MCPCompanionApp.xcodeproj"

echo "🚀 MCP Companion App Builder"
echo "============================="

# Check if backend services are running
echo "📡 Checking backend services..."
services=(8080 8081 8082 8083 8084 8085)
all_running=true

for port in "${services[@]}"; do
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ Service on port $port is running"
    else
        echo "❌ Service on port $port is NOT running"
        all_running=false
    fi
done

if [ "$all_running" = false ]; then
    echo ""
    echo "⚠️  Some backend services are not running!"
    echo "Would you like to start them? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "🔄 Starting backend services..."
        cd "$PROJECT_DIR"
        source venv/bin/activate
        python -m src.run_all_services &
        echo "⏳ Waiting for services to start..."
        sleep 5
    fi
fi

echo ""
echo "🏗️  Building SwiftUI App..."

# Open in Xcode for development
if [ "$1" = "xcode" ]; then
    echo "🖥️  Opening in Xcode..."
    open "$XCODE_PROJECT"
    exit 0
fi

# Build the app
if [ -d "$XCODE_PROJECT" ]; then
    echo "📦 Building MCP Companion..."
    cd "$APP_DIR"
    
    # Build using xcodebuild
    xcodebuild -project MCPCompanionApp.xcodeproj \
               -scheme "MCP Companion" \
               -configuration Debug \
               build
    
    if [ $? -eq 0 ]; then
        echo "✅ Build successful!"
        
        # Launch the app
        echo "🚀 Launching MCP Companion..."
        open "build/Debug/MCP Companion.app"
    else
        echo "❌ Build failed!"
        echo "💡 Try running: $0 xcode"
        echo "   This will open the project in Xcode for debugging"
    fi
else
    echo "❌ Xcode project not found!"
    echo "📁 Expected: $XCODE_PROJECT"
fi

echo ""
echo "🔧 Development Commands:"
echo "  $0           - Build and run app"
echo "  $0 xcode     - Open in Xcode"
echo "  $0 services  - Check service status"