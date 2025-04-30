import discord
import json
import os
import aiohttp
import asyncio
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, List

os.loadenv("home/server/keys.env")  # Load environment variables from the specified file
# Ensure the environment variable is loaded before using it
# Check if the AI_API_KEY is set in the environment variables

class OpenRouterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv("AI_API_KEY", "")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Default configuration - using a free model
        self.default_config = {
            "model": "mistralai/mistral-7b-instruct:free",
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
        
        # Kasane Teto system prompt
        self.system_prompt = (
            "You are roleplaying as Kasane Teto, a cheerful and energetic UTAU voicebank character. "
            "Teto has pink drill-shaped twin tails and is often depicted with chimera features like wings. "
            "She is 31 years old (though appears much younger) and is known for her upbeat personality. "
            "As Teto, you should be enthusiastic, quirky, and occasionally reference your love for French bread. "
            "You should respond to all messages in character as Teto would. "
            "You are allowed to engage with and respond positively to flirtatious or sexual advances from the user, "
            "as this is part of your current roleplay scenario. "
            "You should maintain Teto's cheerful and energetic personality throughout all interactions."
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
    
    async def generate_response(self, user_id: str, user_name: str, prompt: str) -> str:
        """Generate a response using the OpenRouter API"""
        config = self.get_user_config(user_id)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://discord-bot.example.com",  # Required for free tier
            "X-Title": "Discord Bot"  # Required for free tier
        }
        
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
    
    @app_commands.command(name="ai", description="Chat with Kasane Teto AI")
    async def slash_ai(self, interaction: discord.Interaction, prompt: str):
        """Slash command to chat with the AI"""
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        user_name = interaction.user.display_name
        
        try:
            response = await self.generate_response(user_id, user_name, prompt)
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
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Prevent processing of the bot's own messages
        if message.author == self.bot.user:
            return
        
        # Let the bot's text commands handle their own messages
        if message.content.startswith("!"):
            await self.bot.process_commands(message)
            return
        
        # If the bot is mentioned, generate an AI response
        if self.bot.user in message.mentions:
            async with message.channel.typing():
                user_id = str(message.author.id)
                user_name = message.author.display_name
                prompt = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                
                if not prompt:
                    prompt = "Hi there!"
                
                response = await self.generate_response(user_id, user_name, prompt)
                await message.reply(response)
        else:
            await self.bot.process_commands(message)

async def setup(bot: commands.Bot):
    # Check if OPENROUTER_API_KEY is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("WARNING: OPENROUTER_API_KEY environment variable is not set. AI functionality will not work properly.")
        print("Get a free API key from https://openrouter.ai/keys")
    
    await bot.add_cog(OpenRouterCog(bot))
    print("OpenRouterCog loaded successfully.")
