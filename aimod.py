# moderation_cog.py
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp # For making asynchronous HTTP requests
import json
import os # To load API key from environment variables
import collections # For deque
import datetime # For timestamps

# --- Configuration ---
# Load the OpenRouter API key from the environment variable "AI_API_KEY"
OPENROUTER_API_KEY = os.getenv("AI_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Error: AI_API_KEY environment variable is not set. The ModerationCog requires a valid API key to function.")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemini-2.5-flash-preview" # Make sure this model is available via your OpenRouter key

# --- Per-Guild Discord Configuration ---
GUILD_CONFIG_DIR = "/home/server/wdiscordbot-json-data" # Using the existing directory for all json data
GUILD_CONFIG_PATH = os.path.join(GUILD_CONFIG_DIR, "guild_config.json")
USER_INFRACTIONS_PATH = os.path.join(GUILD_CONFIG_DIR, "user_infractions.json")

os.makedirs(GUILD_CONFIG_DIR, exist_ok=True)

# Initialize Guild Config
if not os.path.exists(GUILD_CONFIG_PATH):
    with open(GUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)
try:
    with open(GUILD_CONFIG_PATH, "r", encoding="utf-8") as f:
        GUILD_CONFIG = json.load(f)
except Exception as e:
    print(f"Failed to load per-guild config from {GUILD_CONFIG_PATH}: {e}")
    GUILD_CONFIG = {}

# Initialize User Infractions
if not os.path.exists(USER_INFRACTIONS_PATH):
    with open(USER_INFRACTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f) # Stores infractions as { "guild_id_user_id": [infraction_list] }
try:
    with open(USER_INFRACTIONS_PATH, "r", encoding="utf-8") as f:
        USER_INFRACTIONS = json.load(f)
except Exception as e:
    print(f"Failed to load user infractions from {USER_INFRACTIONS_PATH}: {e}")
    USER_INFRACTIONS = {}

