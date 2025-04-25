import os
import discord
from discord import app_commands
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
    async def setprompt(self, ctx, *, new_prompt: str):
        """Change the system prompt."""
        self.system_prompt = new_prompt
        await ctx.send(f"System prompt changed to: {new_prompt}")

    @app_commands.command(name='ai')
    async def ai(self, ctx, *, prompt: str):
        """Send a prompt to the AI model."""
        try:
            # Initialize chat history with system prompt if not exists
            if ctx.author.id not in self.chat_histories:
                self.chat_histories[ctx.author.id] = [{"role": "system", "content": self.system_prompt}]
            
            # Add user message to history
            self.chat_histories[ctx.author.id].append({"role": "user", "content": prompt})

            # Prepare the payload
            payload = {
                "model": self.current_model,
                "messages": self.chat_histories[ctx.author.id]
            }

            # Use aiohttp for an asynchronous POST request
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=self.headers, json=payload) as resp:
                    response_data = await resp.json()

            # Check if the response contains the expected data
            if "choices" not in response_data or not response_data["choices"]:
                await ctx.send("No valid response received from the AI API.")
                return

            ai_response = response_data['choices'][0]['message']['content']
            self.chat_histories[ctx.author.id].append({"role": "assistant", "content": ai_response})
            await ctx.send(ai_response)

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    @app_commands.command(name='clearchat')
    async def clearchat(self, ctx):
        """Clear your chat history with the AI."""
        if ctx.author.id in self.chat_histories:
            del self.chat_histories[ctx.author.id]
            await ctx.send("Chat history cleared!")
        else:
            await ctx.send("No chat history to clear!")

    @app_commands.command(name='setmodel')
    async def setmodel(self, ctx, model_name: str):
        """Change the AI model."""
        allowed_models = ["google/gemma-7b-it:free", "google/gemma-2b-it:free"]
        if model_name in allowed_models:
            self.current_model = model_name
            await ctx.send(f"Model changed to {model_name}")
        else:
            await ctx.send(f"Invalid model. Available models: {', '.join(allowed_models)}")

async def setup(bot):
    await bot.add_cog(AI(bot))