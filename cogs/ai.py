import os
import discord
from discord import app_commands
from discord.ext import commands
import random
from dotenv import load_dotenv
import aiohttp



# Load environment variables - note the removal of the trailing slash.
load_dotenv('/home/server/keys.env')
API_KEY = os.getenv('AI_API_KEY')

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.chat_histories = {}
        self.current_model = "google/gemma-7b-it:free"  # default model
        self.system_prompt = "you are kasane teto"  # default system prompt
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Referer": "https://github.com/zacr/discordbot",
        }
      
    @app_commands.command(name='setprompt')
    async def setprompt(self, interaction: discord.Interaction, *, new_prompt: str):
        """Change the system prompt."""
        self.system_prompt = new_prompt
        await interaction.response.send_message(f"System prompt changed to: {new_prompt}")

    @app_commands.command(name='ai')
    async def ai(self, interaction: discord.Interaction, *, prompt: str):
        """Send a prompt to the AI model."""
        try:
            # Initialize chat history with system prompt if not exists
            if interaction.user.id not in self.chat_histories:
                self.chat_histories[interaction.user.id] = [{"role": "system", "content": self.system_prompt}]
            
            # Add user message to history
            self.chat_histories[interaction.user.id].append({"role": "user", "content": prompt})

            # Prepare the payload
            payload = {
                "model": self.current_model,
                "messages": self.chat_histories[interaction.user.id]
            }

            # Use aiohttp for an asynchronous POST request
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=self.headers, json=payload) as resp:
                    response_data = await resp.json()

            # Check if the response contains the expected data
            if "choices" not in response_data or not response_data["choices"]:
                await interaction.response.send_message("No valid response received from the AI API.", ephemeral=True)
                return

            ai_response = response_data['choices'][0]['message']['content']
            self.chat_histories[interaction.user.id].append({"role": "assistant", "content": ai_response})
            await interaction.response.send_message(ai_response)

        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
        
    @app_commands.command(name='clearchat')
    async def clearchat(self, interaction: discord.Interaction):
        """Clear your chat history with the AI."""
        if interaction.user.id in self.chat_histories:
            del self.chat_histories[interaction.user.id]
            await interaction.response.send_message("Chat history cleared!")
        else:
            await interaction.response.send_message("No chat history to clear!")

    @app_commands.command(name='setmodel')
    async def setmodel(self, interaction: discord.Interaction, model_name: str):
        """Change the AI model."""
        allowed_models = ["google/gemma-7b-it:free", "google/gemma-2b-it:free"]
        if model_name in allowed_models:
            self.current_model = model_name
            await interaction.response.send_message(f"Model changed to {model_name}")
        else:
            await interaction.response.send_message(f"Invalid model. Available models: {', '.join(allowed_models)}")

async def setup(bot):
    await bot.add_cog(AI(bot))