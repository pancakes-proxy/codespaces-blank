import discord
from discord.ext import commands
from datetime import datetime, timedelta

# Interactive dropdown to view current Automod configuration
class ConfigSelect(discord.ui.Select):
    def __init__(self, cog):
        options = [
            discord.SelectOption(
                label="Filtered Words",
                description="View/modify words that the bot filters."
            ),
            discord.SelectOption(
                label="Punishment Settings",
                description="View/modify punishments for filtered words."
            )
        ]
        super().__init__(
            placeholder="Choose an automod configuration option...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Filtered Words":
            filtered = self.cog.filtered_words
            content = "Current filtered words:\n" + "\n".join(filtered) if filtered else "No words are currently filtered."
            embed = discord.Embed(
                title="Filtered Words Configuration",
                description=content,
                color=discord.Color.green()
            )
        elif self.values[0] == "Punishment Settings":
            ps = self.cog.punishment_settings
            if ps:
                content = "\n".join([f"**{k}**: {v}" for k, v in ps.items()])
            else:
                content = "No punishment settings configured."
            embed = discord.Embed(
                title="Punishment Settings Configuration",
                description=content,
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="Error",
                description="Invalid option selected.",
                color=discord.Color.red()
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# A simple view that contains the dropdown, which will time out after 60s.
class AutoModConfigView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=60)
        self.add_item(ConfigSelect(cog))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

# The primary cog that monitors messages and acts if a filtered word is detected.
class AutoModConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Example default configuration.
        self.filtered_words = ["badword1", "badword2"]
        self.punishment_settings = {
            "Warning": True,             # Send a warning DM.
            "Message Deletion": True,      # Delete the message.
            "Timeout (seconds)": 60,       # Timeout for 60 seconds.
            "Ban": False                 # Ban is disabled by default.
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from bots or outside a guild.
        if message.author.bot or not message.guild:
            return

        # Check if the message contains any of the filtered words.
        message_lower = message.content.lower()
        if not any(word.lower() in message_lower for word in self.filtered_words):
            return  # No issue detected; do nothing.

        actions_taken = []

        # 1. Warning: DM the user.
        if self.punishment_settings.get("Warning", False):
            try:
                warning_msg = "Warning: Your message contained language that is not allowed in this server. Please follow the rules."
                await message.author.send(warning_msg)
                actions_taken.append("Warned")
            except Exception as e:
                actions_taken.append("Warning DM failed")

        # 2. Message Deletion: Delete the offending message.
        if self.punishment_settings.get("Message Deletion", False):
            try:
                await message.delete()
                actions_taken.append("Message Deleted")
            except Exception as e:
                actions_taken.append("Message deletion failed")

        # 3. Timeout: Apply a temporary timeout if configured.
        timeout_seconds = self.punishment_settings.get("Timeout (seconds)", 0)
        if timeout_seconds > 0:
            try:
                until = datetime.utcnow() + timedelta(seconds=timeout_seconds)
                await message.author.edit(timeout=until, reason="Automod: Timeout for using a filtered word")
                actions_taken.append(f"Timed out for {timeout_seconds} seconds")
            except Exception as e:
                actions_taken.append("Timeout failed")

        # 4. Ban: Ban the user if set.
        if self.punishment_settings.get("Ban", False):
            try:
                await message.guild.ban(message.author, reason="Automod: Banned for using a filtered word")
                actions_taken.append("Banned")
            except Exception as e:
                actions_taken.append("Ban failed")

        # Optionally, you might want to log these actions in a mod log channel.
        # For example:
        # mod_log = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        # if mod_log:
        #     await mod_log.send(f"Automod actions on {message.author.mention}: {', '.join(actions_taken)}")

        # Ensure other commands get processed.
        await self.bot.process_commands(message)

    @commands.hybrid_group(name="automod", invoke_without_command=True, help="Automod command group. Use /automod config to configure automod settings.")
    async def automod(self, ctx):
        await ctx.send("Please specify a subcommand. For example: `/automod config`", ephemeral=True)

    @automod.command(name="config", help="Displays a menu to configure the bot's automod settings.")
    async def config(self, ctx):
        embed = discord.Embed(
            title="AutoMod Configuration Menu",
            description=(
                "Select an option from the dropdown below to view or modify automod settings.\n\n"
                "• **Filtered Words:** Words that the bot is set to filter.\n"
                "• **Punishment Settings:** Actions taken when a filtered word is detected."
            ),
            color=discord.Color.blue()
        )
        view = AutoModConfigView(self)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(AutoModConfigCog(bot))
