import discord
from discord.ext import commands

class IssueReportCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="issuereport", help="Sends a link to the repository's issues page.")
    async def issuereport(self, ctx):
        issues_link = "https://github.com/pancakes-proxy/codespaces-blank/issues"
        await ctx.send(f"Report or track issues here: {issues_link}")

async def setup(bot):
    await bot.add_cog(IssueReportCog(bot))
