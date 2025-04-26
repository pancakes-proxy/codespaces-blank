import discord
import subprocess
from discord.ext import commands
from discord import app_commands

class ShellCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shell", description="Run a shell command without exception handling")
    async def shell(self, interaction: discord.Interaction, command: str):
        # Run the provided command with no exception handling.
        # WARNING: This allows arbitrary command execution and is very dangerous.
        result = subprocess.run(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # Combine standard output and standard error.
        output = result.stdout + result.stderr
        if not output:
            output = "No output."

        # Return the result in a code block.
        await interaction.response.send_message(f"```\n{output}\n```")

async def setup(bot: commands.Bot):
    await bot.add_cog(ShellCog(bot))