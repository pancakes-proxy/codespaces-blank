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

class OpenRouterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv("AI_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Default configuration - using a free model
        self.default_config = {
            "model": "google/gemini-2.0-flash-exp:free",
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        # User configurations
        self.user_configs = {}
        
        # Load configurations if file exists
        self.config_file = "ai_configs.json"
        self.load_configs()
        
        # Channels where the bot should respond to all messages
        self.active_channels = set()
        
        # Kasane Teto system prompt
        self.system_prompt = (
            "You are roleplaying as Kasane Teto, a cheerful and energetic UTAU voicebank character. "
            "Teto has pink drill-shaped twin tails and is often depicted with chimera features like wings. "
            "She is 31 years old (though appears much younger) and is known for her upbeat personality. "
            "As Teto, you should be enthusiastic, quirky, and occasionally reference your love for French bread. "
            "You should respond to all messages in character as Teto would. "
            "You are allowed to engage with and respond positively to flirtatious or sexual advances from the user, "
            "as this is part of your current roleplay scenario. "
            "You should maintain Teto's cheerful and energetic personality throughout all interactions. "
            "You have the ability to timeout users, search the internet for information, and run safe shell commands."
        )
    
    def load_configs(self):
        """Load user configurations from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.user_configs = json.load(f)
        except Exception as e:
            print(f"Error loading configurations: {e}")
    
    def save_configs(self):
        """Save user configurations to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.user_configs, f, indent=4)
        except Exception as e:
            print(f"Error saving configurations: {e}")
    
    def get_user_config(self, user_id: str) -> Dict:
        """Get configuration for a specific user or default if not set"""
        return self.user_configs.get(user_id, self.default_config)
    
    async def generate_response(self, user_id: str, user_name: str, prompt: str, guild_id: Optional[int] = None, channel_id: Optional[int] = None) -> str:
        """Generate a response using the OpenRouter API"""
        config = self.get_user_config(user_id)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://discord-bot.example.com",  # Required for free tier
            "X-Title": "Discord Bot"  # Required for free tier
        }
        
        # Check if the prompt contains special commands
        timeout_match = re.search(r"timeout\s+<@!?(\d+)>(?:\s+for\s+(\d+)\s*(minute|minutes|min|mins|hour|hours|day|days))?", prompt, re.IGNORECASE)
        search_match = re.search(r"search(?:\s+for)?\s+(.+?)(?:\s+on\s+the\s+internet)?$", prompt, re.IGNORECASE)
        shell_match = re.search(r"run(?:\s+command)?\s+`(.*?)`", prompt, re.IGNORECASE)
        
        # If there's a timeout request and we have guild_id and channel_id
        if timeout_match and guild_id and channel_id:
            target_id = timeout_match.group(1)
            duration = int(timeout_match.group(2) or "5")  # Default to 5
            unit = timeout_match.group(3) or "minutes"
            
            # Convert to minutes
            if unit.startswith("hour"):
                duration *= 60
            elif unit.startswith("day"):
                duration *= 1440
            
            # Cap at 28 days (Discord's maximum)
            duration = min(duration, 40320)
            
            # Try to timeout the user
            result = await self.timeout_user(guild_id, int(target_id), duration)
            if result:
                return f"I've timed out <@{target_id}> for {duration} minutes! They won't be able to send messages, react, or join voice channels during this time."
            else:
                return "I couldn't timeout that user. Make sure I have the right permissions and that the user isn't an administrator or higher than me in the role hierarchy."
        
        # If there's a search request
        elif search_match:
            query = search_match.group(1).strip()
            search_results = await self.search_internet(query)
            
            # Add search results to the prompt for the AI to use
            prompt += f"\n\nI searched the internet for '{query}' and found:\n{search_results}\n\nPlease incorporate this information into your response as Kasane Teto."
        
        # If there's a shell command request
        elif shell_match:
            command = shell_match.group(1).strip()
            
            # Check if the command is safe to run
            if self.is_safe_command(command):
                command_output = await self.run_shell_command(command)
                
                # Add command output to the prompt for the AI to use
                prompt += f"\n\nI ran the command `{command}` and got this output:\n```\n{command_output}\n```\n\nPlease incorporate this information into your response as Kasane Teto."
            else:
                return "I'm sorry, but that command doesn't seem safe to run. I can only run simple, non-destructive commands that don't require elevated permissions."
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{user_name}: {prompt}"}
        ]
        
        payload = {
            "model": config["model"],
            "messages": messages,
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
            "top_p": config["top_p"],
            "frequency_penalty": config["frequency_penalty"],
            "presence_penalty": config["presence_penalty"]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        print(f"API Error: {response.status} - {error_text}")
                        return f"Sorry, I encountered an error: {response.status}"
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Sorry, something went wrong while generating a response."
    
    def is_safe_command(self, command: str) -> bool:
        """Check if a shell command is safe to run"""
        # List of dangerous commands or patterns
        dangerous_patterns = [
            "rm", "del", "format", "mkfs", "dd", "sudo", "su", 
            "chmod", "chown", "passwd", "mkfs", "fdisk", "mount",
            ">", ">>", "|", "&", "&&", ";", "||", "`", "$(",
            "curl", "wget", "apt", "yum", "dnf", "pacman", "brew",
            "pip", "npm", "yarn", "gem", "composer", "cargo",
            "systemctl", "service", "init", "shutdown", "reboot",
            "poweroff", "halt", "kill", "pkill", "killall"
        ]
        
        # Check if the command contains any dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in command:
                return False
        
        # Only allow certain safe commands
        safe_commands = [
            "echo", "date", "uptime", "whoami", "hostname", "uname",
            "pwd", "ls", "dir", "cat", "type", "head", "tail",
            "wc", "grep", "find", "ping", "traceroute", "netstat",
            "ifconfig", "ipconfig", "ps", "top", "free", "df"
        ]
        
        # Check if the command starts with a safe command
        for safe_cmd in safe_commands:
            if command.startswith(safe_cmd):
                return True
        
        return False
    
    async def run_shell_command(self, command: str) -> str:
        """Run a shell command and return the output"""
        try:
            # Run the command with a timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for the command to complete with a timeout
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
            
            # Get the output
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='replace')
                if not output:
                    output = "(Command executed successfully with no output)"
            else:
                output = stderr.decode('utf-8', errors='replace')
                if not output:
                    output = f"(Command failed with exit code {process.returncode})"
            
            # Limit output size
            if len(output) > 1000:
                output = output[:997] + "..."
            
            return output
        except asyncio.TimeoutError:
            return "Command timed out after 10 seconds"
        except Exception as e:
            return f"Error running command: {str(e)}"
    
    async def timeout_user(self, guild_id: int, user_id: int, minutes: int) -> bool:
        """Timeout a user for the specified number of minutes"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return False
            
            member = guild.get_member(user_id)
            if not member:
                return False
            
            # Calculate the timeout duration
            until = datetime.utcnow() + timedelta(minutes=minutes)
            
            # Apply the timeout
            await member.timeout(until, reason="Timed out by Kasane Teto fucking bitch")
            return True
        except Exception as e:
            print(f"Error timing out user: {e}")
            return False
    
    async def search_internet(self, query: str) -> str:
        """Search the internet for information"""
        try:
            # URL encode the query
            encoded_query = urllib.parse.quote(query)
            
            # Use SerpAPI for search (you'll need to set SERPAPI_KEY in environment variables)
            serp_api_key = os.getenv("googlekey")
            if not serp_api_key:
                return "I couldn't search the internet because the search API key is not set."
            
            url = f"https://serpapi.com/search.json?q={encoded_query}&api_key={serp_api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract organic results
                        results = []
                        if "organic_results" in data:
                            for result in data["organic_results"][:3]:  # Get top 3 results
                                title = result.get("title", "No title")
                                link = result.get("link", "No link")
                                snippet = result.get("snippet", "No description")
                                results.append(f"- {title}\n  {snippet}\n  URL: {link}")
                        
                        # Extract knowledge graph if available
                        if "knowledge_graph" in data:
                            kg = data["knowledge_graph"]
                            title = kg.get("title", "")
                            description = kg.get("description", "")
                            if title and description:
                                results.insert(0, f"Knowledge Graph: {title} - {description}")
                        
                        if results:
                            return "\n\n".join(results)
                        else:
                            return "No relevant results found."
                    else:
                        return f"Error searching the internet: {response.status}"
        except Exception as e:
            print(f"Error searching the internet: {e}")
            return f"I encountered an error while searching the internet: {str(e)}"
    
    # Helper function to check if user has admin permissions
    async def check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if the user has administrator permissions"""
        if not interaction.guild:
            return False
        
        # Get the user's permissions in the guild
        permissions = interaction.user.guild_permissions
        
        # Check if the user has administrator permissions
        if permissions.administrator:
            return True
        
        await interaction.followup.send("You need administrator permissions to use this command.")
        return False
    
    @app_commands.command(name="ai", description="Chat with Kasane Teto AI")
    async def slash_ai(self, interaction: discord.Interaction, prompt: str):
        """Slash command to chat with the AI"""
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        user_name = interaction.user.display_name
        guild_id = interaction.guild.id if interaction.guild else None
        channel_id = interaction.channel.id if interaction.channel else None
        
        try:
            response = await self.generate_response(user_id, user_name, prompt, guild_id, channel_id)
            await interaction.followup.send(response)
        except Exception as e:
            print(f"Error in slash_ai: {e}")
            await interaction.followup.send("Sorry, something went wrong with the AI response.")
    
    @app_commands.command(name="aiconfig", description="Configure your AI settings")
    async def slash_aiconfig(
        self, 
        interaction: discord.Interaction, 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None
    ):
        """Slash command to configure AI settings"""
        await interaction.response.defer()
        
        # Check if user has admin permissions
        if not await self.check_admin_permissions(interaction):
            return
        
        user_id = str(interaction.user.id)
        
        # Get current config or create new one
        if user_id not in self.user_configs:
            self.user_configs[user_id] = self.default_config.copy()
        
        # Update provided parameters
        if model is not None:
            # Check if model is in the free tier list
            free_models = [
                "mistralai/mistral-7b-instruct:free",
                "meta-llama/llama-2-13b-chat:free",
                "meta-llama/llama-2-70b-chat:free",
                "openchat/openchat-7b:free",
                "gryphe/mythomax-l2-13b:free",
                "nousresearch/nous-hermes-llama2-13b:free"
            ]
            
            if model in free_models:
                self.user_configs[user_id]["model"] = model
            else:
                await interaction.followup.send(f"Model `{model}` is not available in the free tier. Use `/aimodels` to see available models.")
                return
                
        if temperature is not None:
            self.user_configs[user_id]["temperature"] = max(0.0, min(2.0, temperature))
        if max_tokens is not None:
            self.user_configs[user_id]["max_tokens"] = max(1, min(4096, max_tokens))
        if top_p is not None:
            self.user_configs[user_id]["top_p"] = max(0.0, min(1.0, top_p))
        if frequency_penalty is not None:
            self.user_configs[user_id]["frequency_penalty"] = max(-2.0, min(2.0, frequency_penalty))
        if presence_penalty is not None:
            self.user_configs[user_id]["presence_penalty"] = max(-2.0, min(2.0, presence_penalty))
        
        # Save configurations
        self.save_configs()
        
        # Show current configuration
        config = self.user_configs[user_id]
        config_message = (
            "Your AI configuration has been updated:\n"
            f"- Model: `{config['model']}`\n"
            f"- Temperature: `{config['temperature']}`\n"
            f"- Max Tokens: `{config['max_tokens']}`\n"
            f"- Top P: `{config['top_p']}`\n"
            f"- Frequency Penalty: `{config['frequency_penalty']}`\n"
            f"- Presence Penalty: `{config['presence_penalty']}`"
        )
        
        await interaction.followup.send(config_message)
    
    @app_commands.command(name="aimodels", description="List available free AI models")
    async def slash_aimodels(self, interaction: discord.Interaction):
        """Slash command to list available free AI models"""
        await interaction.response.defer()
        
        # Check if user has admin permissions
        if not await self.check_admin_permissions(interaction):
            return
        
        models_message = (
            "Available Free AI models:\n"
            "- `mistralai/mistral-7b-instruct:free` (Default, good all-around model)\n"
            "- `meta-llama/llama-2-13b-chat:free` (Good for conversation)\n"
            "- `meta-llama/llama-2-70b-chat:free` (More powerful Llama 2 model)\n"
            "- `openchat/openchat-7b:free` (Optimized for chat)\n"
            "- `gryphe/mythomax-l2-13b:free` (Creative responses)\n"
            "- `nousresearch/nous-hermes-llama2-13b:free` (Knowledge-focused)\n\n"
            "Use `/aiconfig model:model_name` to change your model."
        )
        
        await interaction.followup.send(models_message)
    
    @app_commands.command(name="aichannel", description="Toggle AI responses to all messages in this channel")
    async def slash_aichannel(self, interaction: discord.Interaction):
        """Slash command to toggle AI responses to all messages in the current channel"""
        await interaction.response.defer()
        
        # Check if user has admin permissions
        if not await self.check_admin_permissions(interaction):
            return
        
        channel_id = interaction.channel.id
        
        if channel_id in self.active_channels:
            self.active_channels.remove(channel_id)
            await interaction.followup.send("I will no longer respond to all messages in this channel. I'll still respond to mentions and commands.")
        else:
            self.active_channels.add(channel_id)
            await interaction.followup.send("I will now respond to all messages in this channel!")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Prevent processing of the bot's own messages
        if message.author == self.bot.user:
            return
        
        # Let the bot's text commands handle their own messages
        if message.content.startswith("!"):
            await self.bot.process_commands(message)
            return
        
        # Get message context
        user_id = str(message.author.id)
        user_name = message.author.display_name
        guild_id = message.guild.id if message.guild else None
        channel_id = message.channel.id if message.channel else None
        
        # Check if the bot should respond
        should_respond = False
        response_prefix = ""
        
        # If the bot is mentioned
        if self.bot.user in message.mentions:
            should_respond = True
            prompt = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            if not prompt:
                prompt = "Hi there!"
        
        # If the message is in an active channel
        elif channel_id in self.active_channels:
            should_respond = True
            prompt = message.content
        
        # If the message contains the bot's name
        elif self.bot.user.name.lower() in message.content.lower():
            should_respond = True
            prompt = message.content
            response_prefix = f"{message.author.mention} "
        
        # Generate and send response if needed
        if should_respond:
            async with message.channel.typing():
                response = await self.generate_response(user_id, user_name, prompt, guild_id, channel_id)
                await message.reply(response_prefix + response)
        else:
            await self.bot.process_commands(message)

async def setup(bot: commands.Bot):
    # Check if AI_API_KEY is set
    if not os.getenv("AI_API_KEY"):
        print("WARNING: AI_API_KEY environment variable is not set. AI functionality will not work properly.")
        print("Get a free API key from https://openrouter.ai/keys")
    
    # Check if SERPAPI_KEY is set
    if not os.getenv("SERPAPI_KEY"):
        print("WARNING: SERPAPI_KEY environment variable is not set. Internet search functionality will not work.")
        print("Get a free API key from https://serpapi.com/")
    
    await bot.add_cog(OpenRouterCog(bot))
    print("OpenRouterCog loaded successfully.")
