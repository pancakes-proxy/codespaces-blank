import discord
from discord.ext import commands

class ApplicationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # This will store the Google Forms link for applications.
        self.apply_link = None

    # --------------------------------------------------------------------------
    # Set Application Link Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="setap", help="Set the Google Forms link for applications. (Usage: /setap <google_forms_link>)")
    @commands.has_permissions(administrator=True)
    async def setap(self, ctx, link: str):
        # Optionally, add basic validation for the link here.
        self.apply_link = link
        await ctx.send(f"Application link has been set to:\n{link}")

    # --------------------------------------------------------------------------
    # Clear Application Link Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="clearap", help="Clear the currently set Google Forms link for applications.")
    @commands.has_permissions(administrator=True)
    async def clearap(self, ctx):
        self.apply_link = None
        await ctx.send("Application link has been cleared.")

    # --------------------------------------------------------------------------
    # Apply Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="apply", help="Receive the application link via DM.")
    async def apply(self, ctx):
        if self.apply_link is None:
            await ctx.send("No application link has been set yet. Please contact an administrator.")
            return

        try:
            # Attempt to create or fetch the user's DM channel
            dm_channel = await ctx.author.create_dm()
            await dm_channel.send(f"Here is your application link:\n{self.apply_link}")
            await ctx.send("I've sent the application link to your DMs.")
        except Exception as e:
            await ctx.send(f"Unable to DM you the application link: {e}")

async def setup(bot):
    await bot.add_cog(ApplicationCog(bot))
