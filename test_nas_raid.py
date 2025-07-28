#!/usr/bin/env python3
"""
Test script to find NAS RAID folder and test opening
"""

import json
import requests
import subprocess
import os

def check_mounted_volumes():
    """Check what volumes are mounted"""
    print("🔍 Checking mounted volumes:")
    if os.path.exists("/Volumes"):
        for item in os.listdir("/Volumes"):
            volume_path = f"/Volumes/{item}"
            if os.path.isdir(volume_path):
                print(f"  📁 {volume_path}")
    
    print("\n🔍 Checking Desktop for NAS RAID:")
    desktop_path = "/Users/mark/Desktop"
    if os.path.exists(desktop_path):
        for item in os.listdir(desktop_path):
            if "nas" in item.lower() or "raid" in item.lower():
                print(f"  📁 {desktop_path}/{item}")

def test_nas_raid_command():
    """Test the NAS RAID opening command"""
    
    test_payload = {
        "command": "open nas raid folder",
        "context": {"source": "test_script"},
        "timestamp": "2025-07-28T12:00:00Z"
    }
    
    print("🧪 Testing 'open nas raid folder' command...")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    
    try:
        response = requests.post(
            "http://localhost:8092/process_command",
            json=test_payload,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_workflow_trigger():
    """Test via workflow orchestrator"""
    
    trigger_data = {
        "trigger_type": "voice_command",
        "trigger_data": {
            "command": "open nas raid folder",
            "user_input": "open nas raid folder", 
            "context": {"source": "test_script"},
            "timestamp": "2025-07-28T12:00:00Z"
        }
    }
    
    print("\n🧪 Testing via workflow orchestrator...")
    
    try:
        response = requests.post(
            "http://localhost:8084/trigger",
            json=trigger_data,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("🔧 Testing NAS RAID Folder Opening")
    print("=" * 50)
    
    check_mounted_volumes()
    
    print("\n" + "=" * 50)
    
    if test_nas_raid_command():
        print("✅ Direct Claude service test PASSED")
    else:
        print("❌ Direct Claude service test FAILED")
    
    if test_workflow_trigger():
        print("✅ Workflow trigger test PASSED")
    else:
        print("❌ Workflow trigger test FAILED")

if __name__ == "__main__":
    main()
