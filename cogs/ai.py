import discord
from discord.ext import commands
from discord import app_commands
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv("/home/server/keys.env/")
OPENROUTER_API_KEY = os.getenv("AI_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("AI_API_KEY environment variable not set.")

class OpenRouterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.system_prompt = "You are Kasane Teto idk what else"
        self.model = "google/gemini-2.0-flash-exp:free"
        self.auto_respond = True  # Set to True for automatic responses

    async def _query_openrouter(self, prompt, use_web_search=False):
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/yourusername/yourbotname",  # Replace with your bot's info
            "X-Client-Type": "discord-bot",
            "X-Client-Version": discord.__version__,
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }
        if use_web_search:
            data["tool_choice"] = {"type": "code_interpreter"}
            data["tools"] = [{"type": "code_interpreter"}]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data
            ) as response:
                if response.status == 200:
                    json_response = await response.json()
                    if json_response and "choices" in json_response and json_response["choices"]:
                        return json_response["choices"][0]["message"]["content"]
                    else:
                        return "Error: No response from OpenRouter."
                else:
                    error_data = await response.json()
                    return f"OpenRouter API Error: {response.status} - {error_data.get('error', {}).get('message', 'Unknown error')}"

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if self.auto_respond and not message.content.startswith(self.bot.command_prefix):
            async with message.channel.typing():
                response = await self._query_openrouter(message.content, use_web_search=True)
                await message.reply(response)

    @app_commands.command(name="ai", description="Ask Kasane Teto something.")
    async def ai(self, interaction: discord.Interaction, *, prompt: str):
        async with interaction.channel.typing():
            response = await self._query_openrouter(prompt, use_web_search=True)
            await interaction.response.send_message(response)

    @app_commands.command(name="setsysprompt", description="Set the system prompt for Kasane Teto.")
    @app_commands.checks.is_owner()
    async def setsysprompt(self, interaction: discord.Interaction, *, new_prompt: str):
        self.system_prompt = new_prompt
        await interaction.response.send_message(f"System prompt updated to: `{self.system_prompt}`")

async def setup(bot):
    await bot.add_cog(OpenRouterCog(bot))

if __name__ == '__main__':
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user.name}')
        await bot.load_extension(__name__)
        # This is crucial for syncing application commands globally
        await bot.tree.sync()

    bot.run(TOKEN)
