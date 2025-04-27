import discord
from discord import app_commands
from discord.ext import commands

class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sa", description="sa a user.")
    async def wave(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} groped {member.mention} on a japanese train")

    @app_commands.command(name="backshots", description="Give backshots to a user.")
    async def backshots(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} gave backshots to {member.mention}")

    @app_commands.command(name="rape", description="rape a user.")       
    async def rape(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user} raped {member.mention}")

    @app_commands.command(name="suicide", description="user that runs it shoots themselves.")    
    async def suicide(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{interaction.user.mention} committed suicide")

async def setup(bot):
    await bot.add_cog(ExampleCog(bot))