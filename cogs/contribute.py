import discord
from discord.ext import commands

class SourceCodeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="sourcecode", help="Displays the bot's source code repository link.")
    async def sourcecode(self, ctx):
        source_link = "https://github.com/pancakes-proxy/codespaces-blank.git"
        await ctx.send(f"Source code repository: {source_link}")

async def setup(bot):
    await bot.add_cog(SourceCodeCog(bot))
