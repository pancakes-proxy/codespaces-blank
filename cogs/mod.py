import discord
from discord.ext import commands
from datetime import datetime, timedelta

class ModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # This will store the user who receives reports.
        self.report_recipient = None  

    # --------------------------------------------------------------------------
    # Kick Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="kick", help="Kick a member from the server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked.\n**Reason:** {reason}")
        except Exception as e:
            await ctx.send(f"Failed to kick {member.mention}: {e}")

    # --------------------------------------------------------------------------
    # Ban Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="ban", help="Ban a member from the server.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned.\n**Reason:** {reason}")
        except Exception as e:
            await ctx.send(f"Failed to ban {member.mention}: {e}")

    # --------------------------------------------------------------------------
    # Warn Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="warn", help="Warn a member. (This command just announces the warning.)")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            # You might want to log this warning or record it in a database/file.
            await ctx.send(f"{member.mention} has been warned.\n**Reason:** {reason}")
        except Exception as e:
            await ctx.send(f"Failed to warn {member.mention}: {e}")

    # --------------------------------------------------------------------------
    # Timeout Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="timeout", help="Timeout a member for a specified duration (in seconds).")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: int, *, reason: str = "No reason provided"):
        try:
            until = datetime.utcnow() + timedelta(seconds=duration)
            await member.edit(timeout=until, reason=reason)
            await ctx.send(f"{member.mention} has been timed out for {duration} seconds.\n**Reason:** {reason}")
        except Exception as e:
            await ctx.send(f"Failed to timeout {member.mention}: {e}")

    # --------------------------------------------------------------------------
    # Server Lockdown Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="serverlockdown", help="Lock down the entire server by disabling send messages for @everyone.")
    @commands.has_permissions(manage_channels=True)
    async def serverlockdown(self, ctx):
        try:
            locked_count = 0
            for channel in ctx.guild.text_channels:
                overwrite = channel.overwrites_for(ctx.guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                locked_count += 1
            await ctx.send(f"Server lockdown activated. Locked {locked_count} text channels.")
        except Exception as e:
            await ctx.send(f"Failed to lockdown the server: {e}")

    # --------------------------------------------------------------------------
    # Channel Lockdown Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="chanlockdown", help="Lockdown a specific text channel by disabling send messages for @everyone. "
                                                      "If no channel is provided, the current channel is used.")
    @commands.has_permissions(manage_channels=True)
    async def chanlockdown(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            await ctx.send(f"{channel.mention} has been locked down.")
        except Exception as e:
            await ctx.send(f"Failed to lockdown {channel.mention}: {e}")

    # --------------------------------------------------------------------------
    # Set Report Recipient Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="setreport", help="Set the user that will receive reports (usage: /setreport @User).")
    @commands.has_permissions(administrator=True)
    async def setreport(self, ctx, user: discord.User):
        self.report_recipient = user
        await ctx.send(f"Report recipient has been set to {user.mention}")

    # --------------------------------------------------------------------------
    # Report Command
    # --------------------------------------------------------------------------
    @commands.hybrid_command(name="report", help="Report a user. This command sends a DM to the designated report recipient.")
    async def report(self, ctx, user: discord.User, *, reason: str = "No reason provided"):
        if self.report_recipient is None:
            await ctx.send("No report recipient has been set yet. Please ask an administrator to set one using /setreport.")
            return
        try:
            report_message = (
                f"**Report Received**\n"
                f"**Reported by:** {ctx.author.mention}\n"
                f"**User Reported:** {user.mention}\n"
                f"**Reason:** {reason}\n"
                f"**Server:** {ctx.guild.name}\n"
                f"**Channel:** {ctx.channel.name}"
            )
            await self.report_recipient.send(report_message)
            await ctx.send("Your report has been submitted successfully.")
        except Exception as e:
            await ctx.send(f"Failed to submit your report: {e}")

async def setup(bot):
    await bot.add_cog(ModCog(bot))
