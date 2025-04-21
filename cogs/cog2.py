import discord
from discord.ext import commands

class CogManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_loaded_cogs(self):
        """Return a sorted string of all loaded cog extensions."""
        if self.bot.extensions:
            return "\n".join(sorted(self.bot.extensions.keys()))
        return "No extensions loaded."

    @commands.hybrid_command(name="loadedcogs", help="Displays all loaded cogs/extensions.")
    @commands.is_owner()
    async def loadedcogs(self, ctx):
        loaded = self.format_loaded_cogs()
        message = f"Loaded Cogs:\n{loaded}"
        await ctx.send(f"```\n{message}\n```")

    @commands.hybrid_command(
        name="unmountcog",
        help="Disables/unloads a cog and reloads all other cogs. Usage: /unmountcog <cog_name>"
    )
    @commands.is_owner()
    async def unmountcog(self, ctx, cog: str):
        output_lines = []
        # If needed, prepend "cogs." to the cog name
        extension = cog if cog.startswith("cogs.") else f"cogs.{cog}"
        output_lines.append(f"Attempting to unmount cog: {extension}")

        # Check if the extension is loaded.
        if extension not in self.bot.extensions:
            await ctx.send(f"Cog `{extension}` is not currently loaded.")
            return

        try:
            self.bot.unload_extension(extension)
            output_lines.append(f"Successfully unmounted `{extension}`.")
        except Exception as e:
            output_lines.append(f"Failed to unmount `{extension}`: {e}")
            await ctx.send(f"```\n" + "\n".join(output_lines) + "\n```")
            return

        # Reload all remaining loaded cogs
        output_lines.append("Reloading remaining cogs:")
        for ext in list(self.bot.extensions.keys()):
            try:
                self.bot.reload_extension(ext)
                output_lines.append(f"Reloaded: {ext}")
            except Exception as e:
                output_lines.append(f"Failed to reload {ext}: {e}")

        output_lines.append("Currently loaded cogs:")
        output_lines.append(self.format_loaded_cogs())

        await ctx.send(f"```\n" + "\n".join(output_lines) + "\n```")

    @commands.hybrid_command(
        name="mountcog",
        help="Enables/loads a disabled cog and reloads all cogs. Usage: /mountcog <cog_name>"
    )
    @commands.is_owner()
    async def mountcog(self, ctx, cog: str):
        output_lines = []
        extension = cog if cog.startswith("cogs.") else f"cogs.{cog}"
        output_lines.append(f"Attempting to mount cog: {extension}")

        if extension in self.bot.extensions:
            await ctx.send(f"Cog `{extension}` is already loaded.")
            return

        try:
            self.bot.load_extension(extension)
            output_lines.append(f"Successfully mounted `{extension}`.")
        except Exception as e:
            output_lines.append(f"Failed to mount `{extension}`: {e}")
            await ctx.send(f"```\n" + "\n".join(output_lines) + "\n```")
            return

        # Reload all currently loaded cogs
        output_lines.append("Reloading all cogs:")
        for ext in list(self.bot.extensions.keys()):
            try:
                self.bot.reload_extension(ext)
                output_lines.append(f"Reloaded: {ext}")
            except Exception as e:
                output_lines.append(f"Failed to reload {ext}: {e}")

        output_lines.append("Currently loaded cogs:")
        output_lines.append(self.format_loaded_cogs())

        await ctx.send(f"```\n" + "\n".join(output_lines) + "\n```")

async def setup(bot):
    await bot.add_cog(CogManagerCog(bot))
