# cogs/core.py
import os
import platform
import psutil
import discord
from discord.ext import commands
from discord import app_commands
import shutil
import subprocess
import sys
import asyncio
import logging

class Core(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sysinfo", description="Shows the hardware information of the server.")
    async def sysinfo(self, interaction: discord.Interaction):
        # (The CPU, RAM, and other details are hard-coded here as an example.)
        embed = discord.Embed(title="Kasanes pc >.<", color=discord.Color.blue())
        embed.add_field(name="System", value="PowerEdge R7715 ラックサーバー", inline=False)
        embed.add_field(name="OS", value="ubuntu 24.10", inline=False)
        embed.add_field(name="Processor", value="AMD EPYC 9175F 4.20GHz", inline=False)
        embed.add_field(name="RAM", value="768 GB", inline=False)
        embed.add_field(name="Disk Space", value="480 GB", inline=False)
        embed.add_field(name="Server Name", value="Freaky teto :3", inline=False)
    
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="status", description="Sets the bot's status to the provided text.")
    async def status(self, interaction: discord.Interaction, text: str):
        await self.bot.change_presence(activity=discord.Game(name=text))
        await interaction.response.send_message(f"Bot status updated to: **{text}**")

    @app_commands.command(name="user", description="Changes the bot's nickname to the provided text.")
    async def user(self, interaction: discord.Interaction, text: str):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        try:
            await interaction.guild.me.edit(nick=text)
            await interaction.response.send_message(f"Bot nickname changed to: **{text}**")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to change my nickname.", ephemeral=True)

    @app_commands.command(name="say", description="Make the bot say something.")
    async def say(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(f"Message sent: {message}", ephemeral=True)
        await interaction.channel.send(message)

    @app_commands.command(name="help", description="Lists all available commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Help Command",
            description="Here is a list of all the available commands:",
            color=discord.Color.blurple()
        )
        commands_list = [
            ("/sysinfo", "Shows the hardware information of the server."),
            ("/status", "Sets the bot's status to the provided text."),
            ("/user", "Changes the bot's nickname."),
            ("/ping", "Pings a server and returns the result."),
            ("/credits", "Displays the credits for the bot."),
            ("/shop", "Displays a joke menu of snacks."),
            ("/developersite", "Sends a link to the developer's website."),
            ("/discordsupportinvite", "Sends a link to the Discord support server."),
            ("/wave", "Waves at a user."),
            ("/hug", "Hugs a user."),
            ("/kiss", "Kisses a user."),
            ("/punch", "Punches a user."),
            ("/kick", "Kicks a user."),
            ("/banhammer", "Uses the banhammer on a user."),
            ("/marry", "Proposes to a user."),
            ("/divorce", "Divorces a user."),
            ("/slap", "Slaps a user."),
            ("/snatch", "Playfully snatches a user."),
            ("/triplebaka", "Sends a link to the Triple Baka video."),
            ("/spotify", "Sends a link to a Spotify playlist."),
            ("/coinflip", "Flips a coin by picking heads or tails."),
            ("/rps", "Plays Rock, Paper, Scissors with the bot.")
        ]
        for name, desc in commands_list:
            embed.add_field(name=name, value=desc, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="credits", description="Displays the credits for the bot.")
    async def credits(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Bot Credits",
            description="This bot was developed with contributions from the following:",
            color=discord.Color.gold()
        )
        embed.add_field(name="Developer", value="zacarias posey - https://staffteam.learnhelp.cc/zac.html", inline=False)
        embed.add_field(name="Contributors", value="Izzy - https://staffteam.learnhelp.cc/izzy.html", inline=False)
        embed.add_field(name="Contributors", value="Milly - https://staffteam.learnhelp.cc/milly.html", inline=False)
        embed.add_field(name="Special Thanks", value="Slipstream", inline=False)
        embed.add_field(name="Powered By", value="OpenAI, Discord API", inline=False)
        embed.add_field(name="Website", value="https://learnhelp.cc", inline=False)
        embed.add_field(name="Discord Server", value="https://discord.gg/9CFwFRPNH4", inline=False)
        embed.set_footer(text="Thank you for using the bot!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="update", description="Updates the bot code from GitLab and restarts the bot. (Admin Only)")
    async def update(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return
        await interaction.response.send_message("Initiating update. The bot will restart shortly...")
        target_dir = "/home/server/wdiscordbot/"
        repo_url = "https://github.com/pancakes-proxy/wdiscordbot.git"
        restart_script = "/home/server/wdiscordbot/bot.py"

        try:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
                await interaction.followup.send(f"Removed directory: {target_dir}")
            else:
                await interaction.followup.send(f"Directory {target_dir} does not exist; proceeding with clone...")
            subprocess.run(["git", "clone", repo_url, target_dir], check=True)
            await interaction.followup.send("Repository cloned successfully.")
        except Exception as e:
            error_msg = f"Update failed: {e}"
            print(error_msg)
            await interaction.followup.send(error_msg)
            return
        os.execv(sys.executable, [sys.executable, restart_script])
        await interaction.response.send_message("Bot has updated to the latest commit and is restarting...")

        
    @app_commands.command(name="temps", description="Runs the 'sensors' command and sends its output to chat.")
    async def temps(self, interaction: discord.Interaction):
        """Executes the sensors command and returns the output."""
        try:
            # Run the 'sensors' command asynchronously
            process = await asyncio.create_subprocess_exec(
                "sensors",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            # Get the command output: prefer stdout, fallback to stderr if needed.
            output = stdout.decode("utf-8").strip() or stderr.decode("utf-8").strip() or "No output."
        except Exception as e:
            output = f"Error executing sensors command: {e}"

        # If the output is too long for a single message, send it as a file.
        if len(output) > 1900:  # leave some room for Discord formatting
            file_name = "temps.txt"
            with open(file_name, "w") as f:
                f.write(output)
            await interaction.response.send_message("Output was too long; see attached file:", file=discord.File(file_name))
        else:
            # Send output wrapped in a code block for clarity.
            await interaction.response.send_message(f"```\n{output}\n```")

async def setup(bot: commands.Bot):
    await bot.add_cog(Core(bot))