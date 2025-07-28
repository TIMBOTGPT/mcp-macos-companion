#!/bin/bash

# MCP Companion - Build Standalone App

echo "🏗️  Building MCP Companion as standalone app..."

PROJECT_DIR="/Users/mark/Desktop/MCP STUFF/mcp-macos-companion"
APP_DIR="$PROJECT_DIR/MCPCompanionApp"
BUILD_DIR="$APP_DIR/Build"

cd "$APP_DIR"

# Build the app for release
echo "📦 Building release version..."
xcodebuild -project MCPCompanionApp.xcodeproj \
           -scheme "MCP Companion" \
           -configuration Release \
           -derivedDataPath "$BUILD_DIR" \
           build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    
    # Find the built app
    BUILT_APP=$(find "$BUILD_DIR" -name "MCP Companion.app" -type d | head -1)
    
    if [ -n "$BUILT_APP" ]; then
        echo "📱 App built at: $BUILT_APP"
        
        # Copy to Applications folder
        echo "📂 Installing to Applications folder..."
        cp -R "$BUILT_APP" "/Applications/"
        
        if [ $? -eq 0 ]; then
            echo "🎉 MCP Companion installed to /Applications/"
            echo ""
            echo "✅ You can now:"
            echo "   1. Find 'MCP Companion' in Applications folder"
            echo "   2. Double-click to launch"
            echo "   3. Add to Dock for easy access"
            echo "   4. Set to launch at login in app preferences"
            echo ""
            echo "🧠 The brain icon will appear in your menu bar!"
        else
            echo "❌ Failed to copy to Applications"
            echo "💡 You can manually copy from: $BUILT_APP"
        fi
    else
        echo "❌ Could not find built app"
    fi
else
    echo "❌ Build failed!"
    echo "💡 Try building in Xcode first to check for errors"
fi