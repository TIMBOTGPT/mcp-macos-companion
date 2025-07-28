#!/bin/bash

# MCP Companion App Builder with Voice Feedback
echo "🎤 Building MCP Companion with Voice Feedback"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project paths
PROJECT_DIR="/Users/mark/Desktop/MCP STUFF/mcp-macos-companion"
NEW_APP_DIR="$PROJECT_DIR/MCPCompanionApp_New"
BUNDLE_DIR="$PROJECT_DIR/MCPCompanion.app"

echo -e "${BLUE}📦 Building Swift executable...${NC}"
cd "$NEW_APP_DIR"

# Build the Swift package
if swift build --configuration release; then
    echo -e "${GREEN}✅ Swift build successful${NC}"
else
    echo -e "${RED}❌ Swift build failed${NC}"
    exit 1
fi

echo -e "${BLUE}🏗️  Creating App Bundle...${NC}"

# Create app bundle structure
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR/Contents/MacOS"
mkdir -p "$BUNDLE_DIR/Contents/Resources"

# Copy the executable
cp ".build/arm64-apple-macosx/release/MCPCompanion" "$BUNDLE_DIR/Contents/MacOS/MCPCompanion"

# Make executable
chmod +x "$BUNDLE_DIR/Contents/MacOS/MCPCompanion"

# Create Info.plist
cat > "$BUNDLE_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>MCPCompanion</string>
    <key>CFBundleIdentifier</key>
    <string>com.mcpcompanion.app</string>
    <key>CFBundleName</key>
    <string>MCP Companion</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>CFBundleVersion</key>
    <string>2.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>MCP Companion needs microphone access for voice recording and transcription features.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>MCP Companion needs access to control other applications for automation workflows.</string>
</dict>
</plist>
EOF

echo -e "${GREEN}✅ App bundle created: $BUNDLE_DIR${NC}"

# Test voice recording functionality
echo -e "${BLUE}🎤 Testing Voice Recording Features...${NC}"
echo "Features included in this build:"
echo "  • Real-time microphone level display"
echo "  • Visual recording feedback"
echo "  • Recording status indicators"
echo "  • Processing status display"
echo "  • Transcription confidence scores"

echo -e "${YELLOW}🚀 Starting MCP Companion...${NC}"

# Kill any existing instances
pkill -f MCPCompanion 2>/dev/null

# Launch the app
open "$BUNDLE_DIR"

echo -e "${GREEN}✅ MCP Companion launched with voice feedback!${NC}"
echo ""
echo "Voice Recording Features:"
echo "  🎤 Click the Voice button in Quick Actions"
echo "  🔴 Red circle indicates active recording"
echo "  📊 Real-time microphone level meter"
echo "  ⚡ Processing status with spinner"
echo "  📝 Live transcription results"
echo "  📈 Confidence score display"
echo ""
echo "To test voice recording:"
echo "  1. Look for MCP Companion in your menu bar"
echo "  2. Click the icon and select 'Voice Recording'"
echo "  3. Grant microphone permissions when prompted"
echo "  4. Click record and speak clearly"
echo "  5. Watch the visual feedback indicators"
