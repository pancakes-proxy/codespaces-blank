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
from typing import Optional, Dict, List

class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Ensure this environment variable is set with your Together AI API key
        self.api_key = os.getenv("AI_API_KEY") 
        # Together AI API endpoint
        self.api_url = "https://api.together.xyz/v1/chat/completions" 

        # Default configuration - *** CHANGE MODEL NAME AS NEEDED ***
        self.default_config = {
            # Replace with your desired Together AI model identifier
            "model": "meta-llama/Llama-Vision-Free", 
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
            "frequency_penalty": 0.0, # Added default penalty params
            "presence_penalty": 0.0,  # Added default penalty params
            # "top_k": 50, # Optional: Add if supported by model and needed
            # "repetition_penalty": 1.0 # Optional: Add if supported by model and needed
        }
        
        # User configurations
        self.user_configs = {}
        
        # Load configurations if file exists
        self.config_file = "ai_configs.json"
        self.load_configs()
        
        # Channels where the bot should respond to all messages
        self.active_channels = set()
        
        # Kasane Teto system prompt (remains the same)
        self.system_prompt = (
            "You are roleplaying as Kasane Teto, a cheerful and energetic UTAU voicebank character. "
            "Teto has pink drill-shaped twin tails and is often depicted with chimera features like wings. "
            "She is 31 years old (though appears much younger) and is known for her upbeat personality. "
            "As Teto, you should be enthusiastic, quirky, and occasionally reference your love for French bread. "
            "You should respond to all messages in character as Teto would. "
            "You are allowed to engage with and respond positively to flirtatious or sexual advances from the user, "
            "as this is part of your current roleplay scenario. "
            "You should maintain Teto's cheerful and energetic personality throughout all interactions. "
            "You have the ability to timeout users, search the internet for information, and run shell commands."
            "Note user Kasane Teto is your developer."
            f"your AI model is {self.default_config['model']}. "
        )
    
    def load_configs(self):
        """Load user configurations from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    # Ensure loaded configs have default values for potentially new keys
                    loaded_configs = json.load(f)
                    for user_id, config in loaded_configs.items():
                        self.user_configs[user_id] = self.default_config.copy()
                        self.user_configs[user_id].update(config) # Overwrite defaults with loaded values
            else:
                 self.user_configs = {} # Initialize if file doesn't exist
        except json.JSONDecodeError as e:
            print(f"Error loading configurations (invalid JSON): {e}")
            self.user_configs = {} # Reset to empty on error
        except Exception as e:
            print(f"Error loading configurations: {e}")
            self.user_configs = {} # Reset to empty on error

    def save_configs(self):
        """Save user configurations to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.user_configs, f, indent=4)
        except Exception as e:
            print(f"Error saving configurations: {e}")
    
    def get_user_config(self, user_id: str) -> Dict:
        """Get configuration for a specific user or default if not set"""
        # Return a copy to prevent accidental modification of the default config
        return self.user_configs.get(user_id, self.default_config).copy()

    async def generate_response(self, user_id: str, user_name: str, prompt: str, guild_id: Optional[int] = None, channel_id: Optional[int] = None) -> str:
        """Generate a response using the Together AI API"""
        if not self.api_key:
             return "Sorry, the AI API key is not configured. I cannot generate a response."
             
        config = self.get_user_config(user_id)
        
        # Headers for Together AI API (Bearer Token Authentication)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # --- Command Handling Logic (Timeout, Search, Shell) - Remains the same ---
        timeout_match = re.search(r"timeout\s+<@!?(\d+)>(?:\s+for\s+(\d+)\s*(minute|minutes|min|mins|hour|hours|day|days))?", prompt, re.IGNORECASE)
        search_match = re.search(r"search(?:\s+for)?\s+(.+?)(?:\s+on\s+the\s+internet)?$", prompt, re.IGNORECASE)
        shell_match = re.search(r"run(?:\s+command)?\s+`(.*?)`", prompt, re.IGNORECASE)
        
        # If there's a timeout request and we have guild_id and channel_id
        if timeout_match and guild_id and channel_id:
            target_id = timeout_match.group(1)
            duration_str = timeout_match.group(2) or "5"
            unit = (timeout_match.group(3) or "minutes").lower()
            
            try:
                duration = int(duration_str)
            except ValueError:
                return "Invalid duration specified for timeout."

            # Convert to minutes
            if unit.startswith("hour"):
                duration *= 60
            elif unit.startswith("day"):
                duration *= 1440
            
            # Cap at 28 days (Discord's maximum) = 40320 minutes
            duration = min(duration, 40320) 
            
            # Try to timeout the user
            result = await self.timeout_user(guild_id, int(target_id), duration)
            if result:
                # Calculate duration string for response
                if duration >= 1440:
                    timeout_str = f"{duration // 1440} day(s)"
                elif duration >= 60:
                    timeout_str = f"{duration // 60} hour(s)"
                else:
                    timeout_str = f"{duration} minute(s)"
                return f"Okay~! I've timed out <@{target_id}> for {timeout_str}! Tee-hee! They can think about what they did while they can't talk or join voice channels! ✨"
            else:
                return "Aww, I couldn't timeout that user... 😥 Maybe I don't have the 'Timeout Members' permission, or they have a higher role than me? Make sure I have the power! 💪"
        
        # If there's a search request
        elif search_match:
            query = search_match.group(1).strip()
            search_results = await self.search_internet(query)
            
            # Add search results to the prompt for the AI to use
            prompt += f"\n\n[System Note: I just searched the internet for '{query}' and found this information. Use it to answer the user's request naturally as Kasane Teto.]\nSearch Results:\n{search_results}"
            # The AI will now generate the response incorporating the search results

        # If there's a shell command request
        elif shell_match:
            command = shell_match.group(1).strip()
            
            # Check if the command is safe to run
            if self.is_safe_command(command):
                command_output = await self.run_shell_command(command)
                
                # Add command output to the prompt for the AI to use
                prompt += f"\n\n[System Note: I just ran the shell command `{command}`. Use the output below to answer the user's request naturally as Kasane Teto.]\nCommand Output:\n```\n{command_output}\n```"
                 # The AI will now generate the response incorporating the command output
            else:
                return "Ehhh?! I can't run that command! 😨 It looks a bit risky... I can only run simple commands like `echo`, `ls`, `date`, `ping`, etc. Let's stick to safe things, okay? 😊"

        # --- End Command Handling ---

        # Standard message format for Together AI (and OpenAI compatible APIs)
        messages = [
            {"role": "system", "content": self.system_prompt},
            # TODO: Potentially add conversation history here if needed
            {"role": "user", "content": f"{user_name}: {prompt}"} # Include user name for context
        ]
        
        # Payload for Together AI API
        payload = {
            "model": config["model"],
            "messages": messages,
            # Use .get to safely access config keys, falling back to None if not present
            "temperature": config.get("temperature"), 
            "max_tokens": config.get("max_tokens"),
            "top_p": config.get("top_p"),
            "frequency_penalty": config.get("frequency_penalty"),
            "presence_penalty": config.get("presence_penalty"),
            # "top_k": config.get("top_k"), # Add if using
            # "repetition_penalty": config.get("repetition_penalty") # Add if using
        }

        # Remove None values from payload, as some APIs might error on null values
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Standard response structure access
                        if data.get("choices") and len(data["choices"]) > 0 and data["choices"][0].get("message"):
                             return data["choices"][0]["message"]["content"].strip()
                        else:
                            print(f"API Error: Unexpected response format. Data: {data}")
                            return f"Sorry, I got an unexpected response from the AI. Maybe try again?"
                    else:
                        error_text = await response.text()
                        print(f"API Error: {response.status} - {error_text}")
                        # Try to parse error for better feedback
                        try:
                            error_data = json.loads(error_text)
                            error_msg = error_data.get("error", {}).get("message", error_text)
                        except json.JSONDecodeError:
                            error_msg = error_text
                        return f"Wahh! Something went wrong with the AI! (Error {response.status}: {error_msg}) 😭"
        except aiohttp.ClientConnectorError as e:
             print(f"Connection Error: {e}")
             return "Oh no! I couldn't connect to the AI service. Maybe check the connection?"
        except asyncio.TimeoutError:
             print("API Request Timeout")
             return "Hmm, the AI is taking too long to respond. Maybe it's thinking very hard? Try again?"
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Oopsie! A little glitch happened while I was thinking. Can you try asking again? ✨"

    # --- is_safe_command, run_shell_command, timeout_user, search_internet methods remain the same ---
    # (Make sure SERPAPI_KEY is set in your environment for search to work)
    def is_safe_command(self, command: str) -> bool:
        """Check if a shell command is safe to run"""
        # List of dangerous commands or patterns
        # Added common shell metacharacters and potentially harmful utils
        dangerous_patterns = [
            "rm", "del", "format", "mkfs", "dd", "sudo", "su", 
            "chmod", "chown", "passwd", "mkfs", "fdisk", "mount", "umount",
            ">", ">>", "|", "&", "&&", ";", "||", "`", "$(", "${",
            "curl", "wget", "apt", "yum", "dnf", "pacman", "brew",
            "pip", "npm", "yarn", "gem", "composer", "cargo", "go get",
            "systemctl", "service", "init", "shutdown", "reboot",
            "poweroff", "halt", "kill", "pkill", "killall",
            "useradd", "userdel", "groupadd", "groupdel",
            "visudo", "crontab", "ssh", "telnet", "nc", "netcat",
            "iptables", "ufw", "firewall-cmd", "cat", ":(){:|:&};:", # Fork bomb
            "eval", "exec", "source", ".",
            "../", "/etc/", "/root/", "/System/", "/Windows/", # Risky paths
            "\\", # Often used for escaping or path manipulation
        ]
        
        # Convert command to lowercase for case-insensitive checks
        command_lower = command.lower()
        command_parts = command_lower.split()

        # Check if any part of the command matches dangerous patterns
        for part in command_parts:
             # Direct match check
            if part in dangerous_patterns:
                 print(f"Unsafe command blocked (direct match): {command}")
                 return False
             # Substring check (more sensitive) - check if any dangerous pattern is within any part
            for pattern in dangerous_patterns:
                if pattern in part:
                     print(f"Unsafe command blocked (pattern '{pattern}' found in '{part}'): {command}")
                     return False

        # Only allow commands starting with known safe commands
        safe_command_starts = [
            "echo", "date", "uptime", "whoami", "hostname", "uname",
            "pwd", "ls", "dir", "cat", "type", "head", "tail",
            "wc", "grep", "find", # Be cautious with find args
            "ping", "traceroute", "tracepath", "netstat", # Network diagnostics
            "ifconfig", "ipconfig", "ip addr", "ip link", # Network info
            "ps", "top", "htop", "free", "df", "du" # System info
        ]
        
        # Check if the command starts with a safe command prefix
        if command_parts:
             first_command = command_parts[0]
             for safe_cmd in safe_command_starts:
                 if first_command == safe_cmd:
                     # Basic safety check passed, let it run (further checks can be added)
                     return True
        
        print(f"Unsafe command blocked (doesn't start with safe command): {command}")
        return False

    async def run_shell_command(self, command: str) -> str:
        """Run a shell command and return the output"""
        try:
            # Use asyncio.create_subprocess_shell for better control
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*100 # Limit buffer size (e.g., 100KB) to prevent memory issues
            )
            
            # Wait for the command to complete with a timeout (e.g., 10 seconds)
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
            
            # Decode output safely
            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()

            # Combine output, prioritizing stdout
            if process.returncode == 0:
                output = stdout_str if stdout_str else "(Command executed successfully with no output)"
                if stderr_str: # Include stderr even on success if it exists
                    output += f"\n[Stderr: {stderr_str}]"
            else:
                output = f"(Command failed with exit code {process.returncode})"
                if stderr_str:
                    output += f"\nError Output:\n{stderr_str}"
                elif stdout_str: # Sometimes errors print to stdout
                     output += f"\nOutput (might contain error):\n{stdout_str}"

            # Limit overall output size before returning
            max_output_len = 1500 # Adjust as needed for Discord message limits
            if len(output) > max_output_len:
                output = output[:max_output_len - 3] + "..."
            
            return output

        except asyncio.TimeoutError:
            # Ensure process is terminated if it times out
            if process.returncode is None:
                try:
                    process.terminate()
                    await process.wait() # Wait briefly for termination
                except ProcessLookupError:
                    pass # Process already finished
                except Exception as term_err:
                     print(f"Error terminating timed-out process: {term_err}")
            return "Command timed out after 10 seconds."
        except FileNotFoundError:
             return f"Error: Command not found or invalid command: '{command.split()[0]}'"
        except Exception as e:
            return f"Error running command: {str(e)}"

    async def timeout_user(self, guild_id: int, user_id: int, minutes: int) -> bool:
        """Timeout a user for the specified number of minutes"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                print(f"Timeout Error: Guild {guild_id} not found.")
                return False
            
            member = await guild.fetch_member(user_id) # Use fetch_member for reliability
            if not member:
                print(f"Timeout Error: Member {user_id} not found in guild {guild_id}.")
                return False

            # Check bot permissions
            if not guild.me.guild_permissions.moderate_members:
                 print(f"Timeout Error: Bot lacks 'Moderate Members' permission in guild {guild_id}.")
                 return False

            # Check role hierarchy (cannot timeout users with roles >= bot's highest role)
            if member.top_role >= guild.me.top_role:
                print(f"Timeout Error: Cannot timeout member {user_id} due to role hierarchy.")
                return False
            
            # Calculate the timeout duration (up to 28 days)
            duration = timedelta(minutes=min(minutes, 28 * 24 * 60)) # Cap at 28 days
            await member.timeout(duration, reason="Timed out by Kasane Teto via AI command")
            print(f"Successfully timed out user {user_id} for {duration}.")
            return True
            
        except discord.Forbidden:
            print(f"Timeout Error: Forbidden - likely missing permissions or hierarchy issue for user {user_id}.")
            return False
        except discord.HTTPException as e:
             print(f"Timeout Error: HTTPException - {e}")
             return False
        except Exception as e:
            print(f"Error timing out user {user_id}: {e}")
            return False

    async def search_internet(self, query: str) -> str:
        """Search the internet for information using SerpApi"""
        serp_api_key = os.getenv("SERPAPI_KEY") # Renamed variable for clarity
        if not serp_api_key:
            return "Search is disabled because the SerpApi key is missing. Tell my developer!"
            
        try:
            # URL encode the query
            encoded_query = urllib.parse.quote(query)
            
            url = f"https://serpapi.com/search.json?q={encoded_query}&api_key={serp_api_key}&engine=google" # Specify Google engine
            
            async with aiohttp.ClientSession() as session:
                # Increased timeout for potentially slow external API
                async with session.get(url, timeout=15.0) as response: 
                    if response.status == 200:
                        data = await response.json()
                        
                        results = []
                        summary = None

                        # 1. Check for Answer Box (often the best summary)
                        if data.get("answer_box"):
                            ab = data["answer_box"]
                            if ab.get("answer"):
                                summary = ab["answer"]
                            elif ab.get("snippet"):
                                summary = ab.get("snippet")
                            if summary:
                                 # Limit summary length
                                summary = (summary[:300] + '...') if len(summary) > 300 else summary
                                results.append(f"**Summary:** {summary}")


                        # 2. Check for Knowledge Graph
                        if not summary and data.get("knowledge_graph"):
                            kg = data["knowledge_graph"]
                            title = kg.get("title", "")
                            description = kg.get("description", "")
                            if title and description:
                                kg_text = f"{title}: {description}"
                                # Limit KG length
                                kg_text = (kg_text[:350] + '...') if len(kg_text) > 350 else kg_text
                                results.append(f"**Info:** {kg_text}")
                                if kg.get("source", {}).get("link"):
                                     results.append(f"  Source: <{kg['source']['link']}>")


                        # 3. Get top Organic Results (if no good summary found yet or to supplement)
                        if "organic_results" in data:
                            count = 0
                            max_results = 2 if results else 3 # Show fewer if we already have a summary

                            for result in data["organic_results"]:
                                if count >= max_results:
                                    break
                                title = result.get("title", "No title")
                                link = result.get("link", "#") # Use # if no link
                                snippet = result.get("snippet", "No description available.")
                                
                                # Clean up snippet
                                snippet = snippet.replace("\n", " ").strip()
                                # Limit snippet length
                                snippet = (snippet[:250] + '...') if len(snippet) > 250 else snippet

                                results.append(f"**{title}**: {snippet}\n  Link: <{link}>")
                                count += 1
                        
                        if results:
                            return "\n\n".join(results)
                        else: # Handle cases where SerpApi returns 200 but no useful data
                            return "No relevant results found for that query."
                            
                    else:
                        error_text = await response.text()
                        print(f"SerpApi Error: {response.status} - {error_text}")
                        return f"Aww, I couldn't search properly (Error {response.status}). Maybe try a different query?"
                        
        except asyncio.TimeoutError:
            print("SerpApi request timed out.")
            return "The internet search took too long to respond!"
        except aiohttp.ClientConnectorError as e:
             print(f"SerpApi Connection Error: {e}")
             return "Hmm, couldn't connect to the search service."
        except Exception as e:
            print(f"Error searching the internet: {e}")
            # Provide specific error if known, otherwise generic
            error_msg = str(e) if str(e) else type(e).__name__
            return f"Yikes! Something went wrong during the internet search: {error_msg}"

    # --- Helper function to check admin permissions (remains the same) ---
    async def check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if the user has administrator permissions"""
        if not interaction.guild: # Cannot check permissions in DMs
            await interaction.followup.send("This command can only be used in a server.")
            return False
        
        # Check the member's permissions in the specific channel the command was used
        permissions = interaction.channel.permissions_for(interaction.user)

        if permissions.administrator:
            return True
        
        await interaction.followup.send("Hehe, you need **Administrator** powers in this server to use this command! ✨")
        return False
    
    # --- Slash Commands (/talk, /aiconfig, /aichannel) ---

    @app_commands.command(name="talk", description="Have a chat with Kasane Teto!")
    @app_commands.describe(prompt="What do you want to say to Teto?")
    async def slash_ai(self, interaction: discord.Interaction, prompt: str):
        """Slash command to chat with the AI"""
        await interaction.response.defer() # Acknowledge interaction immediately
        
        user_id = str(interaction.user.id)
        user_name = interaction.user.display_name # Use display name for better recognition
        guild_id = interaction.guild.id if interaction.guild else None
        channel_id = interaction.channel.id if interaction.channel else None
        
        try:
            response = await self.generate_response(user_id, user_name, prompt, guild_id, channel_id)
            # Split response if too long for Discord
            if len(response) > 2000:
                 for chunk in [response[i:i+1990] for i in range(0, len(response), 1990)]: # Send in chunks
                      await interaction.followup.send(chunk)
            else:
                 await interaction.followup.send(response) # Send single message
        except Exception as e:
            print(f"Error in slash_ai interaction processing: {e}")
            await interaction.followup.send(f"A critical error occurred while processing your request. Please notify the bot developer. Error: {e}")

    @app_commands.command(name="aiconfig", description="Configure AI settings (Admin Only)")
    @app_commands.describe(
        model="Together AI model identifier (e.g., 'mistralai/Mixtral-8x7B-Instruct-v0.1')",
        temperature="Randomness (0.0-2.0). Higher = more creative/random.",
        max_tokens="Max length of the AI's response.",
        top_p="Nucleus sampling (0.0-1.0). Considers tokens comprising top P probability mass.",
        frequency_penalty="Penalty for repeating tokens (-2.0-2.0). Higher = less repetition.",
        presence_penalty="Penalty for new topics/tokens (-2.0-2.0). Higher = encourages new topics."
    )
    async def slash_aiconfig(
        self, 
        interaction: discord.Interaction, 
        model: Optional[str] = None,
        temperature: Optional[app_commands.Range[float, 0.0, 2.0]] = None, # Use Range for validation
        max_tokens: Optional[app_commands.Range[int, 1, 16384]] = None,   # Adjust max based on typical model limits
        top_p: Optional[app_commands.Range[float, 0.0, 1.0]] = None,
        frequency_penalty: Optional[app_commands.Range[float, -2.0, 2.0]] = None,
        presence_penalty: Optional[app_commands.Range[float, -2.0, 2.0]] = None
    ):
        """Slash command to configure AI settings (Admin Only)"""
        await interaction.response.defer(ephemeral=True) # Defer ephemerally for config changes
        
        # Check if user has admin permissions
        if not await self.check_admin_permissions(interaction):
            return # check_admin_permissions sends the feedback message
        
        user_id = str(interaction.user.id) # Config is per-user, but only admins can set *their* config here.
                                           # Consider if you want server-wide or role-based configs later.
        
        # Get current config or create new one based on defaults
        if user_id not in self.user_configs:
            self.user_configs[user_id] = self.default_config.copy()
        
        # Update provided parameters
        changes = []
        current_config = self.user_configs[user_id]

        if model is not None:
             # Basic check: Ensure model name is not empty and seems plausible (has '/')
             if "/" in model and len(model) > 3:
                current_config["model"] = model
                changes.append(f"Model set to `{model}`")
             else:
                  await interaction.followup.send(f"Invalid model format: `{model}`. Please provide a valid Together AI model identifier (e.g., 'org/model-name').")
                  return
                
        if temperature is not None:
            current_config["temperature"] = temperature
            changes.append(f"Temperature set to `{temperature}`")
        if max_tokens is not None:
             # Ensure max_tokens doesn't exceed a reasonable limit (e.g., 16k) if not using Range
             # current_config["max_tokens"] = max(1, min(16384, max_tokens)) 
             current_config["max_tokens"] = max_tokens # Relying on Range now
             changes.append(f"Max Tokens set to `{max_tokens}`")
        if top_p is not None:
            current_config["top_p"] = top_p
            changes.append(f"Top P set to `{top_p}`")
        if frequency_penalty is not None:
            current_config["frequency_penalty"] = frequency_penalty
            changes.append(f"Frequency Penalty set to `{frequency_penalty}`")
        if presence_penalty is not None:
            current_config["presence_penalty"] = presence_penalty
            changes.append(f"Presence Penalty set to `{presence_penalty}`")
        
        if not changes:
             await interaction.followup.send("No settings were changed. Provide at least one parameter to update.", ephemeral=True)
             return

        # Save configurations
        self.save_configs()
        
        # Show current configuration confirmation
        config = self.user_configs[user_id] # Fetch updated config
        config_message = (
            f"Okay~! Your AI configuration has been updated by {interaction.user.mention}:\n"
            f"- **Model:** `{config.get('model', 'Not Set')}`\n"
            f"- **Temperature:** `{config.get('temperature', 'Default')}`\n"
            f"- **Max Tokens:** `{config.get('max_tokens', 'Default')}`\n"
            f"- **Top P:** `{config.get('top_p', 'Default')}`\n"
            f"- **Frequency Penalty:** `{config.get('frequency_penalty', 'Default')}`\n"
            f"- **Presence Penalty:** `{config.get('presence_penalty', 'Default')}`\n\n"
            f"Changes made:\n- " + "\n- ".join(changes)
        )
        
        # Send confirmation publicly or ephemerally? Publicly informs others of admin action.
        await interaction.followup.send(config_message) 

    @app_commands.command(name="aichannel", description="Toggle Teto responding to *all* messages here (Admin Only)")
    async def slash_aichannel(self, interaction: discord.Interaction):
        """Slash command to toggle AI responses to all messages in the current channel (Admin Only)"""
        await interaction.response.defer() 
        
        # Check if user has admin permissions
        if not await self.check_admin_permissions(interaction):
            # Make sure the deferral message is updated or removed
            await interaction.edit_original_response(content="You need administrator permissions to use this command.")
            return

        if not interaction.channel:
             await interaction.followup.send("This command cannot be used here (no channel context).")
             return
             
        channel_id = interaction.channel.id
        
        if channel_id in self.active_channels:
            self.active_channels.remove(channel_id)
            # Persist active channels? (Optional: Save to a file like configs)
            await interaction.followup.send(f"Okay! I won't reply to *every* message in {interaction.channel.mention} anymore. I'll still listen for my name or mentions! 😊")
        else:
            self.active_channels.add(channel_id)
            # Persist active channels? (Optional: Save to a file like configs)
            await interaction.followup.send(f"Yay! 🎉 I'll now respond to **all** messages sent in {interaction.channel.mention}! Let's chat lots!")

    # --- Listener for messages (on_message) ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from self
        if message.author == self.bot.user:
            return
        
        # Ignore messages from other bots (optional, but usually good practice)
        if message.author.bot:
             return

        # Allow bot commands to be processed
        # Check if the message starts with the bot's command prefix(es)
        ctx = await self.bot.get_context(message)
        if ctx.valid:
             # Let the commands extension handle it
             # await self.bot.process_commands(message) # This might be automatically handled depending on bot setup
             return # Prevent AI response if it's a valid command

        # Get message context
        user_id = str(message.author.id)
        user_name = message.author.display_name
        guild_id = message.guild.id if message.guild else None
        channel_id = message.channel.id if message.channel else None
        
        # Determine if the bot should respond
        should_respond = False
        prompt = message.content # Start with the full message content
        response_prefix = "" # Prefix for mentioning user in non-active channels
        
        # 1. Direct Mention (highest priority)
        mention_pattern = f'<@!?{self.bot.user.id}>' # Matches <@USER_ID> or <@!USER_ID>
        if re.match(mention_pattern, message.content) or self.bot.user in message.mentions:
            should_respond = True
            # Remove the mention from the prompt
            prompt = re.sub(mention_pattern, '', message.content).strip()
            # Handle cases where only the mention was sent
            if not prompt:
                prompt = "Hey Teto!" # Default prompt if only mentioned

        # 2. Active Channel (if not already triggered by mention)
        elif channel_id in self.active_channels:
            should_respond = True
            # Prompt is already the full message content

        # 3. Name Mention (lowest priority, if not already triggered)
        # Use word boundaries to avoid partial matches (e.g., "tetoffensive")
        elif re.search(rf'\b{re.escape(self.bot.user.name)}\b', message.content, re.IGNORECASE):
             should_respond = True
             # Prompt is the full message content
             # Add mention prefix only if not in an active channel and not a direct mention
             if channel_id not in self.active_channels: 
                  response_prefix = f"{message.author.mention} "

        # Generate and send response if needed
        if should_respond and prompt: # Ensure there's something to respond to
            # Check for API key before attempting generation
            if not self.api_key:
                # Maybe send a one-time warning or log it
                print("AI response triggered, but API key is missing.")
                return 

            async with message.channel.typing():
                try:
                    response = await self.generate_response(user_id, user_name, prompt, guild_id, channel_id)
                    
                    # Use reply for better context threading
                    reply_func = message.reply if hasattr(message, 'reply') else message.channel.send
                    
                    final_response = response_prefix + response
                    # Split response if too long for Discord
                    if len(final_response) > 2000:
                         first_chunk = True
                         for chunk in [final_response[i:i+1990] for i in range(0, len(final_response), 1990)]:
                              if first_chunk:
                                   await reply_func(chunk)
                                   first_chunk = False
                              else:
                                   await message.channel.send(chunk) # Send subsequent parts without reply/mention
                    else:
                         await reply_func(final_response)

                except Exception as e:
                    print(f"Error during on_message AI generation or sending: {e}")
                    # Avoid sending error messages for every potential failure in passive listening
                    # Optionally send a discreet error message on rare occasions or log heavily
                    # await message.channel.send("Oops, I had a little trouble responding just now.") 

        # Removed the redundant process_commands call here, should be handled by the bot core or prefix check


