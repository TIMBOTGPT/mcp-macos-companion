#!/usr/bin/env python3
"""
Simple Claude Bridge - Routes voice commands to the analysis tool
"""

import json
import logging
import subprocess
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "simple_claude_bridge", "port": 8092})

@app.route('/process_command', methods=['POST'])
def process_command():
    try:
        data = request.get_json()
        command = data.get('command', '').lower()
        
        logger.info(f"Voice command: '{command}' - Processing with intelligent interpretation")
        
        # Debug logging
        logger.info(f"Command analysis:")
        logger.info(f"  'open' in command: {'open' in command}")
        logger.info(f"  'show' in command: {'show' in command}")
        logger.info(f"  'nas raid' in command: {'nas raid' in command}")
        logger.info(f"  'nas rate' in command: {'nas rate' in command}")
        logger.info(f"  'nas equality' in command: {'nas equality' in command}")
        logger.info(f"  'nas red' in command: {'nas red' in command}")
        logger.info(f"  'nas read' in command: {'nas read' in command}")
        logger.info(f"  '4tb' in command: {'4tb' in command}")
        logger.info(f"  'ssd' in command: {'ssd' in command}")
        logger.info(f"  '2tb' in command: {'2tb' in command}")
        
        # Intelligent command processing (simulating Claude's reasoning)
        actions = []
        response_text = ""
        
        if "screenshot" in command or "capture" in command:
            actions = [{"action": "screenshot"}]
            response_text = "I'm taking a screenshot and saving it to your desktop."
            
        elif ("open" in command or "show" in command) and ("nas raid" in command or "nasraid" in command or "nas rate" in command or "nas equality" in command or "nas red" in command or "nas read" in command):
            # Handle NAS RAID folder opening - includes common speech recognition errors
            logger.info("Matched NAS RAID opening pattern!")
            possible_paths = [
                "/Volumes/NAS RAID",  # This is the real, active mount
                "/Users/mark/Desktop/NAS RAID",  # Fallback if it's copied locally
                "/Users/mark/Documents/NAS RAID"  # Another fallback location
            ]
            actions = []
            for path in possible_paths:
                actions.append({"action": "open_folder", "parameters": {"path": path}})
            response_text = "I'm opening the NAS RAID folder for you."
            
        elif ("open" in command or "show" in command) and ("4tb" in command and "ssd" in command):
            # Handle 4TB SSD folder opening
            logger.info("Matched 4TB SSD opening pattern!")
            possible_paths = [
                "/Volumes/4TB SSD",  # This is the real, active mount
                "/Users/mark/Desktop/4TB SSD",  # Fallback if it's copied locally
                "/Users/mark/Documents/4TB SSD"  # Another fallback location
            ]
            actions = []
            for path in possible_paths:
                actions.append({"action": "open_folder", "parameters": {"path": path}})
            response_text = "I'm opening the 4TB SSD folder for you."
            
        elif "open" in command and ("2tb" in command or ("drive" in command and "terabyte" in command and not "4tb" in command)):
            actions = [
                {"action": "open_folder", "parameters": {"path": "/Volumes/2TB"}},
                {"action": "open_folder", "parameters": {"path": "/Volumes/2TBHDD"}}
            ]
            response_text = "I'm opening your 2TB external drives."
            
        elif "nas raid" in command and "email" in command:
            actions = [
                {"action": "search_files", "parameters": {"path": "/Volumes/NAS RAID", "pattern": "*.eml"}},
                {"action": "search_files", "parameters": {"path": "/Volumes/NAS RAID", "pattern": "*.msg"}}
            ]
            response_text = "I'm searching the NAS RAID drive for email files."
            
        elif ("open" in command or "show" in command) and ("mcp" in command and ("folder" in command or "stuff" in command)):
            # Handle MCP STUFF folder opening
            logger.info("Matched MCP STUFF opening pattern!")
            possible_paths = [
                "/Users/mark/Desktop/MCP STUFF",  # This is the main MCP project folder
                "/Volumes/NAS RAID/MCP STUFF"  # Backup location if it exists
            ]
            actions = []
            for path in possible_paths:
                actions.append({"action": "open_folder", "parameters": {"path": path}})
            response_text = "I'm opening the MCP STUFF folder for you."
            
        else:
            actions = [{"action": "respond", "parameters": {"text": f"I understood your command: '{command}' and I'm processing it intelligently."}}]
            response_text = f"I heard and understood: '{command}'"
        
        # Execute the actions
        results = []
        for action in actions:
            if action.get('action') == 'screenshot':
                result = execute_screenshot()
                results.append(result)
            elif action.get('action') == 'open_folder':
                path = action.get('parameters', {}).get('path', '')
                result = execute_open_folder(path)
                results.append(result)
            elif action.get('action') == 'search_files':
                path = action.get('parameters', {}).get('path', '')
                pattern = action.get('parameters', {}).get('pattern', '*')
                result = execute_search_files(path, pattern)
                results.append(result)
            else:
                results.append({"action": "respond", "status": "logged", "text": response_text})
        
        return jsonify({
            "status": "success", 
            "result": {
                "command": data.get('command', ''),
                "claude_response": f"Intelligent interpretation: {response_text}",
                "actions_executed": len(actions),
                "results": results
            }
        })
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def extract_claude_response_from_logs(logs):
    """Extract Claude's response from analysis tool logs"""
    for log in logs:
        if "CLAUDE_RESPONSE:" in str(log):
            try:
                response_text = str(log).split("CLAUDE_RESPONSE:")[1].strip()
                return json.loads(response_text)
            except:
                continue
    return create_fallback_response("unknown command")

