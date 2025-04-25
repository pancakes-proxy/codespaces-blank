import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv('/home/server/keys.env/')
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
            "HTTP-Referer": "https://github.com/zacr/discordbot",  # Replace with your project URL
        }

    @commands.command()
    async def setprompt(self, ctx, *, new_prompt: str):
        """Change the system prompt"""
        self.system_prompt = new_prompt
        await ctx.send(f"System prompt changed to: {new_prompt}")

    @commands.command()
    async def ai(self, ctx, *, prompt: str):
        """Send a prompt to the AI model"""
        try:
            # Get or create chat history for this user
            if ctx.author.id not in self.chat_histories:
                self.chat_histories[ctx.author.id] = []

            # Add user message to history
            self.chat_histories[ctx.author.id].append({"role": "user", "content": prompt})

            # Prepare the request
            payload = {
                "model": self.current_model,
                "messages": self.chat_histories[ctx.author.id]
            }

            # Make API request
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response_data = response.json()

            # Add AI response to history
            ai_response = response_data['choices'][0]['message']['content']
            self.chat_histories[ctx.author.id].append({"role": "assistant", "content": ai_response})

            # Send response
            await ctx.send(ai_response)

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    @commands.command()
    async def clearchat(self, ctx):
        """Clear your chat history with the AI"""
        if ctx.author.id in self.chat_histories:
            self.chat_histories[ctx.author.id] = []
            await ctx.send("Chat history cleared!")
        else:
            await ctx.send("No chat history to clear!")

    @commands.command()
    async def setmodel(self, ctx, model_name: str):
        """Change the AI model"""
        allowed_models = ["google/gemma-7b-it:free", "google/gemma-2b-it:free"]
        if model_name in allowed_models:
            self.current_model = model_name
            await ctx.send(f"Model changed to {model_name}")
        else:
            await ctx.send(f"Invalid model. Available models: {', '.join(allowed_models)}")

async def setup(bot):
    await bot.add_cog(AI(bot))