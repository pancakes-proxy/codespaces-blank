import os
import json
import discord
from discord.ext import commands
from discord import app_commands

# Set the directory for server configuration files.
CONFIG_DIR = "/home/server/serverconfig"

# A custom Select component. Each option represents one command.
class CommandSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Select commands to block",
            min_values=0,
            max_values=len(options),
            options=options
        )

# A View that holds the Select to block/unblock commands as well as an Update button.
class CommandBlockView(discord.ui.View):
    def __init__(self, cog, guild_id: int, commands_list: list[str]):
        super().__init__(timeout=180)
        self.cog = cog
        self.guild_id = guild_id
        self.commands_list = commands_list

        # Build options for the select menu.
        options = []
        # Get the set of currently blocked commands for this guild.
        blocked_cmds = self.cog.disabled_commands.get(guild_id, set())
        for cmd in commands_list:
            options.append(discord.SelectOption(
                label=cmd,
                description="Blocked" if cmd in blocked_cmds else "Allowed",
                default=(cmd in blocked_cmds),
                value=cmd
            ))
        self.select = CommandSelect(options)
        self.add_item(self.select)

    @discord.ui.button(label="Update", style=discord.ButtonStyle.primary)
    async def update(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verify that the user updating the settings has admin permissions.
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need admin permissions to update settings.", ephemeral=True)
            return

        # The selected values indicate the commands to block.
        selected = self.select.values
        self.cog.disabled_commands[self.guild_id] = set(selected)
        # Save the updated settings to file.
        self.cog.save_config(self.guild_id)
        # Rebuild the embed to reflect the changes.
        embed = self.cog.create_settings_embed(self.guild_id)
        await interaction.response.edit_message(embed=embed, view=self)

class ServerSettings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # This dictionary maps guild IDs to a set of command names that are blocked.
        self.disabled_commands = {}

        # Ensure the config directory exists.
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def config_filepath(self, guild_id: int) -> str:
        """Return the configuration file path for a given guild."""
        return os.path.join(CONFIG_DIR, f"{guild_id}.json")

    def load_config(self, guild_id: int):
        """Load the configuration for the guild from its JSON file."""
        filepath = self.config_filepath(guild_id)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                disabled = set(data.get("disabled", []))
                self.disabled_commands[guild_id] = disabled
        except FileNotFoundError:
            # If no config exists, use an empty set.
            self.disabled_commands[guild_id] = set()
        except Exception as e:
            print(f"Error loading config for guild {guild_id}: {e}")
            self.disabled_commands[guild_id] = set()

    def save_config(self, guild_id: int):
        """Save the guild's configuration to its JSON file."""
        filepath = self.config_filepath(guild_id)
        data = {"disabled": list(self.disabled_commands.get(guild_id, set()))}
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config for guild {guild_id}: {e}")

    def get_all_commands(self) -> list[str]:
        """Returns a sorted list of non-hidden command names from the bot."""
        return sorted([cmd.name for cmd in self.bot.commands if not cmd.hidden])
    
    def create_settings_embed(self, guild_id: int) -> discord.Embed:
        """Create an embed listing each command with its current status (Blocked/Allowed)."""
        all_commands = self.get_all_commands()
        blocked = self.disabled_commands.get(guild_id, set())
        description_lines = [
            f"**{cmd}**: {'Blocked' if cmd in blocked else 'Allowed'}" 
            for cmd in all_commands
        ]
        embed = discord.Embed(
            title="Server Command Settings",
            description="\n".join(description_lines),
            color=discord.Color.blurple()
        )
        return embed

    @app_commands.command(
        name="serversettings", 
        description="View and manage command settings for this server."
    )
    async def serversettings(self, interaction: discord.Interaction):
        # Ensure the command is run in a guild.
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        
        # Verify that the user has admin permissions.
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need admin permissions to use this command.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        # Load the configuration for this guild if it hasn't been loaded already.
        if guild_id not in self.disabled_commands:
            self.load_config(guild_id)
        all_commands = self.get_all_commands()
        embed = self.create_settings_embed(guild_id)
        view = CommandBlockView(self, guild_id, all_commands)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerSettings(bot))
