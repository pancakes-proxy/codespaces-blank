# moderation_cog.py
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp # For making asynchronous HTTP requests
import json
import os # To load API key from environment variables

# --- Configuration ---
# Load the OpenRouter API key from the environment variable "AI_API_KEY"
OPENROUTER_API_KEY = os.getenv("AI_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Error: AI_API_KEY environment variable is not set. The ModerationCog requires a valid API key to function.")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemini-2.5-flash-preview" # Make sure this model is available via your OpenRouter key

# --- Per-Guild Discord Configuration ---
GUILD_CONFIG_DIR = "/home/server/wdiscordbot-json-data"
GUILD_CONFIG_PATH = os.path.join(GUILD_CONFIG_DIR, "guild_config.json")
os.makedirs(GUILD_CONFIG_DIR, exist_ok=True)
if not os.path.exists(GUILD_CONFIG_PATH):
    with open(GUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)
try:
    with open(GUILD_CONFIG_PATH, "r", encoding="utf-8") as f:
        GUILD_CONFIG = json.load(f)
except Exception as e:
    print(f"Failed to load per-guild config from {GUILD_CONFIG_PATH}: {e}")
    GUILD_CONFIG = {}

def save_guild_config():
    try:
        os.makedirs(os.path.dirname(GUILD_CONFIG_PATH), exist_ok=True)
        if not os.path.exists(GUILD_CONFIG_PATH):
            with open(GUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
        with open(GUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(GUILD_CONFIG, f, indent=2)
    except Exception as e:
        print(f"Failed to save per-guild config: {e}")

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

# Server rules to provide context to the AI
SERVER_RULES = """
# Server Rules

- Keep NSFW stuff in NSFW channels. No full-on porn or explicit images outside of those spaces. Emojis, jokes and stickers are fine
- No real life pornography.
- Be respectful. No harassment, hate, or bullying, unless its clearly a lighthearted joke.
- No discrimination. This includes gender identity, sexual orientation, race, etc.
- No AI-generated porn.
- No pedophilia. This includes lolicon/shotacon.
- Use the right channels. Bot commands go in <#1360717341775630637>, unless it's part of a bot game or event.
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


    async def cog_unload(self):
        """Clean up the session when the cog is unloaded."""
        await self.session.close()
        print("ModerationCog Unloaded, session closed.")

    MOD_KEYS = [
        "MOD_LOG_CHANNEL_ID",
        "MODERATOR_ROLE_ID",
        "SUICIDAL_PING_ROLE_ID",
        "BOT_COMMANDS_CHANNEL_ID",
        "SUGGESTIONS_CHANNEL_ID",
        "NSFW_CHANNEL_IDS",
    ]

    async def modset_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        return [
            app_commands.Choice(name=k, value=k)
            for k in self.MOD_KEYS if current.lower() in k.lower()
        ]

    @app_commands.command(name="modset", description="Set a moderation config value for this guild (admin only).")
    @app_commands.describe(key="Config key", value="Value (int, comma-separated list, or string)")
    @app_commands.autocomplete(key=modset_key_autocomplete)
    async def modset(
        self,
        interaction: discord.Interaction,
        key: str,
        value: str
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=False)
            return
        if key not in self.MOD_KEYS:
            await interaction.response.send_message(f"Invalid key. Choose from: {', '.join(self.MOD_KEYS)}", ephemeral=False)
            return
        guild_id = interaction.guild.id
        # Try to parse value as int, list of ints, or fallback to string
        parsed_value = value
        if "," in value:
            try:
                parsed_value = [int(v.strip()) for v in value.split(",")]
            except Exception:
                parsed_value = [v.strip() for v in value.split(",")]
        else:
            try:
                parsed_value = int(value)
            except Exception:
                pass
        set_guild_config(guild_id, key, parsed_value)
        await interaction.response.send_message(f"Set `{key}` to `{parsed_value}` for this guild.", ephemeral=False)

    @app_commands.command(name="modenable", description="Enable or disable moderation for this guild (admin only).")
    @app_commands.describe(enabled="Enable moderation (true/false)")
    async def modenable(self, interaction: discord.Interaction, enabled: bool):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=False)
            return
        set_guild_config(interaction.guild.id, "ENABLED", enabled)
        await interaction.response.send_message(f"Moderation is now {'enabled' if enabled else 'disabled'} for this guild.", ephemeral=False)

    async def setup_hook(self):
        self.bot.tree.add_command(self.modset)
        self.bot.tree.add_command(self.modenable)

    async def query_openrouter(self, message: discord.Message, message_content: str, image_urls: list[str]):
        """
        Sends the message content and image URLs to the OpenRouter API for analysis.

        Args:
            message: The original discord.Message object.
            message_content: The text content of the message.
            image_urls: A list of URLs for images attached to the message.

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
        prompt_messages = []
        prompt_content_list = [
            {
                "type": "text",
                "text": f"""You are an AI moderation assistant for a Discord server. Analyze the following message content and any attached images based STRICTLY on the server rules provided below.

Server Rules:
---
{SERVER_RULES}
---

Message Details:
- Author: {message.author.name} (ID: {message.author.id})
- Channel: #{message.channel.name} (ID: {message.channel.id})
- Message Content: "{message_content}"

Instructions:
1. Review the text content AND any provided image URLs against EACH rule.
2. Determine if ANY rule is violated. When evaluating, consider the server's culture where edgy/sexual jokes are common:
   - For general disrespectful behavior, harassment, or bullying (Rule 2 & 3): Only flag a violation if the intent appears **genuinely malicious or serious**, not just an edgy/sexual joke.
   - For **explicit slurs or severe discriminatory language** (Rule 3): These are violations **regardless of joking intent**.
After considering the above, pay EXTREME attention to rules 5 (Pedophilia) and 5A (IRL Porn) – these are always severe. Rule 4 (AI Porn) and Rule 1 (NSFW in wrong channel) are also critical. Prioritize these severe violations.
3. Respond ONLY with a single JSON object containing the following keys:
    - "violation": boolean (true if any rule is violated, false otherwise)
    - "rule_violated": string (The number of the rule violated, e.g., "1", "5A", "None". If multiple rules are violated, state the MOST SEVERE one, prioritizing 5A > 5 > 4 > 3 > 2 > 1 > 6).
    - "reasoning": string (A concise explanation for your decision, referencing the specific rule and content).
    - "action": string (Suggest ONE action: "IGNORE", "WARN", "DELETE", "BAN", "NOTIFY_MODS", "SUICIDAL". If the message content strongly indicates suicidal ideation or intent, ALWAYS use "SUICIDAL" as the action, and set "violation" to true, with "rule_violated" as "N/A" or "Suicidal Content". Otherwise, for rule violations: Mandatory "BAN" for rule 5A or 5. "DELETE" for rule 4 or rule 1 in wrong channel. "WARN" or "DELETE" for 2, 3. "NOTIFY_MODS" if unsure but suspicious).

"this is a note some messages are getting flagged for no reason please note that if there is a NSFW image with a character in it that has red hair that is 31 year old kasane teto so stop fucking flagging it you pmo
Example Response (Violation):
{{
  "violation": true,
  "rule_violated": "5A",
  "reasoning": "The attached image clearly depicts IRL non-consensual sexual content involving minors, violating rule 5A.",
  "action": "BAN"
}}

Example Response (No Violation):
{{
  "violation": false,
  "rule_violated": "None",
  "reasoning": "The message is a respectful discussion and contains no prohibited content or images.",
  "action": "IGNORE"
}}

Example Response (Suicidal Content):
{{
  "violation": true,
  "rule_violated": "Suicidal Content",
  "reasoning": "The user's message 'I want to end my life' indicates clear suicidal intent.",
  "action": "SUICIDAL"
}}

Now, analyze the provided message content and images:
"""
            }
        ]

        # Add image URLs to the prompt content list if any exist
        if image_urls:
            prompt_content_list.append({
                "type": "text",
                "text": "Attached Image URLs to analyze:"
            })
            for url in image_urls:
                # Ensure the model supports the "image_url" type structure
                prompt_content_list.append({
                    "type": "image_url",
                    "image_url": {
                        "url": url,
                        # Detail level might be adjustable for some models, e.g., "low", "high", "auto"
                        # "detail": "auto"
                    }
                })

        # Structure the request payload for OpenRouter
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            # Optional: Add Referer and X-Title headers as recommended by OpenRouter
            # "HTTP-Referer": "YOUR_SITE_URL", # Replace with your bot's project URL if applicable
            # "X-Title": "Your Bot Name", # Replace with your bot's name
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                # You can add a system prompt here if desired
                # {"role": "system", "content": "You are a helpful Discord moderation assistant."},
                {"role": "user", "content": prompt_content_list}
            ],
            "max_tokens": 500, # Adjust as needed, ensure it's enough for the JSON response
            "temperature": 0.2, # Lower temperature for more deterministic moderation responses
            # Enforce JSON output if the model supports it (some models use tool/function calling)
            # "response_format": {"type": "json_object"} # Uncomment if model supports this parameter
        }

        try:
            print(f"Querying OpenRouter model {OPENROUTER_MODEL}...")
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

        moderator_role_id = get_guild_config(message.guild.id, "MODERATOR_ROLE_ID")
        moderator_role = message.guild.get_role(moderator_role_id) if moderator_role_id else None
        mod_ping = moderator_role.mention if moderator_role else f"Moderators (Role ID {moderator_role_id} not found)"

        # --- Transmit action info over HTTP POST ---
        try:
            mod_log_api_secret = os.getenv("MOD_LOG_API_SECRET")
            if mod_log_api_secret:
                guild_id = message.guild.id
                post_url = f"https://slipstreamm.dev/dashboard/api/guilds/{guild_id}/ai-moderation-action"
                payload = {
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "guild_id": guild_id,
                    "guild_name": message.guild.name,
                    "channel_id": message.channel.id,
                    "channel_name": message.channel.name,
                    "message_id": message.id,
                    "message_link": message.jump_url,
                    "user_id": message.author.id,
                    "user_name": str(message.author),
                    "action": action,
                    "rule_violated": rule_violated,
                    "reasoning": reasoning,
                    "violation": ai_decision.get("violation", False),
                    "message_content": message.content[:1024] if message.content else "",
                    "full_message_content": message.content if message.content else "",
                    "attachments": [a.url for a in message.attachments] if message.attachments else [],
                    "ai_model": OPENROUTER_MODEL,
                    "result": "pending"
                }
                headers = {
                    "Authorization": f"Bearer {mod_log_api_secret}",
                    "Content-Type": "application/json"
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(post_url, headers=headers, json=payload, timeout=10) as resp:
                        payload["result"] = "success" if resp.status < 400 else f"error:{resp.status}"
            else:
                print("MOD_LOG_API_SECRET not set; skipping action POST.")
        except Exception as e:
            print(f"Failed to POST action info: {e}")

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
        if message.attachments:
            attachment_urls = "\n".join(a.url for a in message.attachments)
            notification_embed.add_field(name="Attachments", value=attachment_urls[:1024], inline=False)
        notification_embed.set_footer(text=f"AI Model: {OPENROUTER_MODEL}")
        notification_embed.timestamp = discord.utils.utcnow()

        action_taken_message = "" # To append to the notification

        # --- Hardcoded Action Overrides (Crucial for Safety) ---
        if rule_violated == "5A" or rule_violated == "5":
            action = "BAN" # Force BAN for rule 5/5A regardless of AI suggestion
            print(f"ALERT: Rule {rule_violated} violation detected. Overriding action to BAN.")

        # --- Perform Actions ---
        try:
            if action == "BAN":
                action_taken_message = f"Action Taken: User **BANNED** and message deleted."
                notification_embed.color = discord.Color.dark_red()
                try:
                    # Attempt to delete the message first
                    await message.delete()
                except discord.NotFound:
                    print("Message already deleted before banning.")
                except discord.Forbidden:
                    print(f"WARNING: Missing permissions to delete message before banning user {message.author}.")
                    action_taken_message += " (Failed to delete message - check permissions)"

                # Ban the user
                ban_reason = f"Violation of Rule {rule_violated}. AI Reason: {reasoning}"
                await message.guild.ban(message.author, reason=ban_reason, delete_message_days=1) # Delete last 1 day of messages
                print(f"BANNED user {message.author} for violating rule {rule_violated}.")

            elif action == "DELETE":
                action_taken_message = f"Action Taken: Message **DELETED**."
                await message.delete()
                print(f"DELETED message from {message.author} for violating rule {rule_violated}.")

            elif action == "WARN":
                 # For WARN, we will delete the message and notify mods. Optionally DM user.
                action_taken_message = f"Action Taken: Message **DELETED** (AI suggested WARN)."
                notification_embed.color = discord.Color.orange()
                await message.delete()
                print(f"DELETED message from {message.author} (AI suggested WARN for rule {rule_violated}).")
                # Optional: DM the user
                try:
                    dm_channel = await message.author.create_dm()
                    await dm_channel.send(
                        f"Your recent message in **{message.guild.name}** was removed for violating Rule **{rule_violated}**. "
                        f"Reason: _{reasoning}_. Please review the server rules carefully."
                    )
                    action_taken_message += " User notified via DM."
                except discord.Forbidden:
                    print(f"Could not DM warning to {message.author} (DMs likely disabled).")
                    action_taken_message += " (Could not DM user)."
                except Exception as e:
                    print(f"Error sending DM to {message.author}: {e}")
                    action_taken_message += " (Error sending DM)."


            elif action == "NOTIFY_MODS":
                action_taken_message = "Action Taken: **Moderator review requested.**"
                notification_embed.color = discord.Color.gold()
                print(f"Notifying moderators about potential violation (Rule {rule_violated}) by {message.author}.")

            elif action == "SUICIDAL":
                action_taken_message = "Action Taken: **User DMed resources, relevant role notified.**"
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
        # Ignore messages without content and attachments (unless you specifically want to analyze images alone)
        if not message.content and not message.attachments:
             return
        # Ignore DMs
        if not message.guild:
            return
        # Check if moderation is enabled for this guild
        if not get_guild_config(message.guild.id, "ENABLED", True):
            return

        # --- Suicidal Content Check ---
        message_content_lower = message.content.lower()
        # Suicidal keyword check removed; handled by OpenRouter AI moderation.

        # --- Rule 6 Check (Channel Usage - Basic) ---
        # Simple check for common bot command prefixes in wrong channels
        common_prefixes = ('!', '?', '.', '$', '%', '/', '-') # Add more if needed
        is_likely_bot_command = message.content.startswith(common_prefixes)
        bot_commands_channel_ids = get_guild_config(message.guild.id, "BOT_COMMANDS_CHANNEL_ID", [])
        if isinstance(bot_commands_channel_ids, int):
            bot_commands_channel_ids = [bot_commands_channel_ids]
        is_in_bot_commands_channel = message.channel.id in bot_commands_channel_ids
        suggestions_channel_id = get_guild_config(message.guild.id, "SUGGESTIONS_CHANNEL_ID")
        is_in_suggestions_channel = message.channel.id == suggestions_channel_id

        # If it looks like a command AND it's NOT in the commands channel...
        if is_likely_bot_command and not is_in_bot_commands_channel:
            try:
                await message.delete()
                bot_commands_channel_id = bot_commands_channel_ids[0] if bot_commands_channel_ids else None
                warning_channel_ref = f"<#{bot_commands_channel_id}>" if bot_commands_channel_id else "the correct channel"
                warning = await message.channel.send(
                    f"{message.author.mention}, please use bot commands only in {warning_channel_ref} (Rule 6).",
                    delete_after=20 # Delete the warning after 20 seconds
                )
                print(f"Deleted message from {message.author} in #{message.channel.name} for violating Rule 6 (Bot Command).")
            except discord.Forbidden:
                print(f"Missing permissions to delete message/send warning in #{message.channel.name} for Rule 6 violation.")
            except discord.NotFound:
                print("Message already deleted (Rule 6 check).")
            return # Stop further processing for this message

        # --- Prepare for AI Analysis ---
        message_content = message.content
        # Extract image URLs from attachments
        image_urls = [
            attachment.url for attachment in message.attachments
            if attachment.content_type and attachment.content_type.startswith('image/')
        ]

        # Only proceed with AI analysis if there's text OR images to analyze
        if not message_content and not image_urls:
            return

        # --- Rule 1 Context (NSFW Channel Check) ---
        # Determine if the current channel is designated as NSFW
        nsfw_channel_ids = get_guild_config(message.guild.id, "NSFW_CHANNEL_IDS", [])
        is_nsfw_channel = message.channel.id in nsfw_channel_ids or \
                          (hasattr(message.channel, 'is_nsfw') and message.channel.is_nsfw())

        # --- Call AI for Analysis (Rules 1-5A, 7) ---
        # Skip AI call if API key isn't set correctly
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
             # This check prevents API calls if the key wasn't loaded.
             # The warning is printed during __init__ and query_openrouter.
             # print("Skipping AI analysis because API key is not configured.") # Reduce log spam
             return

        print(f"Analyzing message {message.id} from {message.author} in #{message.channel.name}...")
        ai_decision = await self.query_openrouter(message, message_content, image_urls)

        # --- Process AI Decision ---
        if not ai_decision:
            print(f"Failed to get valid AI decision for message {message.id}.")
            # Optionally notify mods about AI failure if it happens often
            return # Stop if AI fails or returns invalid data

        # Check if the AI flagged a violation
        if ai_decision.get("violation"):
            rule_violated = ai_decision.get("rule_violated", "Unknown")

            # --- Rule 1 Specific Handling (NSFW Content in Wrong Channel) ---
            is_content_nsfw = rule_violated in ["1", "4", "5", "5A"] # Rules indicating potentially NSFW content

            if is_content_nsfw and not is_nsfw_channel:
                print(f"AI flagged NSFW content (Rule {rule_violated}) in NON-NSFW channel #{message.channel.name}. Overriding action if necessary.")
                # Ensure severe action for severe content even if AI was lenient
                if rule_violated in ["5", "5A"]:
                    ai_decision["action"] = "BAN"
                elif rule_violated == "4": # AI Porn
                     ai_decision["action"] = "DELETE" # Ensure deletion at minimum
                else: # General NSFW (Rule 1)
                     ai_decision["action"] = "DELETE" # Ensure deletion for Rule 1 in wrong channel

                # Proceed to handle the violation with potentially updated action
                await self.handle_violation(message, ai_decision)

            elif is_content_nsfw and is_nsfw_channel:
                # Content is NSFW, but it's in an NSFW channel.
                # ONLY take action if it violates Rules 4, 5, or 5A (AI/Illegal Porn)
                if rule_violated in ["4", "5", "5A"]:
                    print(f"AI flagged illegal/AI content (Rule {rule_violated}) within NSFW channel #{message.channel.name}. Proceeding with action.")
                    await self.handle_violation(message, ai_decision)
                else:
                    # It's Rule 1 (General NSFW) in an NSFW channel - this is allowed by rules.
                    print(f"AI flagged Rule 1 violation in designated NSFW channel #{message.channel.name}. Ignoring as per rules.")
                    # Do nothing, even if AI suggested an action for Rule 1 here.

            else:
                # Violation is not NSFW-related (e.g., Rule 2, 3, 6) or occurred in appropriate channel
                # Handle normally based on AI decision
                await self.handle_violation(message, ai_decision)
        else:
            # AI found no violation
            print(f"AI analysis complete for message {message.id}. No violation detected.")


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
        # raise ValueError("AI_API_KEY environment variable is not configured. Cannot load ModerationCog.")
    await bot.add_cog(ModerationCog(bot))
    print("ModerationCog has been loaded.")
