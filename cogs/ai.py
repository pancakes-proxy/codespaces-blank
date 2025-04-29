import discord
from discord.ext import commands
import os
import aiohttp
import dotenv
from dotenv import load_dotenv

load_dotenv("/home/server/keys.env"

class OpenRouterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bo
        self.openrouter_api_key = os.environ.get("AI_API_KEY")
        if not self.openrouter_api_key:
            raise ValueError("AI_API_KEY environment variable not set.")
        self.system_prompt = "You are Kasane Teto idk what else"
        self.model = "google/gemini-2.0-flash-exp:free"
        self.auto_respond = True  # Set to True for automatic responses

    async def _query_openrouter(self, prompt, use_web_search=False):
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
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

    @commands.hybrid_command(name="ai", description="Ask Kasane Teto something.")
    async def ai(self, ctx: commands.Context, *, prompt: str):
        async with ctx.typing():
            response = await self._query_openrouter(prompt, use_web_search=True)
            await ctx.reply(response)

    @commands.hybrid_command(name="setsysprompt", description="Set the system prompt for Kasane Teto.")
    @commands.is_owner()  # Restrict this command to the bot owner
    async def setsysprompt(self, ctx: commands.Context, *, new_prompt: str):
        self.system_prompt = new_prompt
        await ctx.reply(f"System prompt updated to: `{self.system_prompt}`")

async def setup(bot):
    await bot.add_cog(OpenRouterCog(bot))
