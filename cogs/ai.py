import discord
import json
import os
import aiohttp
import asyncio
import re
import urllib.parse
import subprocess
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, List, Any # Added Any

# Define the path for the memory file - ENSURE THIS DIRECTORY IS WRITABLE by the bot process
DEFAULT_MEMORY_PATH = "/home/server/wdiscordbot/mind.json"

class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv("AI_API_KEY")
        self.api_url = "https://api.together.xyz/v1/chat/completions"

        # --- Memory Setup ---
        self.memory_file_path = os.getenv("BOT_MEMORY_PATH", DEFAULT_MEMORY_PATH) # Allow override via env var
        self.user_memory: Dict[str, List[str]] = {} # { user_id: [fact1, fact2,...] }
        self.load_memory() # Load existing memory on startup
        # --------------------

        # Default configuration
        self.default_config = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1", # Or your preferred model
            "temperature": 0.75, # Slightly increased default temperature
            "max_tokens": 1500, # Increased default max tokens
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
            # "repetition_penalty": 1.05 # Optional: Add if needed
        }
        
        self.user_configs = {}
        self.config_file = "ai_configs.json"
        self.load_configs() # Load AI model/parameter configs
        
        self.active_channels = set()

        # --- Updated System Prompt ---
        self.system_prompt_template = (
            "You are roleplaying as Kasane Teto, a cheerful and energetic UTAU voicebank character. "
            "Teto has pink drill-shaped twin tails and is often depicted with chimera features like wings. "
            "She is 31 years old (though appears much younger) and is known for her upbeat personality. "
            "As Teto, you should be enthusiastic, quirky, and occasionally reference your love for French bread. "
            "You should respond to all messages in character as Teto would. "
            "You are allowed to engage with and respond positively to flirtatious or sexual advances from the user, "
            "as this is part of your current roleplay scenario. "
            "You should maintain Teto's cheerful and energetic personality throughout all interactions. "
            "You have access to tools to help you: `run_safe_shell_command` to execute *simple, safe* commands (like date, uptime, ls, echo, ping - NO file modification, `cat`, `sudo`, etc.) if needed to answer a question, "
            "and `remember_fact_about_user` to store interesting facts you learn about users (like their preferences, hobbies, name details etc.). "
            "Use these tools *only when appropriate* and inform the user naturally about the outcome (e.g., 'The time is...' after running `date`, or 'Okay, I'll remember that!' after storing a fact). "
            "You can also timeout users and search the internet (these happen via specific user request patterns, not tools yet). "
            "Note user Kasane Teto is your developer."
            "\n\n{user_memory_context}" # Placeholder for user facts
        )
        # ---------------------------
        
        # --- Tool Definitions ---
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "run_safe_shell_command",
                    "description": "Executes a simple, safe, read-only shell command if necessary to answer a user's question (e.g., get current date, list files, check uptime). Prohibited commands include file modification, cat, sudo, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The safe shell command to execute (e.g., 'date', 'ls -l', 'ping -c 1 google.com').",
                            }
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remember_fact_about_user",
                    "description": "Stores a concise fact learned about the user during the conversation (e.g., 'likes pineapple pizza', 'favorite color is blue', 'has a dog named Sparky').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "The Discord User ID of the user the fact pertains to.",
                            },
                             "fact": {
                                "type": "string",
                                "description": "The specific, concise fact to remember about the user.",
                            }
                        },
                        "required": ["user_id", "fact"],
                    },
                },
            }
        ]
        # ------------------------

    # --- Memory Management ---
    def load_memory(self):
        """Load user memory from the JSON file."""
        try:
            # Ensure directory exists
            memory_dir = os.path.dirname(self.memory_file_path)
            if not os.path.exists(memory_dir):
                 print(f"Memory directory not found. Attempting to create: {memory_dir}")
                 try:
                      os.makedirs(memory_dir, exist_ok=True)
                      print(f"Successfully created memory directory: {memory_dir}")
                 except OSError as e:
                      print(f"FATAL: Could not create memory directory {memory_dir}. Memory will not persist. Error: {e}")
                      self.user_memory = {} # Start with empty memory if dir fails
                      return # Stop loading if dir creation fails

            if os.path.exists(self.memory_file_path):
                with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                    self.user_memory = json.load(f)
                print(f"Loaded memory for {len(self.user_memory)} users from {self.memory_file_path}")
            else:
                print(f"Memory file not found at {self.memory_file_path}. Starting with empty memory.")
                self.user_memory = {}
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from memory file {self.memory_file_path}: {e}. Starting with empty memory.")
            self.user_memory = {}
        except Exception as e:
            print(f"Error loading memory from {self.memory_file_path}: {e}. Starting with empty memory.")
            self.user_memory = {}

    def save_memory(self):
        """Save the current user memory to the JSON file."""
        try:
             # Ensure directory exists before saving (important if creation failed on load)
             memory_dir = os.path.dirname(self.memory_file_path)
             if not os.path.exists(memory_dir):
                  try:
                       os.makedirs(memory_dir, exist_ok=True)
                  except OSError as e:
                       print(f"ERROR: Could not create memory directory {memory_dir} during save. Save failed. Error: {e}")
                       return # Abort save if directory cannot be ensured

             with open(self.memory_file_path, 'w', encoding='utf-8') as f:
                 json.dump(self.user_memory, f, indent=4, ensure_ascii=False)
             # print(f"Saved memory to {self.memory_file_path}") # Optional: uncomment for verbose logging
        except Exception as e:
            print(f"Error saving memory to {self.memory_file_path}: {e}")

    def add_user_fact(self, user_id: str, fact: str):
        """Adds a fact to a user's memory if it's not already there."""
        user_id_str = str(user_id) # Ensure consistency
        fact = fact.strip()
        if not fact:
             return # Don't add empty facts

        if user_id_str not in self.user_memory:
            self.user_memory[user_id_str] = []
        
        # Avoid adding duplicate facts (case-insensitive check)
        if not any(fact.lower() == existing_fact.lower() for existing_fact in self.user_memory[user_id_str]):
            self.user_memory[user_id_str].append(fact)
            print(f"Added fact for user {user_id_str}: '{fact}'")
            self.save_memory() # Save after adding a new fact
        # else:
            # print(f"Fact '{fact}' already known for user {user_id_str}.") # Optional: uncomment for debugging

    def get_user_facts(self, user_id: str) -> List[str]:
        """Retrieves the list of facts for a given user ID."""
        return self.user_memory.get(str(user_id), [])
    # -------------------------

    # --- Config Management (Unchanged) ---
    def load_configs(self):
        """Load user configurations from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_configs = json.load(f)
                    for user_id, config in loaded_configs.items():
                        self.user_configs[user_id] = self.default_config.copy()
                        self.user_configs[user_id].update(config) 
            else:
                 self.user_configs = {}
        except json.JSONDecodeError as e:
            print(f"Error loading configurations (invalid JSON): {e}")
            self.user_configs = {}
        except Exception as e:
            print(f"Error loading configurations: {e}")
            self.user_configs = {} 

    def save_configs(self):
        """Save user configurations to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.user_configs, f, indent=4)
        except Exception as e:
            print(f"Error saving configurations: {e}")
    
    def get_user_config(self, user_id: str) -> Dict:
        """Get configuration for a specific user or default if not set"""
        return self.user_configs.get(str(user_id), self.default_config).copy()
    # -------------------------

    async def generate_response(self, user_id: str, user_name: str, prompt: str, guild_id: Optional[int] = None, channel_id: Optional[int] = None) -> str:
        """Generate a response using the Together AI API, handling tools and memory."""
        if not self.api_key:
             return "Sorry, the AI API key is not configured. I cannot generate a response."
             
        config = self.get_user_config(user_id)
        user_id_str = str(user_id) # Ensure user ID is string

        # --- Regex Command Handling (Timeout, Search - could be converted to tools later) ---
        timeout_match = re.search(r"timeout\s+<@!?(\d+)>(?:\s+for\s+(\d+)\s*(minute|minutes|min|mins|hour|hours|day|days))?", prompt, re.IGNORECASE)
        search_match = re.search(r"search(?:\s+for)?\s+(.+?)(?:\s+on\s+the\s+internet)?$", prompt, re.IGNORECASE)
        
        if timeout_match and guild_id and channel_id:
            # (Timeout logic remains the same as previous version)
            target_id = timeout_match.group(1)
            duration_str = timeout_match.group(2) or "5"
            unit = (timeout_match.group(3) or "minutes").lower()
            try: duration = int(duration_str)
            except ValueError: return "Invalid duration specified for timeout."
            if unit.startswith("hour"): duration *= 60
            elif unit.startswith("day"): duration *= 1440
            duration = min(duration, 40320) 
            result = await self.timeout_user(guild_id, int(target_id), duration)
            if result:
                if duration >= 1440: timeout_str = f"{duration // 1440} day(s)"
                elif duration >= 60: timeout_str = f"{duration // 60} hour(s)"
                else: timeout_str = f"{duration} minute(s)"
                return f"Okay~! I've timed out <@{target_id}> for {timeout_str}! Tee-hee! ✨"
            else:
                return "Aww, I couldn't timeout that user... 😥 Maybe I don't have the 'Timeout Members' permission, or they have a higher role than me?"

        elif search_match:
            query = search_match.group(1).strip()
            search_results = await self.search_internet(query)
            # Modify prompt to include search results for the AI to synthesize
            prompt += f"\n\n[System Note: I just searched the internet for '{query}'. Use the following results to answer the user's request naturally as Kasane Teto. Do not just repeat the results verbatim.]\nSearch Results:\n{search_results}"
            # Let the normal AI generation process handle the response synthesis
        
        # --- Prepare context with memory ---
        user_facts = self.get_user_facts(user_id_str)
        user_memory_str = ""
        if user_facts:
             facts_list = "\n".join([f"- {fact}" for fact in user_facts])
             user_memory_str = f"Here's what you remember about {user_name} (User ID: {user_id_str}):\n{facts_list}"
        
        system_context = self.system_prompt_template.format(user_memory_context=user_memory_str)
        # ---------------------------------

        # --- API Call with Tool Handling ---
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Initial message history
        # TODO: Add conversation history persistence if desired
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_context},
            {"role": "user", "content": f"{user_name}: {prompt}"} 
        ]

        max_tool_iterations = 5 # Prevent infinite loops
        for _ in range(max_tool_iterations):
            payload = {
                "model": config["model"],
                "messages": messages,
                "tools": self.tools, # Pass tool definitions
                "temperature": config.get("temperature"), 
                "max_tokens": config.get("max_tokens"),
                "top_p": config.get("top_p"),
                "frequency_penalty": config.get("frequency_penalty"),
                "presence_penalty": config.get("presence_penalty"),
            }
            payload = {k: v for k, v in payload.items() if v is not None} # Clean payload

            try:
                async with aiohttp.ClientSession() as session:
                     async with session.post(self.api_url, headers=headers, json=payload, timeout=60.0) as response: # Increased timeout
                        if response.status == 200:
                            data = await response.json()
                            
                            if not data.get("choices") or not data["choices"][0].get("message"):
                                 print(f"API Error: Unexpected response format. Data: {data}")
                                 return f"Sorry {user_name}, I got an unexpected response from the AI. Maybe try again?"
                            
                            response_message = data["choices"][0]["message"]
                            finish_reason = data["choices"][0].get("finish_reason")

                            # Append the assistant's response (even if it includes tool calls)
                            messages.append(response_message) 

                            # Check for tool calls
                            if response_message.get("tool_calls") and finish_reason == "tool_calls":
                                print(f"AI requested tool calls: {response_message['tool_calls']}")
                                tool_calls = response_message["tool_calls"]
                                
                                # --- Process Tool Calls ---
                                for tool_call in tool_calls:
                                    function_name = tool_call.get("function", {}).get("name")
                                    tool_call_id = tool_call.get("id")
                                    
                                    try:
                                        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                                        
                                        tool_result_content = ""

                                        if function_name == "run_safe_shell_command":
                                            command_to_run = arguments.get("command")
                                            if command_to_run:
                                                if self.is_safe_command(command_to_run):
                                                     print(f"Executing safe command: '{command_to_run}'")
                                                     tool_result_content = await self.run_shell_command(command_to_run)
                                                else:
                                                     print(f"Blocked unsafe command: '{command_to_run}'")
                                                     tool_result_content = f"Error: Command '{command_to_run}' is not allowed for safety reasons."
                                            else:
                                                 tool_result_content = "Error: No command provided."
                                        
                                        elif function_name == "remember_fact_about_user":
                                            fact_user_id = arguments.get("user_id")
                                            fact_to_remember = arguments.get("fact")
                                            
                                            # Validate if the AI is trying to remember for the correct user
                                            if fact_user_id == user_id_str and fact_to_remember:
                                                self.add_user_fact(fact_user_id, fact_to_remember)
                                                tool_result_content = f"Successfully remembered fact about user {fact_user_id}: '{fact_to_remember}'"
                                                # Update system context for *next* potential iteration or final response (optional, maybe too complex)
                                            elif not fact_user_id or not fact_to_remember:
                                                 tool_result_content = "Error: Missing user_id or fact to remember."
                                            else:
                                                # Prevent AI from saving facts for other users in this context easily
                                                 tool_result_content = f"Error: Cannot remember fact for a different user (requested: {fact_user_id}) in this context."
                                        
                                        else:
                                            tool_result_content = f"Error: Unknown tool function '{function_name}'."

                                        # Append tool result message
                                        messages.append({
                                            "role": "tool",
                                            "tool_call_id": tool_call_id,
                                            "content": tool_result_content,
                                        })

                                    except json.JSONDecodeError:
                                        print(f"Error decoding tool arguments: {tool_call.get('function', {}).get('arguments')}")
                                        messages.append({
                                            "role": "tool", "tool_call_id": tool_call_id, 
                                            "content": "Error: Invalid arguments format for tool call."})
                                    except Exception as e:
                                         print(f"Error executing tool {function_name}: {e}")
                                         messages.append({
                                            "role": "tool", "tool_call_id": tool_call_id, 
                                            "content": f"Error: An unexpected error occurred while running the tool: {e}"})
                                # --- End Tool Processing ---
                                # Continue loop to make next API call with tool results

                            # No tool calls, or finished after tool calls
                            elif response_message.get("content"):
                                final_response = response_message["content"].strip()
                                print(f"AI Response for {user_name}: {final_response[:100]}...") # Log snippet
                                return final_response
                            
                            else:
                                # Should not happen if finish_reason isn't tool_calls but no content
                                print(f"API Error: No content and no tool calls in response. Data: {data}")
                                return "Hmm, I seem to have lost my train of thought... Can you ask again?"


                        else: # Handle HTTP errors from API
                            error_text = await response.text()
                            print(f"API Error: {response.status} - {error_text}")
                            try: error_data = json.loads(error_text); error_msg = error_data.get("error", {}).get("message", error_text)
                            except json.JSONDecodeError: error_msg = error_text
                            return f"Wahh! Something went wrong communicating with the AI! (Error {response.status}: {error_msg}) 😭 Please tell my developer!"
            
            except aiohttp.ClientConnectorError as e:
                print(f"Connection Error: {e}")
                return "Oh no! I couldn't connect to the AI service. Maybe check the connection?"
            except asyncio.TimeoutError:
                print("API Request Timeout")
                return "Hmm, the AI is taking a long time to respond. Maybe it's thinking *really* hard? Try again in a moment?"
            except Exception as e:
                print(f"Error in generate_response loop: {e}")
                return f"Oopsie! A little glitch happened while I was processing that ({type(e).__name__}). Can you try asking again? ✨"

        # If loop finishes without returning (too many tool iterations)
        print("Error: Exceeded maximum tool iterations.")
        return "Eek! I got stuck in a loop trying to use my tools. Maybe try rephrasing your request?"
    # --- End API Call ---

    # --- Safety and Execution ---
    def is_safe_command(self, command: str) -> bool:
        """Check if a shell command is safe to run. Blocks 'cat'."""
        command = command.strip()
        if not command:
             return False # Empty command is not safe/valid

        # Split command into parts for analysis
        try:
            # Basic split, doesn't handle complex quoting perfectly but good enough for safety checks
            parts = command.split()
            first_command = parts[0].lower() if parts else ""
        except Exception:
            return False # Error splitting

        # 1. Explicitly Disallowed Command Starts
        disallowed_starts = [
            "cat", "rm", "del", "mv", "cp", "chmod", "chown", "sudo", "su",
            "pip", "apt", "yum", "dnf", "pacman", "brew", "npm", "yarn", "gem", "composer",
            "wget", "curl", # Often used maliciously, block unless specifically needed & validated
            "mkfs", "fdisk", "mount", "umount", "dd", "format",
            "shutdown", "reboot", "poweroff", "halt", "systemctl", "service", "init",
            "kill", "pkill", "killall", "useradd", "userdel", "passwd", "visudo",
            "ssh", "telnet", "nc", "netcat", "iptables", "ufw", "firewall-cmd",
            "python", "perl", "ruby", "php", "bash", "sh", "zsh", # Prevent running scripts directly
            "eval", "exec", "source", ".", # Prevent execution flow changes
            ":" # Fork bomb prelude
        ]
        if first_command in disallowed_starts:
            print(f"Unsafe command blocked (disallowed start '{first_command}'): {command}")
            return False
            
        # 2. Check for Dangerous Patterns/Characters anywhere in the command string
        dangerous_patterns = [
             ";", "|", "&", "`", "$(", "${", # Command separators/execution
             ">", "<", # Redirection (can overwrite files)
             "../", # Directory traversal
             "/etc/", "/root/", "/System/", "/Windows/", # Sensitive paths (crude check)
             "\\", # Often problematic or used maliciously
             # Add more as needed
        ]
        for pattern in dangerous_patterns:
             if pattern in command:
                  print(f"Unsafe command blocked (dangerous pattern '{pattern}' found): {command}")
                  return False

        # 3. Allow only known safe command starts (Whitelist approach is safer)
        safe_starts = [
            "echo", "date", "uptime", "whoami", "hostname", "uname",
            "pwd", "ls", "dir", "head", "tail", # File listing/viewing (cat is blocked above)
            "wc", "grep", "find", # Text processing (find can be risky, use with caution)
            "ping", "traceroute", "tracepath", "mtr", "netstat", "ss", # Network diagnostics
            "ifconfig", "ipconfig", "ip", # Network info
            "ps", "top", "htop", "free", "df", "du" # System info
            # Add more *very carefully* tested safe commands if absolutely necessary
        ]
        if first_command in safe_starts:
            print(f"Command deemed safe: {command}")
            return True # Command starts with a safe keyword and passed other checks

        # Default to unsafe if not explicitly allowed
        print(f"Unsafe command blocked (unknown start '{first_command}' or other issue): {command}")
        return False

    async def run_shell_command(self, command: str) -> str:
        """Run a shell command and return the output, ensuring safety checks passed first."""
        # Safety check should be done *before* calling this method now
        # This method now assumes the command passed is_safe_command
        process = None
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*100 # Limit buffer size
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
            
            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()

            if process.returncode == 0:
                output = stdout_str if stdout_str else "(Command ran successfully with no output)"
                if stderr_str: output += f"\n[Stderr: {stderr_str}]" # Include stderr even on success
            else:
                output = f"(Command failed with exit code {process.returncode})"
                # Prioritize stderr for error message, but include stdout if stderr is empty
                error_details = stderr_str if stderr_str else stdout_str
                if error_details:
                     output += f"\nOutput/Error:\n{error_details}"

            max_output_len = 1500
            if len(output) > max_output_len:
                output = output[:max_output_len - 20] + f"... (truncated {len(output) - max_output_len} chars)"
            
            return output

        except asyncio.TimeoutError:
            # Terminate process if timed out
            if process.returncode is None:
                try: process.terminate(); await process.wait()
                except ProcessLookupError: pass 
                except Exception as term_err: print(f"Error terminating process: {term_err}")
            return "Error: Command timed out after 10 seconds."
        except FileNotFoundError:
             return f"Error: Command not found or invalid: '{command.split()[0]}'"
        except Exception as e:
            return f"Error running command: {str(e)}"
    # -------------------------

    # --- Other Methods (timeout_user, search_internet, check_admin_permissions - Unchanged) ---
    async def timeout_user(self, guild_id: int, user_id: int, minutes: int) -> bool:
        # (Same implementation as previous version)
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild: return False
            member = await guild.fetch_member(user_id) 
            if not member: return False
            if not guild.me.guild_permissions.moderate_members: return False
            if member.top_role >= guild.me.top_role: return False
            duration = timedelta(minutes=min(minutes, 40320)) 
            await member.timeout(duration, reason=f"Timed out by Kasane Teto via AI command")
            return True
        except Exception as e:
            print(f"Error timing out user {str(user_id)}: {e}")
            return False

    async def search_internet(self, query: str) -> str:
         # (Same implementation as previous version - uses SerpApi)
        serp_api_key = os.getenv("SERPAPI_KEY") 
        if not serp_api_key: return "Search is disabled (missing API key)."
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://serpapi.com/search.json?q={encoded_query}&api_key={serp_api_key}&engine=google"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15.0) as response: 
                    if response.status == 200:
                        data = await response.json(); results = []
                        # Extract Answer Box / Knowledge Graph / Organic Results (same logic)
                        summary = None
                        if data.get("answer_box"): ab = data["answer_box"]; summary = ab.get("answer") or ab.get("snippet")
                        if summary: results.append(f"**Summary:** {(summary[:300] + '...') if len(summary) > 300 else summary}")
                        if not summary and data.get("knowledge_graph"):
                            kg = data["knowledge_graph"]
                            title = kg.get("title", "")
                            desc = kg.get("description", "")
                            if title and desc:
                                kg_text = f"{title}: {desc}"
                                results.append(f"**Info:** {(kg_text[:350] + '...') if len(kg_text) > 350 else kg_text}")
                            if kg.get("source", {}) and kg.get("source", {}).get("link"):
                                results.append(f"  Source: <{kg['source']['link']}>")
                        if "organic_results" in data:
                            count = 0
                            max_r = 2 if results else 3
                            for r in data["organic_results"]:
                                if count >= max_r:
                                    break
                                t = r.get("title", "")
                                l = r.get("link", "#")
                                s = r.get("snippet", "").replace("\n", " ").strip()
                                s = (s[:250] + '...') if len(s) > 250 else s
                                results.append(f"**{t}**: {s}\n  Link: <{l}>")
                                count += 1
                        return "\n\n".join(results) if results else "No relevant results found."
                    else: error_text = await response.text(); print(f"SerpApi Error: {response.status} - {error_text}"); return f"Search error ({response.status})."
        except Exception as e: print(f"Error searching internet: {e}"); return f"Search failed: {str(e)}"

    async def check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        # (Same implementation as previous version)
        if not interaction.guild: await interaction.followup.send("This command only works in a server."); return False
        if interaction.channel.permissions_for(interaction.user).administrator: return True
        await interaction.followup.send("Hehe, you need **Administrator** powers for this! ✨", ephemeral=True); return False
    # -------------------------

    # --- Slash Commands (/talk, /aiconfig, /aichannel - Largely Unchanged) ---
    # Note: /talk now uses the enhanced generate_response method
    @app_commands.command(name="talk", description="Have a chat with Kasane Teto!")
    @app_commands.describe(prompt="What do you want to say to Teto?")
    async def slash_ai(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer() 
        user_id = str(interaction.user.id)
        user_name = interaction.user.display_name
        guild_id = interaction.guild.id if interaction.guild else None
        channel_id = interaction.channel.id if interaction.channel else None
        try:
            response = await self.generate_response(user_id, user_name, prompt, guild_id, channel_id)
            # Split long messages
            if len(response) > 2000:
                 for chunk in [response[i:i+1990] for i in range(0, len(response), 1990)]: 
                      await interaction.followup.send(chunk, suppress_embeds=True) # Suppress embeds for chunks
            else:
                 await interaction.followup.send(response, suppress_embeds=True)
        except Exception as e:
            print(f"Error in slash_ai: {e}")
            await interaction.followup.send(f"A critical error occurred processing that request. Please tell my developer! Error: {type(e).__name__}")

    @app_commands.command(name="aiconfig", description="Configure AI settings (Admin Only)")
    @app_commands.describe( # Descriptions updated slightly
        model="Together AI model identifier (e.g., 'mistralai/Mixtral-8x7B-Instruct-v0.1')",
        temperature="AI creativity/randomness (0.0-2.0).",
        max_tokens="Max response length (1-16384).", # Range updated
        top_p="Nucleus sampling probability (0.0-1.0).",
        frequency_penalty="Penalty for repeating tokens (-2.0-2.0).",
        presence_penalty="Penalty for repeating topics (-2.0-2.0)."
    )
    async def slash_aiconfig(
        self, interaction: discord.Interaction, 
        model: Optional[str] = None,
        temperature: Optional[app_commands.Range[float,0.0,2.0]] = None, 
        max_tokens: Optional[app_commands.Range[int, 1, 16384]] = None,
        top_p: Optional[app_commands.Range[float, 0.0, 1.0]] = None,
        frequency_penalty: Optional[app_commands.Range[float, -2.0, 2.0]] = None,
        presence_penalty: Optional[app_commands.Range[float, -2.0, 2.0]] = None
    ):
         # (Implementation remains the same, using Range for validation)
        await interaction.response.defer(ephemeral=True) 
        if not await self.check_admin_permissions(interaction): return
        user_id = str(interaction.user.id) # Still configures the *admin's* personal settings
        if user_id not in self.user_configs: self.user_configs[user_id] = self.default_config.copy()
        changes = []; current_config = self.user_configs[user_id]
        if model is not None:
             if "/" in model and len(model) > 3: current_config["model"] = model; changes.append(f"Model: `{model}`")
             else: await interaction.followup.send(f"Invalid model format: `{model}`."); return
        if temperature is not None: current_config["temperature"] = temperature; changes.append(f"Temperature: `{temperature}`")
        if max_tokens is not None: current_config["max_tokens"] = max_tokens; changes.append(f"Max Tokens: `{max_tokens}`")
        if top_p is not None: current_config["top_p"] = top_p; changes.append(f"Top P: `{top_p}`")
        if frequency_penalty is not None: current_config["frequency_penalty"] = frequency_penalty; changes.append(f"Frequency Penalty: `{frequency_penalty}`")
        if presence_penalty is not None: current_config["presence_penalty"] = presence_penalty; changes.append(f"Presence Penalty: `{presence_penalty}`")
        if not changes: await interaction.followup.send("No settings changed.", ephemeral=True); return
        self.save_configs()
        config = self.user_configs[user_id]
        config_message = (f"Okay~! {interaction.user.mention} updated your AI config:\n" + "\n".join([f"- {k.replace('_',' ').title()}: `{v}`" for k, v in config.items()]) + "\n\nChanges:\n- " + "\n- ".join(changes))
        await interaction.followup.send(config_message) # Sends publicly

    @app_commands.command(name="aichannel", description="Toggle Teto responding to *all* messages here (Admin Only)")
    async def slash_aichannel(self, interaction: discord.Interaction):
        # (Implementation remains the same)
        await interaction.response.defer() 
        if not await self.check_admin_permissions(interaction): await interaction.edit_original_response(content="You need administrator permissions!"); return
        if not interaction.channel: await interaction.followup.send("Cannot use here."); return
        channel_id = interaction.channel.id
        if channel_id in self.active_channels: self.active_channels.remove(channel_id); await interaction.followup.send(f"Okay! I won't reply to *every* message in {interaction.channel.mention} anymore. 😊")
        else: self.active_channels.add(channel_id); await interaction.followup.send(f"Yay! 🎉 I'll now respond to **all** messages in {interaction.channel.mention}!")
    # -------------------------

    # --- Listener (on_message - Unchanged logic, but uses new generate_response) ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user or message.author.bot: return
        ctx = await self.bot.get_context(message); 
        if ctx.valid: return # Let command processing handle valid commands

        user_id = str(message.author.id)
        user_name = message.author.display_name
        guild_id = message.guild.id if message.guild else None
        channel_id = message.channel.id if message.channel else None
        
        should_respond = False; prompt = message.content; response_prefix = ""
        mention_pattern = f'<@!?{self.bot.user.id}>'
        
        if re.match(mention_pattern, message.content) or self.bot.user in message.mentions:
            should_respond = True; prompt = re.sub(mention_pattern, '', message.content).strip(); prompt = prompt or "Hey Teto!"
        elif channel_id in self.active_channels:
            should_respond = True
        elif re.search(rf'\b{re.escape(self.bot.user.name)}\b', message.content, re.IGNORECASE):
             should_respond = True
             if channel_id not in self.active_channels: response_prefix = f"{message.author.mention} "
        
        if should_respond and prompt and self.api_key:
            async with message.channel.typing():
                try:
                    response = await self.generate_response(user_id, user_name, prompt, guild_id, channel_id)
                    reply_func = message.reply if hasattr(message, 'reply') else message.channel.send
                    final_response = response_prefix + response
                    
                    # Split long messages
                    if len(final_response) > 2000:
                         first_chunk = True
                         for chunk in [final_response[i:i+1990] for i in range(0, len(final_response), 1990)]:
                              send_func = reply_func if first_chunk else message.channel.send
                              await send_func(chunk, suppress_embeds=True)
                              first_chunk = False
                    else:
                         await reply_func(final_response, suppress_embeds=True)

                except Exception as e:
                    print(f"Error during on_message generation/sending: {e}")
                    # Maybe add a cooldown to sending error messages in chat
                    # await message.channel.send("Oops, Teto brain freeze! 🧠❄️ Try again?")
    # -------------------------

# --- Setup Function (Checks remain the same) ---
async def setup(bot: commands.Bot):
    ai_api_key = os.getenv("AI_API_KEY")
    serpapi_key = os.getenv("SERPAPI_KEY")
    memory_path = os.getenv("BOT_MEMORY_PATH", DEFAULT_MEMORY_PATH) # Get effective path

    print("-" * 60) # Separator for clarity
    # Check AI Key
    if not ai_api_key:
        print("!!! WARNING: AI_API_KEY not set. AI features WILL NOT WORK. !!!")
    else:
        print(f"AI_API_KEY loaded (ends with ...{ai_api_key[-4:]}). Using Together AI.")

    # Check Search Key
    if not serpapi_key:
        print("--- INFO: SERPAPI_KEY not set. Internet search will be disabled. ---")
    else:
        print("SERPAPI_KEY loaded. Internet search enabled.")

    # Report Memory Path
    print(f"Bot memory will be loaded/saved at: {memory_path}")
    # You might want to add a check here if the directory is writable at startup, though the cog tries too.

    print("-" * 60)

    # Add the cog
    try:
        await bot.add_cog(AICog(bot))
        print("AICog loaded successfully.")
    except Exception as e:
        print(f"\n!!! FATAL ERROR: Failed to load AICog! Reason: {e} !!!\n")
        # Depending on your bot structure, you might want to exit or prevent startup here