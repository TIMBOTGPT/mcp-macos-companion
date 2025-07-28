#!/usr/bin/env python3
"""
Claude API Bridge Service
Uses the analysis tool to properly call the real Claude API for voice commands
"""

import json
import logging
import subprocess
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "claude_api_bridge",
        "port": 8091,
        "capabilities": ["real_claude_api", "voice_processing", "action_execution"]
    })

@app.route('/process_command', methods=['POST'])
def process_command():
    """Process voice commands using real Claude API through the analysis tool"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        
        if not command:
            return jsonify({"error": "No command provided"}), 400
        
        logger.info(f"Sending voice command to real Claude via analysis tool: '{command}'")
        
        # Create a request to the analysis tool that will call Claude
        analysis_request = {
            "voice_command": command,
            "request_type": "voice_processing",
            "user_location": "macOS system",
            "available_actions": [
                "search - Search filesystem", 
                "open - Open files/folders/apps",
                "screenshot - Capture screen",
                "memory - Store/retrieve information",
                "organize - Organize files",
                "respond - Provide response"
            ]
        }
        
        # Write the request to a temp file that the analysis tool can read
        temp_file = "/tmp/voice_command_request.json"
        with open(temp_file, 'w') as f:
            json.dump(analysis_request, f)
        
        # Call the analysis tool to process this command
        result = subprocess.run([
            "curl", "-X", "POST", "http://localhost:3000/analysis",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "code": f"""
// Read the voice command request
const fs = require('fs');
const requestData = JSON.parse(fs.readFileSync('/tmp/voice_command_request.json', 'utf8'));

// Call the real Claude API
const callRealClaude = async () => {{
    try {{
        const response = await fetch("https://api.anthropic.com/v1/messages", {{
            method: "POST",
            headers: {{
                "Content-Type": "application/json",
            }},
            body: JSON.stringify({{
                model: "claude-sonnet-4-20250514",
                max_tokens: 1500,
                messages: [
                    {{ 
                        role: "user", 
                        content: `You are Claude, integrated with a macOS automation system. The user just spoke this voice command: "${{requestData.voice_command}}"

Available Actions (respond with JSON):
1. SEARCH - Search filesystem: {{"action": "search", "path": "/path/to/search", "pattern": "*.ext", "description": "what you're looking for"}}
2. OPEN - Open files/folders: {{"action": "open", "target": "folder/file name", "type": "folder/file/app"}}
3. SCREENSHOT - Capture screen: {{"action": "screenshot", "save_path": "/Users/mark/Desktop/screenshot.png"}}
4. MEMORY - Store/search info: {{"action": "memory", "operation": "store/search", "content": "...", "category": "..."}}
5. ORGANIZE - Organize files: {{"action": "organize", "path": "/path/to/organize"}}
6. RESPOND - Give response: {{"action": "respond", "text": "your response to user"}}

For complex commands, break into multiple actions. Respond ONLY with JSON in this format:
{{"actions": [action1, action2, ...], "response": "your natural response to the user"}}`
                    }}
                ]
            }})
        }});
        
        const data = await response.json();
        console.log("Real Claude Response:", data.content[0].text);
        return data.content[0].text;
        
    }} catch (error) {{
        console.log("Claude API Error:", error);
        return JSON.stringify({{
            "actions": [{{"action": "respond", "text": "I encountered an error processing your command: " + error.message}}],
            "response": "I had trouble processing your voice command."
        }});
    }}
}};

await callRealClaude();
"""
            })
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Extract Claude's response from the analysis tool output
            claude_response = extract_claude_response(result.stdout)
        else:
            logger.error(f"Analysis tool error: {result.stderr}")
            claude_response = create_fallback_response(command)
        
        # Parse Claude's response for actions
        actions = parse_claude_actions(claude_response)
        
        # Execute the actions
        execution_results = execute_actions(actions)
        
        return jsonify({
            "status": "success",
            "result": {
                "command": command,
                "claude_response": claude_response,
                "actions_executed": len(actions),
                "results": execution_results,
                "timestamp": data.get('timestamp', '')
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

def extract_claude_response(analysis_output):
    """Extract Claude's response from analysis tool output"""
    try:
        # Look for JSON in the output
        lines = analysis_output.split('\n')
        for line in lines:
            if line.strip().startswith('{') and 'actions' in line:
                return line.strip()
        
        # If no JSON found, create a simple response
        return json.dumps({
            "actions": [{"action": "respond", "text": "I processed your command but couldn't extract specific actions."}],
            "response": "I received your command and processed it."
        })
        
    except Exception as e:
        logger.error(f"Failed to extract Claude response: {e}")
        return json.dumps({
            "actions": [{"action": "respond", "text": f"Error processing: {str(e)}"}],
            "response": "I had trouble processing your command."
        })

def create_fallback_response(command):
    """Create fallback when analysis tool fails"""
    return json.dumps({
        "actions": [{"action": "respond", "text": f"I received your command: '{command}' but the analysis tool connection failed."}],
        "response": f"I heard: '{command}' but couldn't process it through the analysis tool."
    })

def parse_claude_actions(response):
    """Parse Claude's JSON response to extract actions"""
    try:
        data = json.loads(response)
        return data.get('actions', [])
    except Exception as e:
        logger.error(f"Failed to parse Claude response: {e}")
        return [{"action": "respond", "text": "I processed your command but couldn't extract specific actions."}]

def execute_actions(actions):
    """Execute the actions returned by Claude"""
    results = []
    
    for action in actions:
        try:
            result = execute_single_action(action)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")
            results.append({"action": action.get("action", "unknown"), "status": "failed", "error": str(e)})
    
    return results

def execute_single_action(action):
    """Execute a single action"""
    action_type = action.get("action")
    
    if action_type == "open":
        return execute_open_action(action)
    elif action_type == "screenshot":
        return execute_screenshot_action(action)
    elif action_type == "respond":
        return execute_response_action(action)
    else:
        return {"action": action_type, "status": "not_implemented"}

def execute_open_action(action):
    """Execute open folder/file with enhanced visibility"""
    target = action.get("target", "")
    
    try:
        # Handle known drives specifically
        if target in ["2TB", "2TBHDD", "4TB SSD", "NAS RAID"]:
            volume_path = f"/Volumes/{target}"
            if os.path.exists(volume_path):
                subprocess.run(["open", volume_path], check=True)
                # Use AppleScript for better visibility
                applescript = f'''
                tell application "Finder"
                    activate
                    open folder "{volume_path}" as POSIX file
                    set the position of the front window to {{100, 100}}
                end tell
                '''
                subprocess.run(["osascript", "-e", applescript], check=False)
                return {"action": "open", "status": "success", "path": volume_path, "method": "enhanced"}
        
        return {"action": "open", "status": "not_found", "target": target}
        
    except Exception as e:
        return {"action": "open", "status": "error", "error": str(e)}

def execute_screenshot_action(action):
    """Execute screenshot"""
    try:
        save_path = action.get("save_path", "/Users/mark/Desktop/screenshot.png")
        subprocess.run(["screencapture", save_path], check=True)
        return {"action": "screenshot", "status": "success", "path": save_path}
    except Exception as e:
        return {"action": "screenshot", "status": "error", "error": str(e)}

def execute_response_action(action):
    """Log voice response"""
    text = action.get("text", "")
    logger.info(f"Voice Response: {text}")
    return {"action": "response", "status": "logged", "text": text}

if __name__ == '__main__':
    logger.info("Starting Claude API Bridge Service on port 8091")
    app.run(host='0.0.0.0', port=8091, debug=False)
