import os
import shutil
import subprocess
import discord
from discord.ext import commands

class UpdateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="update")
    @commands.is_owner()
    async def update(self, ctx):
        output_lines = []
        base_dir = "/home/server/wdiscordbot/"

        # Step 1: Delete the directory /home/server/wdiscordbot/
        output_lines.append(f"Deleting directory {base_dir} ...")
        try:
            if os.path.exists(base_dir):
                shutil.rmtree(base_dir)
                output_lines.append("Directory deleted successfully.")
            else:
                output_lines.append(f"Directory {base_dir} does not exist.")
        except Exception as e:
            output_lines.append(f"Error deleting directory: {e}")

        # Step 2: Clone the GitHub repository to /home/server/wdiscordbot/
        output_lines.append("Cloning repository from https://github.com/pancakes-proxy/codespaces-blank.git ...")
        try:
            result = subprocess.run(
                ["git", "clone", "https://github.com/pancakes-proxy/codespaces-blank.git", base_dir],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                output_lines.append("Repository cloned successfully.")
            else:
                output_lines.append(f"Git clone error: {result.stderr.strip()}")
        except Exception as e:
            output_lines.append(f"Exception during cloning: {e}")

        # Step 3: Reload all cogs from /home/server/wdiscordbot/cogs
        cogs_path = os.path.join(base_dir, "cogs")
        output_lines.append(f"Reloading cogs from {cogs_path} ...")
        try:
            if os.path.exists(cogs_path):
                for filename in os.listdir(cogs_path):
                    # Ignore __init__.py if present
                    if filename.endswith(".py") and filename != "__init__.py":
                        cog_name = filename[:-3]
                        extension = f"cogs.{cog_name}"
                        try:
                            self.bot.reload_extension(extension)
                            output_lines.append(f"Reloaded extension: {extension}")
                        except Exception as e:
                            output_lines.append(f"Failed to reload {extension}: {e}")
            else:
                output_lines.append(f"Cogs directory {cogs_path} not found.")
        except Exception as e:
            output_lines.append(f"Error reloading cogs: {e}")

        # Step 4: Sync slash commands with Discord
        output_lines.append("Syncing slash commands ...")
        try:
            synced = await self.bot.tree.sync()
            output_lines.append(f"Synced {len(synced)} commands.")
        except Exception as e:
            output_lines.append(f"Error syncing commands: {e}")

        # Step 5: Send the output back to the channel
        final_output = "Update finished:\n" + "\n".join(output_lines)
        await ctx.send(f"```\n{final_output}\n```")

async def setup(bot):
    await bot.add_cog(UpdateCog(bot))