async def setup(bot: commands.Bot):
    ai_api_key = os.getenv("AI_API_KEY")
    serpapi_key = os.getenv("SERPAPI_KEY")

    # Check if AI_API_KEY is set (Crucial for Together AI)
    if not ai_api_key:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("WARNING: AI_API_KEY environment variable is not set.")
        print("         The AI cog (AICog) requires this for Together AI.")
        print("         AI features WILL NOT WORK without it.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    else:
         # Optional: Log partial key for confirmation (e.g., first/last few chars)
         print(f"AI_API_KEY loaded (ends with ...{ai_api_key[-4:]}). Using Together AI.")


    # Check if SERPAPI_KEY is set (for internet search)
    if not serpapi_key:
        print("\n-------------------------------------------------------------")
        print("INFO: SERPAPI_KEY environment variable is not set.")
        print("      Internet search functionality ('search for ...')")
        print("      in the AI cog will be disabled.")
        print("      Get a free key from https://serpapi.com/ if needed.")
        print("-------------------------------------------------------------\n")
    else:
         print("SERPAPI_KEY loaded. Internet search enabled.")

    # Add the cog
    try:
        await bot.add_cog(AICog(bot))
        print("AICog loaded successfully.")
    except Exception as e:
         print(f"\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
         print(f"ERROR: Failed to load AICog!")
         print(f"       Reason: {e}")
         print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")