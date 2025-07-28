#!/usr/bin/env python3
"""
Test script for MCP macOS Companion services
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path

# Test ports (avoiding common conflicts)
TEST_PORTS = {
    'service_registry': 8090,
    'memory_engine': 8091,
    'finder_actions': 8092,
    'screen_vision': 8093,
    'workflow_orchestrator': 8094,
    'whisper_client': 8095
}

def check_port(port):
    """Check if a port is available"""
    try:
        response = requests.get(f'http://localhost:{port}/health', timeout=2)
        return True
    except:
        return False

def test_basic_service(service_name, port):
    """Test a basic service"""
    print(f"\n🧪 Testing {service_name} on port {port}...")
    
    # Start service in background
    service_path = f"services/{service_name}.py"
    if not os.path.exists(service_path):
        print(f"❌ Service file not found: {service_path}")
        return False
    
    try:
        # Modify service to use test port
        modify_service_port(service_name, port)
        
        # Start service
        proc = subprocess.Popen([
            sys.executable, service_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for startup
        time.sleep(3)
        
        # Test health endpoint
        if check_port(port):
            print(f"✅ {service_name} is running on port {port}")
            proc.terminate()
            return True
        else:
            print(f"❌ {service_name} failed to start")
            proc.terminate()
            return False
            
    except Exception as e:
        print(f"❌ Error testing {service_name}: {e}")
        return False

def modify_service_port(service_name, port):
    """Temporarily modify service to use test port"""
    service_file = f"services/{service_name}.py"
    
    # Read the file
    with open(service_file, 'r') as f:
        content = f.read()
    
    # Create backup
    with open(f"{service_file}.backup", 'w') as f:
        f.write(content)
    
    # Replace port in main section
    if service_name == 'service_registry':
        content = content.replace('registry = ServiceRegistry(port=8080)', 
                                f'registry = ServiceRegistry(port={port})')
    elif service_name == 'memory_engine':
        content = content.replace('app.run(host="0.0.0.0", port=8081)', 
                                f'app.run(host="0.0.0.0", port={port})')
    # Add more replacements as needed
    
    # Write modified version
    with open(service_file, 'w') as f:
        f.write(content)

def restore_services():
    """Restore original service files"""
    for service_name in TEST_PORTS.keys():
        service_file = f"services/{service_name}.py"
        backup_file = f"{service_file}.backup"
        
        if os.path.exists(backup_file):
            with open(backup_file, 'r') as f:
                content = f.read()
            with open(service_file, 'w') as f:
                f.write(content)
            os.remove(backup_file)

def main():
    """Main test function"""
    print("🚀 MCP macOS Companion - Service Testing")
    print("=" * 50)
    
    # Change to project directory
    os.chdir('/Users/mark/Desktop/MCP STUFF/mcp-macos-companion')
    
    results = {}
    
    try:
        # Test each service
        for service_name, port in TEST_PORTS.items():
            results[service_name] = test_basic_service(service_name, port)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS:")
        print("=" * 50)
        
        for service_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{service_name:20} {status}")
        
        total_pass = sum(results.values())
        total_tests = len(results)
        print(f"\nPassed: {total_pass}/{total_tests}")
        
        if total_pass == total_tests:
            print("🎉 All services are working!")
        else:
            print("⚠️  Some services need attention")
    
    finally:
        # Restore original files
        restore_services()
        print("\n🔄 Original service files restored")

if __name__ == "__main__":
    main()
