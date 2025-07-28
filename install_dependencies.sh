#!/bin/bash
# MCP macOS Companion - Dependency Installation Script
# Installs all required dependencies for macOS

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 MCP macOS Companion - Installing Dependencies${NC}"
echo ""

# Check macOS version
macos_version=$(sw_vers -productVersion)
echo -e "${BLUE}🍎 macOS Version: ${macos_version}${NC}"

# Check architecture
arch=$(uname -m)
echo -e "${BLUE}🏗️  Architecture: ${arch}${NC}"
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}🍺 Homebrew not found. Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for current session
    if [[ "$arch" == "arm64" ]]; then
        export PATH="/opt/homebrew/bin:$PATH"
    else
        export PATH="/usr/local/bin:$PATH"
    fi
else
    echo -e "${GREEN}✅ Homebrew found${NC}"
fi

# Update Homebrew
echo -e "${YELLOW}🔄 Updating Homebrew...${NC}"
brew update

# Install system dependencies
echo -e "${BLUE}🔧 Installing system dependencies...${NC}"

# Python 3 (if not already installed)
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}🐍 Installing Python 3...${NC}"
    brew install python@3.11
else
    echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${NC}"
fi

# Tesseract for OCR
if ! command -v tesseract &> /dev/null; then
    echo -e "${YELLOW}👁️  Installing Tesseract OCR...${NC}"
    brew install tesseract
else
    echo -e "${GREEN}✅ Tesseract found: $(tesseract --version | head -1)${NC}"
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 not found. Installing...${NC}"
    python3 -m ensurepip --upgrade
fi

# Install Python dependencies
echo -e "${BLUE}🐍 Installing Python dependencies...${NC}"

# Set working directory to project root
cd "/Users/mark/Desktop/MCP STUFF/mcp-macos-companion"

# Upgrade pip first
python3 -m pip install --upgrade pip

# Install from requirements.txt
echo -e "${YELLOW}📋 Installing from requirements.txt...${NC}"
pip3 install -r requirements.txt

# Additional macOS-specific installations
echo -e "${BLUE}🍎 Installing macOS-specific packages...${NC}"

# For Apple Silicon optimizations
if [[ "$arch" == "arm64" ]]; then
    echo -e "${BLUE}🚀 Apple Silicon detected - installing MPS optimizations...${NC}"
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Verify installations
echo -e "${BLUE}🔍 Verifying installations...${NC}"

python3 -c "
import sys
packages = [
    'flask', 'flask_cors', 'requests', 'numpy', 
    'sentence_transformers', 'faiss', 'watchdog',
    'cv2', 'pytesseract', 'PIL'
]

all_good = True
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError as e:
        print(f'❌ {pkg} - {e}')
        all_good = False

if all_good:
    print('\\n🎉 All Python packages installed successfully!')
else:
    print('\\n⚠️  Some packages failed to install')
    sys.exit(1)
"

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p /Users/mark/.mcp/logs
mkdir -p /Users/mark/.mcp/screenshots
mkdir -p /Users/mark/.mcp/data

echo -e "${GREEN}✅ Directories created:${NC}"
echo "  - /Users/mark/.mcp/logs"
echo "  - /Users/mark/.mcp/screenshots" 
echo "  - /Users/mark/.mcp/data"

# Set permissions
echo -e "${BLUE}🔐 Setting permissions...${NC}"
chmod +x start_services.sh
chmod +x stop_services.sh

echo ""
echo -e "${GREEN}🎉 Installation complete!${NC}"
echo ""
echo -e "${BLUE}🚀 Next steps:${NC}"
echo "1. Start services: ./start_services.sh"
echo "2. Check status:   curl http://localhost:8080/health"
echo "3. Stop services:  ./stop_services.sh"
echo ""
echo -e "${BLUE}📝 Logs will be available at:${NC}"
echo "/Users/mark/.mcp/logs/"
