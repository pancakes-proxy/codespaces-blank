import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class Debug(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

@app_commands.command(name="amionline", description="Check if the bot is online.")
async def amionline(self, interaction: discord.Interaction):
    """Responds to the user confirming the bot is online."""
    await interaction.response.send_message("Yes, I'm online!")
