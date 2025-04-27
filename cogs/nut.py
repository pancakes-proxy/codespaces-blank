import discord
from discord import app_commands
from discord.ext import commands

class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sa", description="sa a user.")
    async def wave(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} groped {member.mention} on a japanese train")

    @app_commands.command(name="bootyfuck", description="bootyfuck to a user.")
    async def backshots(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} fucked {member.mention} in they ass")

    @app_commands.command(name="rape", description="rape a user.")       
    async def rape(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user} raped {member.mention}")

async def setup(bot):
    await bot.add_cog(ExampleCog(bot))