def save_guild_config():
    try:
        # os.makedirs(os.path.dirname(GUILD_CONFIG_PATH), exist_ok=True) # Already created by GUILD_CONFIG_DIR
        # if not os.path.exists(GUILD_CONFIG_PATH): # Redundant check, file is created if not exists
        #     with open(GUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
        #         json.dump({}, f)
        with open(GUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(GUILD_CONFIG, f, indent=2)
    except Exception as e:
        print(f"Failed to save per-guild config: {e}")

def save_user_infractions():
    try:
        # os.makedirs(os.path.dirname(USER_INFRACTIONS_PATH), exist_ok=True) # Already created by GUILD_CONFIG_DIR
        # if not os.path.exists(USER_INFRACTIONS_PATH): # Redundant check
        #     with open(USER_INFRACTIONS_PATH, "w", encoding="utf-8") as f:
        #         json.dump({}, f)
        with open(USER_INFRACTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(USER_INFRACTIONS, f, indent=2)
    except Exception as e:
        print(f"Failed to save user infractions: {e}")

def get_guild_config(guild_id: int, key: str, default=None):
    guild_str = str(guild_id)
    if guild_str in GUILD_CONFIG and key in GUILD_CONFIG[guild_str]:
        return GUILD_CONFIG[guild_str][key]
    return default

def set_guild_config(guild_id: int, key: str, value):
    guild_str = str(guild_id)
    if guild_str not in GUILD_CONFIG:
        GUILD_CONFIG[guild_str] = {}
    GUILD_CONFIG[guild_str][key] = value
    save_guild_config()

def get_user_infraction_history(guild_id: int, user_id: int) -> list:
    """Retrieves a list of past infractions for a specific user in a guild."""
    key = f"{guild_id}_{user_id}"
    return USER_INFRACTIONS.get(key, [])

def add_user_infraction(guild_id: int, user_id: int, rule_violated: str, action_taken: str, reasoning: str, timestamp: str):
    """Adds a new infraction record for a user."""
    key = f"{guild_id}_{user_id}"
    if key not in USER_INFRACTIONS:
        USER_INFRACTIONS[key] = []

    infraction_record = {
        "timestamp": timestamp,
        "rule_violated": rule_violated,
        "action_taken": action_taken,
        "reasoning": reasoning
    }
    USER_INFRACTIONS[key].append(infraction_record)
    # Keep only the last N infractions to prevent the file from growing too large, e.g., last 10
    USER_INFRACTIONS[key] = USER_INFRACTIONS[key][-10:]
    save_user_infractions()

# Server rules to provide context to the AI
SERVER_RULES = """
# Server Rules

- Keep NSFW stuff in NSFW channels. No full-on porn or explicit images outside of those spaces. Emojis, jokes and stickers are fine
- No real life pornography.
- Be respectful. No harassment, hate, or bullying, unless its clearly a lighthearted joke.
- No discrimination. This includes gender identity, sexual orientation, race, etc.
- No AI-generated porn.
- No pedophilia. This includes lolicon/shotacon.
- Suggestions are welcome! Drop them in <#1361752490210492489> if you've got any ideas.

If someone breaks the rules, ping <@&1361031007536549979>.
"""
SUICIDAL_HELP_RESOURCES = """
Hey, I'm really concerned to hear you're feeling this way. Please know that you're not alone and there are people who want to support you.
Your well-being is important to us on this server.

Here are some immediate resources that can offer help right now:

- **National Crisis and Suicide Lifeline (US):** Call or text **988**. This is available 24/7, free, and confidential.
- **Crisis Text Line (US):** Text **HOME** to **741741**. This is also a 24/7 free crisis counseling service.
- **The Trevor Project (for LGBTQ youth):** Call **1-866-488-7386** or visit their website for chat/text options: <https://www.thetrevorproject.org/get-help/>
- **The Jed Foundation (Mental Health Resource Center):** Provides resources for teens and young adults: <https://www.jedfoundation.org/>
- **Find A Helpline (International):** If you're outside the US, this site can help you find resources in your country: <https://findahelpline.com/>

Please reach out to one of these. We've also alerted our server's support team so they are aware and can offer a listening ear or further guidance if you're comfortable.
You matter, and help is available.
"""

class ModerationCog(commands.Cog):
    """
    A Discord Cog that uses OpenRouter AI to moderate messages based on server rules.
    Loads API key from the 'AI_API_KEY' environment variable.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Create a persistent session for making API requests
        self.session = aiohttp.ClientSession()
        self.openrouter_models = []
        self._load_openrouter_models()
        self.last_ai_decisions = collections.deque(maxlen=5) # Store last 5 AI decisions
        print("ModerationCog Initialized.")
        # Check if the API key was successfully loaded from the environment variable
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
            print("\n" + "="*60)
            print("=== WARNING: AI_API_KEY environment variable not found or empty! ===")
            print("=== The Moderation Cog requires a valid API key to function. ===")
            print("=== Make sure the 'AI_API_API_KEY' environment variable is set correctly. ===")
            print("="*60 + "\n")
        else:
             print("Successfully loaded API key from AI_API_KEY environment variable.")

    def _load_openrouter_models(self):
        """Loads OpenRouter model data from the JSON file."""
        models_json_path = "/home/server/wdiscordbotserver/data/openrouter_models.json" # Relative to bot's root
        try:
            if os.path.exists(models_json_path):
                with open(models_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "data" in data and isinstance(data["data"], list):
                        for model_info in data["data"]:
                            if isinstance(model_info, dict) and "id" in model_info and "name" in model_info:
                                self.openrouter_models.append(
                                    {"id": model_info["id"], "name": model_info["name"]}
                                )
                        print(f"Successfully loaded {len(self.openrouter_models)} OpenRouter models for autocomplete.")
                    else:
                        print(f"Warning: {models_json_path} does not have the expected 'data' list structure.")
            else:
                print(f"Warning: {models_json_path} not found. AI_MODEL autocomplete will be empty.")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {models_json_path}. AI_MODEL autocomplete will be empty.")
        except Exception as e:
            print(f"Error loading OpenRouter models from {models_json_path}: {e}. AI_MODEL autocomplete will be empty.")


    async def cog_unload(self):
        """Clean up the session when the cog is unloaded."""
        await self.session.close()
        print("ModerationCog Unloaded, session closed.")

    # --- AI Moderation Command Group ---
    aimod_group = app_commands.Group(name="aimod", description="AI Moderation commands.")
    config_subgroup = app_commands.Group(name="config", description="Configure AI moderation settings.", parent=aimod_group)
    infractions_subgroup = app_commands.Group(name="infractions", description="Manage user infractions.", parent=aimod_group)
    model_subgroup = app_commands.Group(name="model", description="Manage the AI model for moderation.", parent=aimod_group)
    debug_subgroup = app_commands.Group(name="debug", description="Debugging commands for AI moderation.", parent=aimod_group)

    @config_subgroup.command(name="log_channel", description="Set the moderation log channel.")
    @app_commands.describe(channel="The text channel to use for moderation logs.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_guild_config(interaction.guild.id, "MOD_LOG_CHANNEL_ID", channel.id)
        await interaction.response.send_message(f"Moderation log channel set to {channel.mention}.", ephemeral=False)

    @config_subgroup.command(name="suggestions_channel", description="Set the suggestions channel.")
    @app_commands.describe(channel="The text channel to use for suggestions.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_suggestions_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        set_guild_config(interaction.guild.id, "SUGGESTIONS_CHANNEL_ID", channel.id)
        await interaction.response.send_message(f"Suggestions channel set to {channel.mention}.", ephemeral=False)

    @config_subgroup.command(name="moderator_role", description="Set the moderator role.")
    @app_commands.describe(role="The role that identifies moderators.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_moderator_role(self, interaction: discord.Interaction, role: discord.Role):
        set_guild_config(interaction.guild.id, "MODERATOR_ROLE_ID", role.id)
        await interaction.response.send_message(f"Moderator role set to {role.mention}.", ephemeral=False)

    @config_subgroup.command(name="suicidal_ping_role", description="Set the role to ping for suicidal content.")
    @app_commands.describe(role="The role to ping for urgent suicidal content alerts.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_suicidal_ping_role(self, interaction: discord.Interaction, role: discord.Role):
        set_guild_config(interaction.guild.id, "SUICIDAL_PING_ROLE_ID", role.id)
        await interaction.response.send_message(f"Suicidal content ping role set to {role.mention}.", ephemeral=False)

    @config_subgroup.command(name="add_nsfw_channel", description="Add a channel to the list of NSFW channels.")
    @app_commands.describe(channel="The text channel to mark as NSFW for the bot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_add_nsfw_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id
        nsfw_channels: list[int] = get_guild_config(guild_id, "NSFW_CHANNEL_IDS", [])
        if channel.id not in nsfw_channels:
            nsfw_channels.append(channel.id)
            set_guild_config(guild_id, "NSFW_CHANNEL_IDS", nsfw_channels)
            await interaction.response.send_message(f"{channel.mention} added to NSFW channels list.", ephemeral=False)
        else:
            await interaction.response.send_message(f"{channel.mention} is already in the NSFW channels list.", ephemeral=True)

    @config_subgroup.command(name="remove_nsfw_channel", description="Remove a channel from the list of NSFW channels.")
    @app_commands.describe(channel="The text channel to remove from the NSFW list.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_remove_nsfw_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id
        nsfw_channels: list[int] = get_guild_config(guild_id, "NSFW_CHANNEL_IDS", [])
        if channel.id in nsfw_channels:
            nsfw_channels.remove(channel.id)
            set_guild_config(guild_id, "NSFW_CHANNEL_IDS", nsfw_channels)
            await interaction.response.send_message(f"{channel.mention} removed from NSFW channels list.", ephemeral=False)
        else:
            await interaction.response.send_message(f"{channel.mention} is not in the NSFW channels list.", ephemeral=True)

    @config_subgroup.command(name="list_nsfw_channels", description="List currently configured NSFW channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_list_nsfw_channels(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        nsfw_channel_ids: list[int] = get_guild_config(guild_id, "NSFW_CHANNEL_IDS", [])
        if not nsfw_channel_ids:
            await interaction.response.send_message("No NSFW channels are currently configured.", ephemeral=False)
            return

        channel_mentions = []
        for channel_id in nsfw_channel_ids:
            channel_obj = interaction.guild.get_channel(channel_id)
            if channel_obj:
                channel_mentions.append(channel_obj.mention)
            else:
                channel_mentions.append(f"ID:{channel_id} (not found)")
        
        await interaction.response.send_message(f"Configured NSFW channels:\n- " + "\n- ".join(channel_mentions), ephemeral=False)

    # Note: The @app_commands.command(name="modenable", ...) and other commands like
    # viewinfractions, clearinfractions, modsetmodel, modgetmodel remain as top-level commands
    # as they were not part of the original "modset" generic command structure.
    # If these also need to be grouped, that would be a separate consideration.

    @config_subgroup.command(name="enable", description="Enable or disable moderation for this guild (admin only).")
    @app_commands.describe(enabled="Enable moderation (true/false)")
    async def modenable(self, interaction: discord.Interaction, enabled: bool):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=False)
            return
        set_guild_config(interaction.guild.id, "ENABLED", enabled)
        await interaction.response.send_message(f"Moderation is now {'enabled' if enabled else 'disabled'} for this guild.", ephemeral=False)

    @infractions_subgroup.command(name="view", description="View a user's AI moderation infraction history (mod/admin only).")
    @app_commands.describe(user="The user to view infractions for")
    async def viewinfractions(self, interaction: discord.Interaction, user: discord.Member):
        # Check if user has permission (admin or moderator role)
        moderator_role_id = get_guild_config(interaction.guild.id, "MODERATOR_ROLE_ID")
        moderator_role = interaction.guild.get_role(moderator_role_id) if moderator_role_id else None

        has_permission = (interaction.user.guild_permissions.administrator or
                         (moderator_role and moderator_role in interaction.user.roles))

        if not has_permission:
            await interaction.response.send_message("You must be an administrator or have the moderator role to use this command.", ephemeral=True)
            return

        # Get the user's infraction history
        infractions = get_user_infraction_history(interaction.guild.id, user.id)

        if not infractions:
            await interaction.response.send_message(f"{user.mention} has no recorded infractions.", ephemeral=False)
            return

        # Create an embed to display the infractions
        embed = discord.Embed(
            title=f"Infraction History for {user.display_name}",
            description=f"User ID: {user.id}",
            color=discord.Color.orange()
        )

        # Add each infraction to the embed
        for i, infraction in enumerate(infractions, 1):
            timestamp = infraction.get('timestamp', 'Unknown date')[:19].replace('T', ' ')  # Format ISO timestamp
            rule = infraction.get('rule_violated', 'Unknown rule')
            action = infraction.get('action_taken', 'Unknown action')
            reason = infraction.get('reasoning', 'No reason provided')

            # Truncate reason if it's too long
            if len(reason) > 200:
                reason = reason[:197] + "..."

            embed.add_field(
                name=f"Infraction #{i} - {timestamp}",
                value=f"**Rule Violated:** {rule}\n**Action Taken:** {action}\n**Reason:** {reason}",
                inline=False
            )

        embed.set_footer(text=f"Total infractions: {len(infractions)}")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @infractions_subgroup.command(name="clear", description="Clear a user's AI moderation infraction history (admin only).")
    @app_commands.describe(user="The user to clear infractions for")
    async def clearinfractions(self, interaction: discord.Interaction, user: discord.Member):
        # Check if user has administrator permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return

        # Get the user's infraction history
        key = f"{interaction.guild.id}_{user.id}"
        infractions = USER_INFRACTIONS.get(key, [])

        if not infractions:
            await interaction.response.send_message(f"{user.mention} has no recorded infractions to clear.", ephemeral=False)
            return

        # Clear the user's infractions
        USER_INFRACTIONS[key] = []
        save_user_infractions()

        await interaction.response.send_message(f"Cleared {len(infractions)} infraction(s) for {user.mention}.", ephemeral=False)

    @model_subgroup.command(name="set", description="Change the AI model used for moderation (admin only).")
    @app_commands.describe(model="The OpenRouter model to use (e.g., 'google/gemini-2.5-flash-preview', 'anthropic/claude-3-opus-20240229')")
    async def modsetmodel(self, interaction: discord.Interaction, model: str):
        # Check if user has administrator permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return

        # Validate the model name (basic validation)
        if not model or len(model) < 5 or "/" not in model:
            await interaction.response.send_message("Invalid model format. Please provide a valid OpenRouter model ID (e.g., 'google/gemini-2.5-flash-preview').", ephemeral=False)
            return

        # Save the model to guild configuration
        guild_id = interaction.guild.id
        set_guild_config(guild_id, "AI_MODEL", model)

        # Update the global model for immediate effect
        global OPENROUTER_MODEL
        OPENROUTER_MODEL = model

        await interaction.response.send_message(f"AI moderation model updated to `{model}` for this guild.", ephemeral=False)

    @modsetmodel.autocomplete('model')
    async def modsetmodel_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        print(f"[DEBUG] modsetmodel_autocomplete triggered. Current input: '{current}'")
        if not self.openrouter_models:
            print("[DEBUG] modsetmodel_autocomplete: openrouter_models list is empty or not loaded.")
            return [app_commands.Choice(name="⚠️ Models not loaded", value="")]

        print(f"[DEBUG] modsetmodel_autocomplete: Filtering {len(self.openrouter_models)} models with current: '{current}'")
        filtered_models = [
            m for m in self.openrouter_models
            if current.lower() in m["name"].lower() or current.lower() in m["id"].lower()
        ][:25]
        
        choices_to_return = [
            app_commands.Choice(name=m["name"][:100], value=m["id"][:100]) # Truncate name/value
            for m in filtered_models
        ]
        print(f"[DEBUG] modsetmodel_autocomplete returning {len(choices_to_return)} choices: {choices_to_return[:5]}")
        return choices_to_return

    @model_subgroup.command(name="get", description="View the current AI model used for moderation.")
    async def modgetmodel(self, interaction: discord.Interaction):
        # Get the model from guild config, fall back to global default
        guild_id = interaction.guild.id
        model_used = get_guild_config(guild_id, "AI_MODEL", OPENROUTER_MODEL)

        # Create an embed to display the model information
        embed = discord.Embed(
            title="AI Moderation Model",
            description=f"The current AI model used for moderation in this server is:",
            color=discord.Color.blue()
        )
        embed.add_field(name="Model", value=f"`{model_used}`", inline=False)
        embed.add_field(name="Default Model", value=f"`{OPENROUTER_MODEL}`", inline=False)
        embed.set_footer(text="Use /modsetmodel to change the model")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    # Removed setup_hook as commands defined with @app_commands.command in a Cog
    # are typically automatically registered when the cog is added.
    # async def setup_hook(self):
    #     self.bot.tree.add_command(self.modset)
    #     self.bot.tree.add_command(self.modenable)
    #     self.bot.tree.add_command(self.viewinfractions)
    #     self.bot.tree.add_command(self.clearinfractions)
    #     self.bot.tree.add_command(self.modsetmodel)
    #     self.bot.tree.add_command(self.modgetmodel)

    async def query_openrouter(self, message: discord.Message, message_content: str, user_history: str):
        """
        Sends the message content, user history, and additional context to the OpenRouter API for analysis.

        Args:
            message: The original discord.Message object.
            message_content: The text content of the message.
            user_history: A string summarizing the user's past infractions.

        Returns:
            A dictionary containing the AI's decision, or None if an error occurs.
            Expected format:
            {
              "violation": bool,
              "rule_violated": str ("None", "1", "5A", etc.),
              "reasoning": str,
              "action": str ("IGNORE", "WARN", "DELETE", "BAN", "NOTIFY_MODS")
            }
        """
        # Check again in case the cog loaded but the key was invalid/placeholder
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
            print("Error: OpenRouter API Key (from AI_API_KEY env var) is not configured correctly.")
            return None

        # Construct the prompt for the AI model
        system_prompt_text = f"""You are an AI moderation assistant for a Discord server.
Your primary function is to analyze message content based STRICTLY on the server rules provided below, using all available context.

Server Rules:
---
{SERVER_RULES}
---

Context Provided:
You will receive the following information to aid your analysis:
- User's Server Role: (e.g., "Server Owner", "Admin", "Moderator", "Member").
- Channel Category: The name of the category the channel belongs to.
- Channel Age-Restricted (Discord Setting): Boolean (true/false).
- Replied-to Message: If the current message is a reply, the content of the original message will be provided. This is crucial for understanding direct interactions.
- Recent Channel History: The last few messages in the channel to understand the flow of conversation.

Instructions:
1. Review the "Message Content" against EACH rule, considering ALL provided context (User Role, Channel Info, Replied-to Message, Recent Channel History).
   - The "Channel Age-Restricted (Discord Setting)" is the definitive indicator for NSFW content by Discord.
   - The "Channel Category" provides general context.
   - **"Replied-to Message" and "Recent Channel History" are vital for understanding banter, jokes, and ongoing discussions. A statement that seems offensive in isolation might be acceptable within the flow of conversation or as a direct reply.**
2. Determine if ANY rule is violated. When evaluating, consider the server's culture where **extremely edgy, dark, and sexual humor, including potentially offensive jokes (e.g., rape jokes, saying you want to be raped), are common and generally permissible IF THEY ARE CLEARLY JOKES, part of an established banter, or a direct non-malicious reply, and not targeted harassment or explicit rule violations.**
   - For Rule 1 (NSFW content):
     - If "Channel Age-Restricted (Discord Setting)" is `true`, more explicit content is generally permissible, but still subject to other rules like Rule 2 (No IRL Porn) and Rule 5 (No Pedophilia).
     - If "Channel Age-Restricted (Discord Setting)" is `false`, Rule 1 applies strictly: "No full-on porn or explicit images outside of those spaces." However, "Emojis, jokes and stickers are fine." Only flag a Rule 1 violation for text if it's **explicitly pornographic text that would qualify as actual pornography if written out**, not just suggestive emojis, stickers, or dark/sexual jokes, especially if conversational context supports a joking intent.
   - For general disrespectful behavior, harassment, or bullying (Rule 2 & 3): Only flag a violation if the intent appears **genuinely malicious, targeted, or serious, even after considering conversational history and replies.** Lighthearted insults or "wild" statements within an ongoing banter are generally permissible.
   - For **explicit slurs or severe discriminatory language** (Rule 3): These are violations **regardless of joking intent if they are used in a targeted or hateful manner**. Context from replies and history is still important to assess targeting.
After considering the above, pay EXTREME attention to rules 5 (Pedophilia) and 5A (IRL Porn) – these are always severe. Rule 4 (AI Porn) is also critical. Prioritize these severe violations.
3. Respond ONLY with a single JSON object containing the following keys:
    - "violation": boolean (true if any rule is violated, false otherwise)
    - "rule_violated": string (The number of the rule violated, e.g., "1", "5A", "None". If multiple rules are violated, state the MOST SEVERE one, prioritizing 5A > 5 > 4 > 3 > 2 > 1).
    - "reasoning": string (A concise explanation for your decision, referencing the specific rule and content).
    - "action": string (Suggest ONE action from: "IGNORE", "WARN", "DELETE", "TIMEOUT_SHORT", "TIMEOUT_MEDIUM", "TIMEOUT_LONG", "KICK", "BAN", "NOTIFY_MODS", "SUICIDAL".
       Consider the user's infraction history. If the user has prior infractions for similar or escalating behavior, suggest a more severe action than if it were a first-time offense for a minor rule.
       Progressive Discipline Guide (unless overridden by severity):
         - First minor offense: "WARN" (and "DELETE" if content is removable like Rule 1/4).
         - Second minor offense / First moderate offense: "TIMEOUT_SHORT" (e.g., 10 minutes).
         - Repeated moderate offenses: "TIMEOUT_MEDIUM" (e.g., 1 hour).
         - Multiple/severe offenses: "TIMEOUT_LONG" (e.g., 1 day), "KICK", or "BAN".
       Rule Severity Guidelines (use your judgment):
         - Consider the severity of each rule violation on its own merits.
         - Consider the user's history of past infractions when determining appropriate action.
         - Consider the context of the message and channel when evaluating violations.
         - You have full discretion to determine the most appropriate action for any violation.
       Suicidal Content:
         If the message content expresses **clear, direct, and serious suicidal ideation, intent, planning, or recent attempts** (e.g., 'I am going to end my life and have a plan', 'I survived my attempt last night', 'I wish I hadn't woken up after trying'), ALWAYS use "SUICIDAL" as the action, and set "violation" to true, with "rule_violated" as "Suicidal Content".
         For casual, edgy, hyperbolic, or ambiguous statements like 'imma kms', 'just kill me now', 'I want to die (lol)', or phrases that are clearly part of edgy humor/banter rather than a genuine cry for help, you should lean towards "IGNORE" or "NOTIFY_MODS" if there's slight ambiguity but no clear serious intent. **Do NOT flag 'imma kms' as "SUICIDAL" unless there is very strong supporting context indicating genuine, immediate, and serious intent.**
       If unsure but suspicious, or if the situation is complex: "NOTIFY_MODS".
       Default action for minor first-time rule violations should be "WARN" or "DELETE" (if applicable).
       Do not suggest "KICK" or "BAN" lightly; reserve for severe or repeated major offenses.
       Timeout durations: TIMEOUT_SHORT (approx 10 mins), TIMEOUT_MEDIUM (approx 1 hour), TIMEOUT_LONG (approx 1 day to 1 week).
       The system will handle the exact timeout duration; you just suggest the category.)

Example Response (Violation):
{{
  "violation": true,
  "rule_violated": "5A",
  "reasoning": "The message content clearly depicts IRL non-consensual sexual content involving minors, violating rule 5A.",
  "action": "BAN"
}}

Example Response (No Violation):
{{
  "violation": false,
  "rule_violated": "None",
  "reasoning": "The message is a respectful discussion and contains no prohibited content.",
  "action": "IGNORE"
}}

Example Response (Suicidal Content):
{{
  "violation": true,
  "rule_violated": "Suicidal Content",
  "reasoning": "The user's message 'I want to end my life' indicates clear suicidal intent.",
  "action": "SUICIDAL"
}}
"""

        member = message.author # This is a discord.Member object
        server_role_str = "Member" # Default

        if member == message.guild.owner:
            server_role_str = "Server Owner"
        elif member.guild_permissions.administrator:
            server_role_str = "Admin"
        else:
            perms = member.guild_permissions
            if perms.manage_messages or perms.kick_members or perms.ban_members or perms.moderate_members:
                server_role_str = "Moderator"

        # --- Fetch Replied-to Message ---
        replied_to_message_content = "N/A (Not a reply)"
        if message.reference and message.reference.message_id:
            try:
                replied_to_msg = await message.channel.fetch_message(message.reference.message_id)
                replied_to_message_content = f"User '{replied_to_msg.author.name}' said: \"{replied_to_msg.content[:200]}\""
                if len(replied_to_msg.content) > 200:
                    replied_to_message_content += "..."
            except discord.NotFound:
                replied_to_message_content = "N/A (Replied-to message not found)"
            except discord.Forbidden:
                replied_to_message_content = "N/A (Cannot fetch replied-to message - permissions)"
            except Exception as e:
                replied_to_message_content = f"N/A (Error fetching replied-to message: {e})"

        # --- Fetch Recent Channel History ---
        recent_channel_history_str = "N/A (Could not fetch history)"
        try:
            history_messages = []
            # Fetch last 11 messages (current + 10 previous). We'll filter out the current one
            async for prev_msg in message.channel.history(limit=11, before=message):
                if prev_msg.id != message.id: # Ensure we don't include the current message itself
                    history_messages.append(f"- {prev_msg.author.name}: \"{prev_msg.content[:150]}{'...' if len(prev_msg.content) > 150 else ''}\" (ID: {prev_msg.id})")
            if history_messages:
                # Reverse to show oldest first in the snippet, then take the last 10.
                recent_channel_history_str = "\n".join(list(reversed(history_messages))[:10])
            else:
                recent_channel_history_str = "No recent messages before this one in the channel."
        except discord.Forbidden:
            recent_channel_history_str = "N/A (Cannot fetch channel history - permissions)"
        except Exception as e:
            recent_channel_history_str = f"N/A (Error fetching channel history: {e})"


        user_prompt_text = f"""User Infraction History (for {message.author.name}, ID: {message.author.id}):
---
{user_history if user_history else "No prior infractions recorded for this user in this guild."}
---

Current Message Context:
- Author: {message.author.name} (ID: {message.author.id})
- Server Role: {server_role_str}
- Channel: #{message.channel.name} (ID: {message.channel.id})
- Channel Category: {message.channel.category.name if message.channel.category else "No Category"}
- Channel Age-Restricted (Discord Setting): {message.channel.is_nsfw()}
---
Replied-to Message:
{replied_to_message_content}
---
Recent Channel History (last up to 10 messages before this one):
{recent_channel_history_str}
---
Message Content to Analyze:
"{message_content}"

Now, analyze the "Message Content to Analyze" based on the server rules and ALL the context provided above (infraction history, message details, replied-to message, and recent channel history).
Follow the JSON output format specified in the system prompt.
"""
        user_prompt_content_list = [{"type": "text", "text": user_prompt_text}]

        # Get guild-specific model if configured, otherwise use default
        guild_id = message.guild.id
        model_to_use = get_guild_config(guild_id, "AI_MODEL", OPENROUTER_MODEL)

        # Structure the request payload for OpenRouter
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            # Optional: Add Referer and X-Title headers as recommended by OpenRouter
            # "HTTP-Referer": "YOUR_SITE_URL", # Replace with your bot's project URL if applicable
            # "X-Title": "Your Bot Name", # Replace with your bot's name
        }
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": system_prompt_text},
                {"role": "user", "content": user_prompt_content_list}
            ],
            "max_tokens": 1000, # Adjust as needed, ensure it's enough for the JSON response
            "temperature": 0.2, # Lower temperature for more deterministic moderation responses
            # Enforce JSON output if the model supports it (some models use tool/function calling)
            # "response_format": {"type": "json_object"} # Uncomment if model supports this parameter
        }

        try:
            print(f"Querying OpenRouter model {model_to_use}...")
            async with self.session.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=60) as response: # Added timeout
                response_text = await response.text() # Get raw text for debugging
                # print(f"OpenRouter Raw Response Status: {response.status}")
                # print(f"OpenRouter Raw Response Body: {response_text[:1000]}...") # Print first 1000 chars

                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                result = await response.json()
                ai_response_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                if not ai_response_content:
                    print("Error: AI response content is empty.")
                    return None

                # Attempt to parse the JSON response from the AI
                try:
                    # Clean potential markdown code blocks
                    if ai_response_content.startswith("```json"):
                        ai_response_content = ai_response_content.strip("```json\n").strip("`\n ")
                    elif ai_response_content.startswith("```"):
                         ai_response_content = ai_response_content.strip("```\n").strip("`\n ")

                    ai_decision = json.loads(ai_response_content)

                    # Basic validation of the parsed JSON structure
                    if not isinstance(ai_decision, dict):
                         print(f"Error: AI response is not a JSON object. Response: {ai_response_content}")
                         return None
                    if not all(k in ai_decision for k in ["violation", "rule_violated", "reasoning", "action"]):
                        print(f"Error: AI response missing expected keys. Response: {ai_response_content}")
                        return None
                    if not isinstance(ai_decision.get("violation"), bool):
                        print(f"Error: 'violation' key is not a boolean. Response: {ai_response_content}")
                        return None # Or attempt to coerce/fix

                    print(f"AI Analysis Received: {ai_decision}")
                    return ai_decision

                except json.JSONDecodeError as e:
                    print(f"Error: Could not decode JSON response from AI: {e}. Response: {ai_response_content}")
                    return None
                except Exception as e:
                    print(f"Error parsing AI response structure: {e}. Response: {ai_response_content}")
                    return None

        except aiohttp.ClientResponseError as e:
            print(f"Error calling OpenRouter API (HTTP {e.status}): {e.message}")
            print(f"Response body: {response_text[:500]}") # Print part of the error body
            return None
        except aiohttp.ClientError as e:
            print(f"Error calling OpenRouter API (Connection/Client Error): {e}")
            return None
        except TimeoutError:
             print("Error: Request to OpenRouter API timed out.")
             return None
        except Exception as e:
            # Catch any other unexpected errors during the API call
            print(f"An unexpected error occurred during action execution for message {message.id}: {e}")
            return None

    async def handle_violation(self, message: discord.Message, ai_decision: dict):
        """
        Takes action based on the AI's violation decision.
        Also transmits action info via HTTP POST with API key header.
        """
        import datetime
        import aiohttp

        rule_violated = ai_decision.get("rule_violated", "Unknown")
        reasoning = ai_decision.get("reasoning", "No reasoning provided.")
        action = ai_decision.get("action", "NOTIFY_MODS").upper() # Default to notify mods
        guild_id = message.guild.id # Get guild_id once
        user_id = message.author.id # Get user_id once

        moderator_role_id = get_guild_config(guild_id, "MODERATOR_ROLE_ID")
        moderator_role = message.guild.get_role(moderator_role_id) if moderator_role_id else None
        mod_ping = moderator_role.mention if moderator_role else f"Moderators (Role ID {moderator_role_id} not found)"

        current_timestamp_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Get the model from guild config, fall back to global default (moved up from line 609)
        model_used = get_guild_config(guild_id, "AI_MODEL", OPENROUTER_MODEL)

        # --- Transmit action info over HTTP POST ---
        try:
            mod_log_api_secret = os.getenv("MOD_LOG_API_SECRET")
            if mod_log_api_secret:
                post_url = f"https://slipstreamm.dev/dashboard/api/guilds/{guild_id}/ai-moderation-action" #will be replaceing later with the Learnhelp API
                payload = {
                    "timestamp": current_timestamp_iso,
                    "guild_id": guild_id,
                    "guild_name": message.guild.name,
                    "channel_id": message.channel.id,
                    "channel_name": message.channel.name,
                    "message_id": message.id,
                    "message_link": message.jump_url,
                    "user_id": user_id,
                    "user_name": str(message.author),
                    "action": action, # This will be the AI suggested action before potential overrides
                    "rule_violated": rule_violated,
                    "reasoning": reasoning,
                    "violation": ai_decision.get("violation", False),
                    "message_content": message.content[:1024] if message.content else "",
                    "full_message_content": message.content if message.content else "",
                    "ai_model": model_used,
                    "result": "pending_system_action" # Indicates AI decision received, system action pending
                }
                headers = {
                    "Authorization": f"Bearer {mod_log_api_secret}",
                    "Content-Type": "application/json"
                }
                async with aiohttp.ClientSession() as http_session: # Renamed session to avoid conflict
                    async with http_session.post(post_url, headers=headers, json=payload, timeout=10) as resp:
                        # This payload is just for the initial AI decision log
                        # The actual outcome will be logged after the action is performed
                        if resp.status >= 400:
                             print(f"Failed to POST initial AI decision log: {resp.status}")
            else:
                print("MOD_LOG_API_SECRET not set; skipping initial action POST.")
        except Exception as e:
            print(f"Failed to POST initial action info: {e}")

        # --- Prepare Notification ---
        notification_embed = discord.Embed(
            title="🚨 Rule Violation Detected 🚨",
            description=f"AI analysis detected a violation of server rules.",
            color=discord.Color.red()
        )
        notification_embed.add_field(name="User", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
        notification_embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        notification_embed.add_field(name="Rule Violated", value=f"**Rule {rule_violated}**", inline=True)
        notification_embed.add_field(name="AI Suggested Action", value=f"`{action}`", inline=True)
        notification_embed.add_field(name="AI Reasoning", value=f"_{reasoning}_", inline=False)
        notification_embed.add_field(name="Message Link", value=f"[Jump to Message]({message.jump_url})", inline=False)
        # Log message content and attachments for audit purposes
        msg_content = message.content if message.content else "*No text content*"
        notification_embed.add_field(name="Message Content", value=msg_content[:1024], inline=False)
        # Use the model_used variable that was defined earlier
        notification_embed.set_footer(text=f"AI Model: {model_used}. Learnhelp AI Moderation.")
        notification_embed.timestamp = discord.utils.utcnow() # Using discord.utils.utcnow() which is still supported

        action_taken_message = "" # To append to the notification

        # --- Perform Actions ---
        try:
            if action == "BAN":
                action_taken_message = f"Action Taken: User **BANNED** and message deleted."
                notification_embed.color = discord.Color.dark_red()
                try:
                    await message.delete()
                except discord.NotFound: print("Message already deleted before banning.")
                except discord.Forbidden:
                    print(f"WARNING: Missing permissions to delete message before banning user {message.author}.")
                    action_taken_message += " (Failed to delete message - check permissions)"
                ban_reason = f"AI Mod: Rule {rule_violated}. Reason: {reasoning}"
                await message.guild.ban(message.author, reason=ban_reason, delete_message_days=1)
                print(f"BANNED user {message.author} for violating rule {rule_violated}.")
                add_user_infraction(guild_id, user_id, rule_violated, "BAN", reasoning, current_timestamp_iso)

            elif action == "KICK":
                action_taken_message = f"Action Taken: User **KICKED** and message deleted."
                notification_embed.color = discord.Color.from_rgb(255, 127, 0) # Dark Orange
                try:
                    await message.delete()
                except discord.NotFound: print("Message already deleted before kicking.")
                except discord.Forbidden:
                    print(f"WARNING: Missing permissions to delete message before kicking user {message.author}.")
                    action_taken_message += " (Failed to delete message - check permissions)"
                kick_reason = f"AI Mod: Rule {rule_violated}. Reason: {reasoning}"
                await message.author.kick(reason=kick_reason)
                print(f"KICKED user {message.author} for violating rule {rule_violated}.")
                add_user_infraction(guild_id, user_id, rule_violated, "KICK", reasoning, current_timestamp_iso)

            elif action.startswith("TIMEOUT"):
                duration_seconds = 0
                duration_readable = ""
                if action == "TIMEOUT_SHORT":
                    duration_seconds = 10 * 60  # 10 minutes
                    duration_readable = "10 minutes"
                elif action == "TIMEOUT_MEDIUM":
                    duration_seconds = 60 * 60  # 1 hour
                    duration_readable = "1 hour"
                elif action == "TIMEOUT_LONG":
                    duration_seconds = 24 * 60 * 60 # 1 day
                    duration_readable = "1 day"

                if duration_seconds > 0:
                    action_taken_message = f"Action Taken: User **TIMED OUT for {duration_readable}** and message deleted."
                    notification_embed.color = discord.Color.blue()
                    try:
                        await message.delete()
                    except discord.NotFound: print(f"Message already deleted before timeout for {message.author}.")
                    except discord.Forbidden:
                        print(f"WARNING: Missing permissions to delete message before timeout for {message.author}.")
                        action_taken_message += " (Failed to delete message - check permissions)"

                    timeout_reason = f"AI Mod: Rule {rule_violated}. Reason: {reasoning}"
                    # discord.py timeout takes a timedelta object
                    await message.author.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds), reason=timeout_reason)
                    print(f"TIMED OUT user {message.author} for {duration_readable} for violating rule {rule_violated}.")
                    add_user_infraction(guild_id, user_id, rule_violated, action, reasoning, current_timestamp_iso)
                else:
                    action_taken_message = "Action Taken: **Unknown timeout duration, notifying mods.**"
                    action = "NOTIFY_MODS" # Fallback if timeout duration is not recognized
                    print(f"Unknown timeout duration for action {action}. Defaulting to NOTIFY_MODS.")


            elif action == "DELETE":
                action_taken_message = f"Action Taken: Message **DELETED**."
                await message.delete()
                print(f"DELETED message from {message.author} for violating rule {rule_violated}.")
                # Typically, a simple delete isn't a formal infraction unless it's part of a WARN.
                # If you want to log deletes as infractions, add:
                # add_user_infraction(guild_id, user_id, rule_violated, "DELETE", reasoning, current_timestamp_iso)


            elif action == "WARN":
                action_taken_message = f"Action Taken: Message **DELETED** (AI suggested WARN)."
                notification_embed.color = discord.Color.orange()
                await message.delete() # Warnings usually involve deleting the offending message
                print(f"DELETED message from {message.author} (AI suggested WARN for rule {rule_violated}).")
                try:
                    dm_channel = await message.author.create_dm()
                    await dm_channel.send(
                        f"Your recent message in **{message.guild.name}** was removed for violating Rule **{rule_violated}**. "
                        f"Reason: _{reasoning}_. Please review the server rules. This is a formal warning."
                    )
                    action_taken_message += " User notified via DM with warning."
                except discord.Forbidden:
                    print(f"Could not DM warning to {message.author} (DMs likely disabled).")
                    action_taken_message += " (Could not DM user for warning)."
                except Exception as e:
                    print(f"Error sending warning DM to {message.author}: {e}")
                    action_taken_message += " (Error sending warning DM)."
                add_user_infraction(guild_id, user_id, rule_violated, "WARN", reasoning, current_timestamp_iso)


            elif action == "NOTIFY_MODS":
                action_taken_message = "Action Taken: **Moderator review requested.**"
                notification_embed.color = discord.Color.gold()
                print(f"Notifying moderators about potential violation (Rule {rule_violated}) by {message.author}.")
                # NOTIFY_MODS itself isn't an infraction on the user, but a request for human review.
                # If mods take action, they would log it manually or via a mod command.

            elif action == "SUICIDAL":
                action_taken_message = "Action Taken: **User DMed resources, relevant role notified.**"
                # No infraction is typically logged for "SUICIDAL" as it's a support action.
                notification_embed.title = "🚨 Suicidal Content Detected 🚨"
                notification_embed.color = discord.Color.dark_purple() # A distinct color
                notification_embed.description = "AI analysis detected content indicating potential suicidal ideation."
                print(f"SUICIDAL content detected from {message.author}. DMing resources and notifying role.")
                # DM the user with help resources
                try:
                    dm_channel = await message.author.create_dm()
                    await dm_channel.send(SUICIDAL_HELP_RESOURCES)
                    action_taken_message += " User successfully DMed."
                except discord.Forbidden:
                    print(f"Could not DM suicidal help resources to {message.author} (DMs likely disabled).")
                    action_taken_message += " (Could not DM user - DMs disabled)."
                except Exception as e:
                    print(f"Error sending suicidal help resources DM to {message.author}: {e}")
                    action_taken_message += f" (Error DMing user: {e})."
                # The message itself is usually not deleted for suicidal content, to allow for intervention.
                # If deletion is desired, add: await message.delete() here.

            else: # Includes "IGNORE" or unexpected actions
                if ai_decision.get("violation"): # If violation is true but action is IGNORE
                     action_taken_message = "Action Taken: **None** (AI suggested IGNORE despite flagging violation - Review Recommended)."
                     notification_embed.color = discord.Color.light_grey()
                     print(f"AI flagged violation ({rule_violated}) but suggested IGNORE for message by {message.author}. Notifying mods for review.")
                else:
                    # This case shouldn't be reached if called correctly, but handle defensively
                    print(f"No action taken for message by {message.author} (AI Action: {action}, Violation: False)")
                    return # Don't notify if no violation and action is IGNORE

            # --- Send Notification to Moderators/Relevant Role ---
            log_channel_id = get_guild_config(message.guild.id, "MOD_LOG_CHANNEL_ID")
            log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
            if not log_channel:
                print(f"ERROR: Moderation log channel (ID: {log_channel_id}) not found or not configured. Defaulting to message channel.")
                log_channel = message.channel
                if not log_channel:
                    print(f"ERROR: Could not find even the original message channel {message.channel.id} to send notification.")
                    return

            if action == "SUICIDAL":
                suicidal_role_id = get_guild_config(message.guild.id, "SUICIDAL_PING_ROLE_ID")
                suicidal_role = message.guild.get_role(suicidal_role_id) if suicidal_role_id else None
                ping_target = suicidal_role.mention if suicidal_role else f"Role ID {suicidal_role_id} (Suicidal Content)"
                if not suicidal_role:
                    print(f"ERROR: Suicidal ping role ID {suicidal_role_id} not found.")
                final_message = f"{ping_target}\n{action_taken_message}"
                await log_channel.send(content=final_message, embed=notification_embed)
            elif moderator_role: # For other violations
                final_message = f"{mod_ping}\n{action_taken_message}"
                await log_channel.send(content=final_message, embed=notification_embed)
            else: # Fallback if moderator role is also not found for non-suicidal actions
                print(f"ERROR: Moderator role ID {moderator_role_id} not found for action {action}.")


        except discord.Forbidden as e:
            print(f"ERROR: Missing Permissions to perform action '{action}' for rule {rule_violated}. Details: {e}")
            # Try to notify mods about the failure
            if moderator_role:
                try:
                    await message.channel.send(
                        f"{mod_ping} **PERMISSION ERROR!** Could not perform action `{action}` on message by {message.author.mention} "
                        f"for violating Rule {rule_violated}. Please check bot permissions.\n"
                        f"Reasoning: _{reasoning}_\nMessage Link: {message.jump_url}"
                    )
                except discord.Forbidden:
                    print("FATAL: Bot lacks permission to send messages, even error notifications.")
        except discord.NotFound:
             print(f"Message {message.id} was likely already deleted when trying to perform action '{action}'.")
        except Exception as e:
            print(f"An unexpected error occurred during action execution for message {message.id}: {e}")
            # Try to notify mods about the unexpected error
            if moderator_role:
                 try:
                    await message.channel.send(
                        f"{mod_ping} **UNEXPECTED ERROR!** An error occurred while handling rule violation "
                        f"for {message.author.mention}. Please check bot logs.\n"
                        f"Rule: {rule_violated}, Action Attempted: {action}\nMessage Link: {message.jump_url}"
                    )
                 except discord.Forbidden:
                    print("FATAL: Bot lacks permission to send messages, even error notifications.")


    @commands.Cog.listener(name="on_message")
    async def message_listener(self, message: discord.Message):
        """Listens to messages and triggers moderation checks."""
        # --- Basic Checks ---
        # Ignore messages from bots (including self)
        if message.author.bot:
            return
        # Ignore messages without content
        if not message.content:
             return
        # Ignore DMs
        if not message.guild:
            return
        # Check if moderation is enabled for this guild
        if not get_guild_config(message.guild.id, "ENABLED", True):
            return

        # --- Suicidal Content Check ---
        # Suicidal keyword check removed; handled by OpenRouter AI moderation.

        # --- Prepare for AI Analysis ---
        message_content = message.content

        # Only proceed with AI analysis if there's text to analyze
        if not message_content:
            return

        # NSFW channel check removed - AI will handle this context

        # --- Call AI for Analysis (All Rules) ---
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
             return

        # Prepare user history for the AI
        infractions = get_user_infraction_history(message.guild.id, message.author.id)
        history_summary_parts = []
        if infractions:
            for infr in infractions:
                history_summary_parts.append(f"- Action: {infr.get('action_taken', 'N/A')} for Rule {infr.get('rule_violated', 'N/A')} on {infr.get('timestamp', 'N/A')[:10]}. Reason: {infr.get('reasoning', 'N/A')[:50]}...")
        user_history_summary = "\n".join(history_summary_parts) if history_summary_parts else "No prior infractions recorded."

        # Limit history summary length to prevent excessively long prompts
        max_history_len = 500
        if len(user_history_summary) > max_history_len:
            user_history_summary = user_history_summary[:max_history_len-3] + "..."


        print(f"Analyzing message {message.id} from {message.author} in #{message.channel.name} with history...")
        ai_decision = await self.query_openrouter(message, message_content, user_history_summary)

        # --- Process AI Decision ---
        if not ai_decision:
            print(f"Failed to get valid AI decision for message {message.id}.")
            # Optionally notify mods about AI failure if it happens often
            # Store the failure attempt for debugging
            self.last_ai_decisions.append({
                "message_id": message.id,
                "author_name": str(message.author),
                "author_id": message.author.id,
                "message_content_snippet": message.content[:100] + "..." if len(message.content) > 100 else message.content,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "ai_decision": {"error": "Failed to get valid AI decision", "raw_response": None} # Simplified error logging
            })
            return # Stop if AI fails or returns invalid data

        # Store the AI decision regardless of violation status
        self.last_ai_decisions.append({
            "message_id": message.id,
            "author_name": str(message.author),
            "author_id": message.author.id,
            "message_content_snippet": message.content[:100] + "..." if len(message.content) > 100 else message.content,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "ai_decision": ai_decision
        })

        # Check if the AI flagged a violation
        if ai_decision.get("violation"):
            # Handle the violation based on AI decision without overrides
            await self.handle_violation(message, ai_decision)
        else:
            # AI found no violation
            print(f"AI analysis complete for message {message.id}. No violation detected.")

    @debug_subgroup.command(name="last_decisions", description="View the last 5 AI moderation decisions (admin only).")
    @app_commands.checks.has_permissions(administrator=True)
    async def aidebug_last_decisions(self, interaction: discord.Interaction):
        if not self.last_ai_decisions:
            await interaction.response.send_message("No AI decisions have been recorded yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Last 5 AI Moderation Decisions",
            color=discord.Color.purple()
        )
        embed.timestamp = discord.utils.utcnow()

        for i, record in enumerate(reversed(list(self.last_ai_decisions))): # Show newest first
            decision_info = record.get("ai_decision", {})
            violation = decision_info.get("violation", "N/A")
            rule_violated = decision_info.get("rule_violated", "N/A")
            reasoning = decision_info.get("reasoning", "N/A")
            action = decision_info.get("action", "N/A")
            error_msg = decision_info.get("error")

            field_value = (
                f"**Author:** {record.get('author_name', 'N/A')} ({record.get('author_id', 'N/A')})\n"
                f"**Message ID:** {record.get('message_id', 'N/A')}\n"
                f"**Content Snippet:** ```{record.get('message_content_snippet', 'N/A')}```\n"
                f"**Timestamp:** {record.get('timestamp', 'N/A')[:19].replace('T', ' ')}\n"
            )
            if error_msg:
                field_value += f"**Status:** <font color='red'>Error during processing: {error_msg}</font>\n"
            else:
                field_value += (
                    f"**Violation:** {violation}\n"
                    f"**Rule Violated:** {rule_violated}\n"
                    f"**Action:** {action}\n"
                    f"**Reasoning:** ```{reasoning}```\n"
                )
            
            # Truncate field_value if it's too long for an embed field
            if len(field_value) > 1024:
                field_value = field_value[:1020] + "..."

            embed.add_field(
                name=f"Decision #{len(self.last_ai_decisions) - i}",
                value=field_value,
                inline=False
            )
            if len(embed.fields) >= 5: # Limit to 5 fields in one embed for very long entries, or send multiple embeds
                break
        
        if not embed.fields: # Should not happen if self.last_ai_decisions is not empty
             await interaction.response.send_message("Could not format AI decisions.", ephemeral=True)
             return

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @aidebug_last_decisions.error
    async def aidebug_last_decisions_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
            print(f"Error in aidebug_last_decisions command: {error}")


# Setup function required by discord.py to load the cog
async def setup(bot: commands.Bot):
    """Loads the ModerationCog."""
    # Check if the API key is set during setup as well
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("\n" + "*"*60)
        print("*** CRITICAL WARNING during setup: AI_API_KEY environment variable is missing! ***")
        print("*** Moderation Cog will load but WILL NOT function. ***")
        print("*"*60 + "\n")
        # You could choose to raise an error here to prevent the bot from starting
        raise ValueError("AI_API_KEY environment variable is not configured. Cannot load ModerationCog.")
    await bot.add_cog(ModerationCog(bot))
    print("ModerationCog has been loaded.")