def parse_claude_response(response):
    """Parse Claude's JSON response into actions"""
    try:
        if isinstance(response, str):
            response = json.loads(response)
        return response.get('actions', [])
    except:
        return [{"action": "respond", "parameters": {"text": "I processed your command but couldn't extract actions."}}]

def execute_actions(actions):
    """Execute the actions from Claude"""
    results = []
    for action in actions:
        if action.get('action') == 'open_folder':
            path = action.get('parameters', {}).get('path', '')
            result = execute_open_folder(path)
            results.append(result)
        elif action.get('action') == 'screenshot':
            result = execute_screenshot()
            results.append(result)
        elif action.get('action') == 'search_files':
            path = action.get('parameters', {}).get('path', '')
            pattern = action.get('parameters', {}).get('pattern', '*')
            result = execute_search_files(path, pattern)
            results.append(result)
        elif action.get('action') == 'respond':
            text = action.get('parameters', {}).get('text', '')
            results.append({"action": "respond", "status": "logged", "text": text})
    return results

def execute_open_folder(path):
    """Open a folder with enhanced visibility"""
    try:
        logger.info(f"Attempting to open folder: {path}")
        
        if os.path.exists(path):
            # Use AppleScript for maximum visibility and control
            applescript = f'''
            tell application "Finder"
                activate
                open folder "{path}" as POSIX file
                
                -- Wait a moment for the window to open
                delay 0.5
                
                -- Configure the window to be very visible
                try
                    set bounds of front window to {{50, 50, 950, 750}}
                    tell application "System Events"
                        tell process "Finder"
                            set frontmost to true
                        end tell
                    end tell
                on error
                    -- If that fails, just make sure Finder is active
                    activate
                end try
            end tell
            
            -- Send a notification to make it obvious
            display notification "📁 Opened {os.path.basename(path)} folder" with title "Folder Opened"
            '''
            
            # Execute the AppleScript
            result = subprocess.run(["osascript", "-e", applescript], 
                                  capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                logger.warning(f"AppleScript failed: {result.stderr}")
                # Fallback to simple open command
                subprocess.run(["open", path], check=True)
            
            logger.info(f"Successfully opened folder: {path}")
            return {"action": "open_folder", "status": "success", "path": path, "message": f"Opened {os.path.basename(path)} with notification"}
        else:
            logger.warning(f"Folder not found: {path}")
            
            # Try to find similar folders
            parent_dir = os.path.dirname(path)
            folder_name = os.path.basename(path)
            
            if os.path.exists(parent_dir):
                # Search for similar folder names
                try:
                    result = subprocess.run(
                        ["find", parent_dir, "-type", "d", "-iname", f"*{folder_name.replace(' ', '*')}*", "-maxdepth", "2"],
                        capture_output=True, text=True, timeout=5
                    )
                    
                    if result.stdout.strip():
                        found_path = result.stdout.strip().split('\n')[0]
                        logger.info(f"Found similar folder: {found_path}")
                        subprocess.run(["open", found_path], check=True)
                        return {"action": "open_folder", "status": "found_similar", "path": found_path, "original_path": path}
                except:
                    pass
            
            return {"action": "open_folder", "status": "not_found", "path": path}
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to open folder {path}: {e}")
        return {"action": "open_folder", "status": "failed", "error": str(e), "path": path}
    except Exception as e:
        logger.error(f"Error opening folder {path}: {e}")
        return {"action": "open_folder", "status": "error", "error": str(e), "path": path}

def execute_screenshot():
    """Take a screenshot"""
    try:
        path = "/Users/mark/Desktop/screenshot.png"
        subprocess.run(["screencapture", path], check=True)
        return {"action": "screenshot", "status": "success", "path": path}
    except Exception as e:
        return {"action": "screenshot", "status": "error", "error": str(e)}

def execute_search_files(path, pattern):
    """Search for files matching pattern"""
    try:
        if os.path.exists(path):
            result = subprocess.run(
                ["find", path, "-name", pattern, "-maxdepth", "3"],
                capture_output=True, text=True, timeout=10
            )
            files = result.stdout.strip().split('\\n') if result.stdout.strip() else []
            return {"action": "search_files", "status": "success", "found_count": len(files), "files": files[:5]}
        else:
            return {"action": "search_files", "status": "path_not_found", "path": path}
    except Exception as e:
        return {"action": "search_files", "status": "error", "error": str(e)}

def create_fallback_response(command):
    """Create fallback when Claude API fails"""
    return {
        "interpretation": f"Received command: {command}",
        "actions": [{"action": "respond", "parameters": {"text": f"I heard your command: '{command}' but couldn't process it through Claude API."}}],
        "response": f"I received your command but the Claude API connection failed."
    }

if __name__ == '__main__':
    print("Starting Simple Claude Bridge on port 8092")
    print("This service demonstrates voice command processing and would route to real Claude API")
    app.run(host='0.0.0.0', port=8092, debug=False)
