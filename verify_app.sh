#!/bin/bash

# MCP Companion App - File Structure Verification

PROJECT_DIR="/Users/mark/Desktop/MCP STUFF/mcp-macos-companion"
APP_DIR="$PROJECT_DIR/MCPCompanionApp"

echo "🔍 MCP Companion App - File Verification"
echo "========================================"

# Check if main project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Project directory not found: $PROJECT_DIR"
    exit 1
fi

echo "✅ Project directory found"

# Check SwiftUI app directory
if [ ! -d "$APP_DIR" ]; then
    echo "❌ App directory not found: $APP_DIR"
    exit 1
fi

echo "✅ App directory found"

# List of required SwiftUI files
swift_files=(
    "MCPCompanionApp.swift"
    "ServiceMonitor.swift"
    "MenuBarContentView.swift"
    "ServiceStatusView.swift"
    "QuickActionsView.swift"
    "ActionComponents.swift"
    "WorkflowsView.swift"
    "WorkflowModels.swift"
    "WorkflowEditView.swift"
    "PreferencesView.swift"
)

echo ""
echo "📱 Checking SwiftUI source files..."

missing_files=0
for file in "${swift_files[@]}"; do
    file_path="$APP_DIR/$file"
    if [ -f "$file_path" ]; then
        lines=$(wc -l < "$file_path")
        echo "✅ $file ($lines lines)"
    else
        echo "❌ Missing: $file"
        ((missing_files++))
    fi
done

# Check Xcode project
echo ""
echo "🏗️  Checking Xcode project..."

if [ -f "$APP_DIR/MCPCompanionApp.xcodeproj/project.pbxproj" ]; then
    echo "✅ Xcode project file found"
else
    echo "❌ Xcode project file missing"
    ((missing_files++))
fi

if [ -f "$APP_DIR/MCPCompanionApp.entitlements" ]; then
    echo "✅ Entitlements file found"
else
    echo "❌ Entitlements file missing"
    ((missing_files++))
fi

# Check build script
echo ""
echo "⚙️  Checking build tools..."

if [ -f "$PROJECT_DIR/build_app.sh" ]; then
    if [ -x "$PROJECT_DIR/build_app.sh" ]; then
        echo "✅ Build script found and executable"
    else
        echo "⚠️  Build script found but not executable"
        echo "   Run: chmod +x \"$PROJECT_DIR/build_app.sh\""
    fi
else
    echo "❌ Build script missing"
    ((missing_files++))
fi

# Check documentation
if [ -f "$APP_DIR/README.md" ]; then
    echo "✅ README documentation found"
else
    echo "❌ README documentation missing"
    ((missing_files++))
fi

# Backend service verification
echo ""
echo "🔗 Checking backend services..."

backend_running=0
services=(8080 8081 8082 8083 8084 8085)
service_names=("Service Registry" "Memory Engine" "Finder Actions" "Screen Vision" "Workflow Orchestrator" "Whisper Client")

for i in "${!services[@]}"; do
    port=${services[$i]}
    name=${service_names[$i]}
    
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $name (port $port) - Running"
        ((backend_running++))
    else
        echo "❌ $name (port $port) - Not running"
    fi
done

# Summary
echo ""
echo "📊 SUMMARY"
echo "=========="

if [ $missing_files -eq 0 ]; then
    echo "✅ All SwiftUI app files are present!"
else
    echo "❌ $missing_files file(s) missing from SwiftUI app"
fi

echo "🔧 Backend services: $backend_running/6 running"

if [ $backend_running -lt 6 ]; then
    echo ""
    echo "💡 To start backend services:"
    echo "   cd \"$PROJECT_DIR\""
    echo "   source venv/bin/activate"
    echo "   python -m src.run_all_services"
fi

echo ""
echo "🚀 Next steps:"
echo "   1. Start backend services (if not running)"
echo "   2. Run: ./build_app.sh xcode"
echo "   3. Build and test in Xcode"
echo "   4. Run: ./build_app.sh (to build and launch)"

echo ""
echo "🎯 Development commands:"
echo "   ./build_app.sh           - Build and run app"
echo "   ./build_app.sh xcode     - Open in Xcode"
echo "   $0                       - Run this verification again"