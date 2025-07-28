#!/usr/bin/env python3
"""
Test script to verify the workflow orchestrator fix
"""

import json
import requests
import time

def test_workflow_trigger():
    """Test the corrected workflow trigger"""
    
    trigger_data = {
        "trigger_type": "voice_command",
        "trigger_data": {
            "command": "take a screenshot",
            "user_input": "take a screenshot", 
            "context": {"source": "test_script"},
            "timestamp": "2025-07-28T12:00:00Z"
        }
    }
    
    print("Testing workflow trigger with complete payload...")
    print(f"Payload: {json.dumps(trigger_data, indent=2)}")
    
    try:
        response = requests.post(
            "http://localhost:8084/trigger",
            json=trigger_data,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('triggered_workflows'):
                workflow_id = data['triggered_workflows'][0]['workflow_id']
                
                # Check workflow status
                print(f"\nChecking workflow status for {workflow_id}...")
                status_response = requests.get(f"http://localhost:8084/workflows/{workflow_id}/status")
                print(f"Status: {json.dumps(status_response.json(), indent=2)}")
                
                return True
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return False

def test_claude_service_directly():
    """Test the Claude service directly"""
    
    test_payload = {
        "command": "take a screenshot",
        "context": {"source": "direct_test"},
        "timestamp": "2025-07-28T12:00:00Z"
    }
    
    print("\nTesting Claude service directly...")
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

def main():
    print("🔧 Testing Workflow Orchestrator Fixes")
    print("=" * 50)
    
    # Test Claude service health
    try:
        health_response = requests.get("http://localhost:8092/health", timeout=5)
        print(f"Claude service health: {health_response.status_code}")
    except:
        print("❌ Claude service not responding on port 8092")
        return
    
    # Test orchestrator health 
    try:
        health_response = requests.get("http://localhost:8084/health", timeout=5)
        print(f"Orchestrator health: {health_response.status_code}")
    except:
        print("❌ Orchestrator not responding on port 8084")
        return
    
    # Test Claude service directly
    if test_claude_service_directly():
        print("✅ Claude service direct test PASSED")
    else:
        print("❌ Claude service direct test FAILED")
    
    # Test workflow trigger
    print("\n" + "=" * 50)
    if test_workflow_trigger():
        print("✅ Workflow trigger test PASSED")
        print("\n🎉 FIX SUCCESSFUL! Workflow orchestrator is now working correctly.")
    else:
        print("❌ Workflow trigger test FAILED")

if __name__ == "__main__":
    main()
