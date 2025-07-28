#!/bin/bash

# MCP Companion - Complete Installation Script

echo "🚀 Installing MCP Companion for Standalone Use"
echo "=============================================="

PROJECT_DIR="/Users/mark/Desktop/MCP STUFF/mcp-macos-companion"
PLIST_FILE="com.mcpcompanion.services.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

# Step 1: Build standalone app
echo ""
echo "📱 Step 1: Building standalone app..."
cd "$PROJECT_DIR"
./build_standalone.sh

# Step 2: Install launch agent for backend services
echo ""
echo "🔧 Step 2: Setting up auto-start for backend services..."

# Create logs directory
mkdir -p "$HOME/.mcp/logs"

# Copy launch agent
if [ ! -d "$LAUNCH_AGENTS_DIR" ]; then
    mkdir -p "$LAUNCH_AGENTS_DIR"
fi

cp "$PROJECT_DIR/$PLIST_FILE" "$LAUNCH_AGENTS_DIR/"

if [ $? -eq 0 ]; then
    echo "✅ Launch agent installed"
    
    # Load the launch agent
    launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ Backend services will now start automatically"
    else
        echo "⚠️  Launch agent created but not loaded (may need manual activation)"
    fi
else
    echo "❌ Failed to install launch agent"
fi

echo ""
echo "🎉 Installation Complete!"
echo "========================"
echo ""
echo "✅ What's now available:"
echo "   📱 MCP Companion app in /Applications/"
echo "   🤖 Backend services auto-start on login"
echo "   🧠 Menu bar icon appears when you launch the app"
echo ""
echo "🚀 To use:"
echo "   1. Open 'MCP Companion' from Applications"
echo "   2. The brain icon will appear in menu bar"
echo "   3. Backend services start automatically"
echo ""
echo "🔧 To uninstall auto-start:"
echo "   launchctl unload ~/Library/LaunchAgents/$PLIST_FILE"
echo "   rm ~/Library/LaunchAgents/$PLIST_FILE"
echo ""
echo "💡 Pro tip: Right-click the app in Applications and"
echo "   select 'Options > Open at Login' for full automation!"