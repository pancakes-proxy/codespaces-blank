import discord
from discord.ext import commands

class BotAnnounceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(
        name="botannounce",
        description="Send an announcement to all joined servers (Owner only)."
    )
    async def botannounce(self, interaction: discord.Interaction, text: str):
        # Check that only the bot owner can use this command.
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "You are not authorized to use this command.",
                ephemeral=True
            )
            return

        sent_count = 0
        # Iterate over every guild the bot is a member of.
        for guild in self.bot.guilds:
            # First, try the guild's system channel.
            channel = guild.system_channel
            if channel and channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(text)
                    sent_count += 1
                    continue  # Move to the next guild after a successful send.
                except Exception as e:
                    print(f"Failed sending in system channel of {guild.name} ({guild.id}): {e}")
            # If no system channel or unable to send there, iterate through text channels.
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    try:
                        await ch.send(text)
                        sent_count += 1
                        break  # Exit loop once a valid channel is found.
                    except Exception as e:
                        print(f"Failed sending in channel {ch.name} of {guild.name} ({guild.id}): {e}")
        await interaction.response.send_message(
            f"Announcement sent to {sent_count} guild(s).",
            ephemeral=True
        )

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        # Generic error handler for this cog's slash command.
        await interaction.response.send_message(
            "An error occurred while processing the command.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(BotAnnounceCog(bot))
