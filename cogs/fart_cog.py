import discord
from discord.ext import commands
from discord import app_commands
import random

possible_responses = [
    "{user} just let one rip on {target}!",
    "{user} delivered a silent but deadly fart to {target}...",
    "{user} farted on {target}!",
    "{user} unleashed a thunderous fart at {target}.",
    "{user} farted so hard at {target} that the room shook!",
    "{user} farted on {target} and it was so loud that it blew up the room!"
]

class FartCog(commands.Cog): 
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fart", description="Fart on a user.")
    async def slay(self, interaction: discord.Interaction, member: discord.Member):
        response = random.choice(possible_responses).format(user=interaction.user.mention, target=member.mention)
        await interaction.response.send_message(response)

async def setup(bot):
    await bot.add_cog(FartCog(bot))