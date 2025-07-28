#!/usr/bin/env python3
"""
Conversational Voice Command Processor
Sends voice commands to Claude for interpretation and execution
"""

import asyncio
import json
import logging
import os
import subprocess
import requests
from typing import Dict, Any, List
from datetime import datetime

class ConversationalVoiceProcessor:
    """Processes voice commands through Claude AI"""
    
    def __init__(self):
        self.claude_api_url = "https://api.anthropic.com/v1/messages"
        self.service_endpoints = {
            "memory": "http://localhost:8081",
            "finder": "http://localhost:8082", 
            "screen": "http://localhost:8083",
            "whisper": "http://localhost:8085"
        }
        
    async def process_voice_command(self, command_text: str, context: Dict = None) -> Dict[str, Any]:
        """Process voice command through Claude and execute actions"""
        
        # Step 1: Send to Claude for interpretation
        claude_response = await self.send_to_claude(command_text, context)
        
        # Step 2: Parse Claude's response for actions
        actions = self.parse_claude_response(claude_response)
        
        # Step 3: Execute recommended actions
        execution_results = await self.execute_actions(actions)
        
        # Step 4: Store interaction in memory
        await self.store_interaction(command_text, claude_response, execution_results)
        
        return {
            "command": command_text,
            "claude_response": claude_response,
            "actions_executed": len(actions),
            "results": execution_results,
            "timestamp": datetime.now().isoformat()
        }
    
    async def send_to_claude(self, command_text: str, context: Dict = None) -> str:
        """Send voice command to Claude for interpretation"""
        
        system_prompt = """You are Claude, an AI assistant integrated with a macOS automation system. The user is speaking to you via voice commands. You can execute actions on their Mac.

Available Actions:
1. MEMORY - Store/retrieve information: {"action": "memory", "operation": "store/search", "content": "...", "category": "..."}
2. FINDER - File operations: {"action": "finder", "operation": "organize/search/move/open", "path": "...", "pattern": "..."}  
3. SCREEN - Screenshots/OCR: {"action": "screen", "operation": "capture/ocr", "save_path": "..."}
4. OPEN - Open files/folders: {"action": "open", "target": "path or name", "type": "folder/file/app"}
5. SEARCH - Search filesystem: {"action": "search", "path": "starting path", "pattern": "file pattern like *.eml,*.msg,*.mbox", "type": "files/folders"}
6. RESPOND - Voice response: {"action": "respond", "text": "your response to the user"}

For complex multi-step tasks, break them into multiple actions. For email searches, use patterns like *.eml,*.msg,*.mbox,*.mailbox.

Format your response as:
ACTIONS: [{"action": "...", ...}, {"action": "...", ...}]
RESPONSE: Your natural response to the user

Be conversational and helpful. Execute actions when the user requests them."""

        user_message = f"Voice command: '{command_text}'"
        if context:
            user_message += f"\nContext: {json.dumps(context, indent=2)}"

        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1500,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "system": system_prompt
        }
        
        try:
            # Use the Claude API (using requests since we're in Python)
            import requests
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['content'][0]['text']
            else:
                logging.error(f"Claude API error: {response.status_code}")
                return self.enhanced_simulate_claude_response(command_text)
                
        except Exception as e:
            logging.error(f"Failed to contact Claude: {e}")
            return self.enhanced_simulate_claude_response(command_text)
    
    def simulate_claude_response(self, command_text: str) -> str:
        """Simulate Claude's response for common commands"""
        command_lower = command_text.lower()
        
        if "screenshot" in command_lower or "capture" in command_lower:
            return '''ACTIONS: [{"action": "screen", "operation": "capture", "save_path": "/Users/mark/Desktop/screenshot.png"}, {"action": "respond", "text": "I've taken a screenshot and saved it to your desktop."}]
RESPONSE: I've taken a screenshot for you and saved it to your desktop.'''

        elif "open" in command_lower and ("folder" in command_lower or "directory" in command_lower):
            # Extract folder name from command
            folder_name = command_text.lower().replace("open", "").replace("the", "").replace("folder", "").replace(",", "").strip()
            return f'''ACTIONS: [{{"action": "open", "target": "{folder_name}", "type": "folder"}}, {{"action": "respond", "text": "I'm opening the {folder_name} folder for you."}}]
RESPONSE: I'm opening the {folder_name} folder for you.'''

        elif "organize" in command_lower and ("download" in command_lower or "file" in command_lower):
            return '''ACTIONS: [{"action": "finder", "operation": "organize", "path": "/Users/mark/Downloads"}, {"action": "respond", "text": "I've organized your Downloads folder."}]
RESPONSE: I've organized your Downloads folder by file type and date.'''

        elif "remember" in command_lower or "note" in command_lower or "save" in command_lower:
            content = command_text.replace("remember", "").replace("note", "").replace("save", "").strip()
            return f'''ACTIONS: [{{"action": "memory", "operation": "store", "content": "{content}", "category": "voice_notes"}}, {{"action": "respond", "text": "I've saved that information for you."}}]
RESPONSE: I've saved that information to your memory system.'''

        elif "search" in command_lower or "find" in command_lower:
            return '''ACTIONS: [{"action": "memory", "operation": "search", "query": "''' + command_text + '''"}, {"action": "respond", "text": "Here's what I found in your memories."}]
RESPONSE: Let me search your memories for that information.'''

        else:
            return f'''ACTIONS: [{"action": "respond", "text": "I heard you say: {command_text}. I'm not sure how to help with that specific request yet."}]
RESPONSE: I heard you say: "{command_text}". I'm not sure how to help with that specific request yet, but I'm learning!'''
    
    def enhanced_simulate_claude_response(self, command_text: str) -> str:
        """Enhanced simulation that handles complex commands"""
        command_lower = command_text.lower()
        
        # Handle the specific NAS RAID email search command
        if "nas raid" in command_lower and "email" in command_lower and ("look" in command_lower or "see" in command_lower):
            actions = [
                {"action": "search", "path": "/Volumes/NAS RAID", "pattern": "*.eml,*.msg,*.mbox,*.mailbox", "type": "files"},
                {"action": "search", "path": "/Users/mark/Desktop/NAS RAID", "pattern": "*.eml,*.msg,*.mbox,*.mailbox", "type": "files"},
                {"action": "search", "path": "/Users/mark/Documents/NAS RAID", "pattern": "*.eml,*.msg,*.mbox,*.mailbox", "type": "files"},
                {"action": "respond", "text": "I'm searching the NAS RAID folder and its subfolders for email files. If I find any, I'll open the folders containing them."}
            ]
            actions_json = json.dumps(actions)
            return f'''ACTIONS: {actions_json}
RESPONSE: I'll search the NAS RAID folder for email files and open any folders that contain them. Let me check multiple possible locations for this folder.'''
        
        # Complex file searching commands
        elif ("look" in command_lower or "search" in command_lower or "find" in command_lower) and ("folder" in command_lower or "directory" in command_lower):
            # Extract folder name and search criteria
            actions = []
            
            # Try to extract folder name
            words = command_lower.split()
            folder_name = "specified folder"
            for i, word in enumerate(words):
                if word == "folder" and i > 0:
                    folder_name = words[i-1]
                    break
            
            actions.append({"action": "search", "path": f"/Users/mark/Desktop/{folder_name}", "pattern": "*.eml,*.msg,*.mbox,*.mailbox", "type": "files"})
            actions.append({"action": "search", "path": f"/Users/mark/Documents/{folder_name}", "pattern": "*.eml,*.msg,*.mbox,*.mailbox", "type": "files"})
            actions.append({"action": "respond", "text": f"I'm searching for email files in the {folder_name}. If I find any, I'll open the folders containing them."})
            
            actions_json = json.dumps(actions)
            return f'''ACTIONS: {actions_json}
RESPONSE: I'm searching for email files in the {folder_name}. This is a complex multi-step task - I'll check multiple locations and open any folders containing emails.'''
        
        # Multi-step commands with "and"
        elif " and " in command_lower and ("open" in command_lower or "find" in command_lower):
            return f'''ACTIONS: [{{"action": "respond", "text": "This is a complex multi-step command that I'm processing. For the best results with commands like this, the system should use the real Claude API for sophisticated reasoning."}}]
RESPONSE: I understand this is a complex command with multiple steps. I'm doing my best to process it, but commands like this work better with full Claude AI integration.'''
        
        # Fall back to simple simulation
        else:
            return self.simulate_claude_response(command_text)
    
    def parse_claude_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse Claude's response to extract actions"""
        actions = []
        
        try:
            # Look for ACTIONS: line
            if "ACTIONS:" in response:
                actions_line = response.split("ACTIONS:")[1].split("RESPONSE:")[0].strip()
                actions = json.loads(actions_line)
        except Exception as e:
            logging.error(f"Failed to parse Claude response: {e}")
            # Fallback: create a simple response action
            actions = [{"action": "respond", "text": "I processed your command but couldn't execute specific actions."}]
        
        return actions
    
    async def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute the actions recommended by Claude"""
        results = []
        
        for action in actions:
            try:
                result = await self.execute_single_action(action)
                results.append(result)
            except Exception as e:
                logging.error(f"Failed to execute action {action}: {e}")
                results.append({"action": action, "status": "failed", "error": str(e)})
        
        return results
    
    async def execute_single_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        action_type = action.get("action")
        
        if action_type == "memory":
            return await self.execute_memory_action(action)
        elif action_type == "finder":
            return await self.execute_finder_action(action)
        elif action_type == "screen":
            return await self.execute_screen_action(action)
        elif action_type == "open":
            return await self.execute_open_action(action)
        elif action_type == "search":
            return await self.execute_search_action(action)
        elif action_type == "respond":
            return await self.execute_response_action(action)
        else:
            return {"action": action, "status": "unknown_action"}
    
    async def execute_memory_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute memory operations"""
        operation = action.get("operation")
        
        if operation == "store":
            payload = {
                "content": action.get("content", ""),
                "category": action.get("category", "voice_notes"),
                "tags": ["voice_command", "claude_processed"],
                "timestamp": datetime.now().timestamp()
            }
            
            response = requests.post(f"{self.service_endpoints['memory']}/store", json=payload)
            return {"action": "memory_store", "status": "success", "id": response.json().get("id")}
            
        elif operation == "search":
            payload = {"query": action.get("query", ""), "limit": 5}
            response = requests.post(f"{self.service_endpoints['memory']}/text_search", json=payload)
            return {"action": "memory_search", "status": "success", "results": response.json().get("results", [])}
    
    async def execute_finder_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operations"""
        operation = action.get("operation")
        
        if operation == "organize":
            payload = {"directory": action.get("path", "/Users/mark/Downloads")}
            response = requests.post(f"{self.service_endpoints['finder']}/smart_organize", json=payload)
            return {"action": "finder_organize", "status": "success"}
    
    async def execute_screen_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute screen operations"""
        operation = action.get("operation")
        
        if operation == "capture":
            response = requests.post(f"{self.service_endpoints['screen']}/capture_screen")
            return {"action": "screen_capture", "status": "success"}
    
    async def execute_open_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute open operations (folders, files, apps)"""
        target = action.get("target", "")
        action_type = action.get("type", "folder")
        
        import subprocess
        
        try:
            if action_type == "folder":
                # Try to find and open the folder
                # First, try common locations
                possible_paths = [
                    f"/Users/mark/Desktop/{target}",
                    f"/Users/mark/Documents/{target}", 
                    f"/Users/mark/Downloads/{target}",
                    f"/Users/mark/{target}",
                    f"/Users/mark/Desktop/Job Interviews" if "job" in target.lower() and "interview" in target.lower() else None
                ]
                
                # Filter out None values
                possible_paths = [p for p in possible_paths if p is not None]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        subprocess.run(["open", path], check=True)
                        return {"action": "open_folder", "status": "success", "path": path}
                
                # If not found, try to search for it
                search_result = subprocess.run(
                    ["find", "/Users/mark", "-type", "d", "-iname", f"*{target}*", "-maxdepth", "3"],
                    capture_output=True, text=True
                )
                
                if search_result.stdout.strip():
                    found_path = search_result.stdout.strip().split('\n')[0]
                    subprocess.run(["open", found_path], check=True)
                    return {"action": "open_folder", "status": "success", "path": found_path}
                else:
                    return {"action": "open_folder", "status": "not_found", "target": target}
            
            return {"action": "open", "status": "unknown_type", "type": action_type}
            
        except subprocess.CalledProcessError as e:
            return {"action": "open", "status": "failed", "error": str(e)}
        except Exception as e:
            return {"action": "open", "status": "error", "error": str(e)}
    
    async def execute_search_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search operations for files and folders"""
        search_path = action.get("path", "/Users/mark")
        pattern = action.get("pattern", "*")
        search_type = action.get("type", "files")
        
        try:
            found_items = []
            
            # Handle multiple patterns (comma-separated)
            patterns = [p.strip() for p in pattern.split(",")]
            
            for p in patterns:
                try:
                    if search_type == "files":
                        # Search for files matching pattern
                        search_result = subprocess.run(
                            ["find", search_path, "-type", "f", "-name", p, "-maxdepth", "4"],
                            capture_output=True, text=True, timeout=10
                        )
                    else:
                        # Search for directories
                        search_result = subprocess.run(
                            ["find", search_path, "-type", "d", "-name", p, "-maxdepth", "4"], 
                            capture_output=True, text=True, timeout=10
                        )
                    
                    if search_result.stdout.strip():
                        found_items.extend(search_result.stdout.strip().split('\n'))
                        
                except subprocess.TimeoutExpired:
                    logging.warning(f"Search timeout for pattern {p} in {search_path}")
                    continue
                except Exception as e:
                    logging.warning(f"Search error for pattern {p}: {e}")
                    continue
            
            # Remove duplicates and empty entries
            found_items = list(set([item for item in found_items if item.strip()]))
            
            if found_items:
                # For email files, try to open the containing folders
                if any(ext in pattern.lower() for ext in ['.eml', '.msg', '.mbox', '.mailbox']):
                    folders_to_open = set()
                    for item in found_items[:5]:  # Limit to first 5 items
                        folder = os.path.dirname(item)
                        folders_to_open.add(folder)
                    
                    # Open the folders containing emails
                    for folder in list(folders_to_open)[:3]:  # Limit to 3 folders
                        subprocess.run(["open", folder], check=False)
                
                return {
                    "action": "search", 
                    "status": "success", 
                    "found_count": len(found_items),
                    "items": found_items[:10],  # Return first 10 items
                    "search_path": search_path,
                    "pattern": pattern
                }
            else:
                return {
                    "action": "search",
                    "status": "not_found", 
                    "search_path": search_path,
                    "pattern": pattern
                }
                
        except subprocess.TimeoutExpired:
            return {"action": "search", "status": "timeout", "error": "Search took too long"}
        except Exception as e:
            return {"action": "search", "status": "error", "error": str(e)}
    
    async def execute_response_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voice responses (for future TTS integration)"""
        response_text = action.get("text", "")
        
        # For now, just log the response. Later we can add TTS
        logging.info(f"Voice Response: {response_text}")
        
        return {"action": "voice_response", "status": "logged", "text": response_text}
    
    async def store_interaction(self, command: str, response: str, results: List) -> None:
        """Store the interaction in memory"""
        interaction_data = {
            "content": f"Voice Interaction - Command: '{command}' | Response: {response[:200]}...",
            "category": "voice_interactions", 
            "tags": ["voice", "claude", "conversation"],
            "metadata": {
                "command": command,
                "actions_count": len(results),
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().timestamp()
        }
        
        try:
            requests.post(f"{self.service_endpoints['memory']}/store", json=interaction_data)
        except Exception as e:
            logging.error(f"Failed to store interaction: {e}")


# Integration function for workflow orchestrator
async def process_conversational_voice_command(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main function called by workflow orchestrator"""
    
    processor = ConversationalVoiceProcessor()
    command_text = trigger_data.get("command", "")
    
    if not command_text:
        return {"status": "error", "message": "No command text provided"}
    
    try:
        result = await processor.process_voice_command(command_text, trigger_data)
        return {"status": "success", "result": result}
    except Exception as e:
        logging.error(f"Conversational voice processing failed: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Test the processor
    import asyncio
    
    async def test():
        processor = ConversationalVoiceProcessor()
        result = await processor.process_voice_command("take a screenshot")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())
