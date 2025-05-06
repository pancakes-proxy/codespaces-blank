# moderation_cog.py
import discord
from discord.ext import commands
import aiohttp # For making asynchronous HTTP requests
import json
import os # To load API key from environment variables

# --- Configuration ---
# Load the OpenRouter API key from the environment variable "AI_API_KEY"
# Fallback to a placeholder if the environment variable is not set.
OPENROUTER_API_KEY = os.getenv("AI_API_KEY", "YOUR_OPENROUTER_API_KEY")
# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Choose a multimodal model from OpenRouter capable of processing text and images
# Examples: 'openai/gpt-4o', 'google/gemini-pro-vision', 'anthropic/claude-3-opus-20240229'
# Ensure the model you choose supports image URLs
OPENROUTER_MODEL = "meta-llama/llama-3.2-11b-vision-instruct" # Make sure this model is available via your OpenRouter key

# Discord Configuration
MODERATOR_ROLE_ID = 1361031007536549979 # Role to ping for violations
BOT_COMMANDS_CHANNEL_ID = 1360717341775630637 # <#1360717341775630637>
SUGGESTIONS_CHANNEL_ID = 1361752490210492489 # <#1361752490210492489>
# Add the IDs of your designated NSFW channels here for Rule 1 check
NSFW_CHANNEL_IDS = [1360708304187297844, 1360842650617647164, 1360842660213952713, 1360842670473216030, 1361081722426364006, 1360859057644245063, 1361892988539896029, 1365524778735239268, 1361097898799927437, 1361097565591961640, 1360842695806812180, 1361097983097049210] # Example: [123456789012345678, 987654321098765432]

# Server rules to provide context to the AI
SERVER_RULES = """
# Server Rules
1. Keep NSFW stuff in NSFW channels. No full-on porn or explicit images outside of those spaces. Emojis and jokes are fine.
2. Be respectful. No harassment, hate, or bullying.
3. No discrimination. This includes gender identity, sexual orientation, race, etc.
4. No AI-generated porn.
5. No pedophilia.
(5A: no IRL porn (for this ban the user and delete the message))
6. Use the right channels. Bot commands go in <#1360717341775630637>, unless it’s part of a bot game or event.
7. Suggestions are welcome! Drop them in <#1361752490210492489> if you’ve got any ideas.

If someone breaks the rules, ping <@&1361031007536549979>.
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
            print("=== Make sure the 'AI_API_KEY' environment variable is set correctly. ===")
            print("="*60 + "\n")
        else:
             print("Successfully loaded API key from AI_API_KEY environment variable.")


    async def cog_unload(self):
        """Clean up the session when the cog is unloaded."""
        await self.session.close()
        print("ModerationCog Unloaded, session closed.")

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
2. Determine if ANY rule is violated. Pay EXTREME attention to rules 5 (Pedophilia) and 5A (IRL Porn). Rule 5A violation requires immediate BAN action. Rule 4 (AI Porn) and Rule 1 (NSFW outside designated channels) are also important.
3. Respond ONLY with a single JSON object containing the following keys:
    - "violation": boolean (true if any rule is violated, false otherwise)
    - "rule_violated": string (The number of the rule violated, e.g., "1", "5A", "None". If multiple rules are violated, state the MOST SEVERE one, prioritizing 5A > 5 > 4 > 3 > 2 > 1 > 6).
    - "reasoning": string (A concise explanation for your decision, referencing the specific rule and content).
    - "action": string (Suggest ONE action based on the violation severity: "IGNORE", "WARN", "DELETE", "BAN", "NOTIFY_MODS". Mandatory "BAN" for rule 5A or 5. "DELETE" for rule 4 or rule 1 in wrong channel. "WARN" or "DELETE" for 2, 3. "NOTIFY_MODS" if unsure but suspicious).

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
            print(f"An unexpected error occurred during OpenRouter API call: {e}")
            return None

    async def handle_violation(self, message: discord.Message, ai_decision: dict):
        """
        Takes action based on the AI's violation decision.
        """
        rule_violated = ai_decision.get("rule_violated", "Unknown")
        reasoning = ai_decision.get("reasoning", "No reasoning provided.")
        action = ai_decision.get("action", "NOTIFY_MODS").upper() # Default to notify mods

        moderator_role = message.guild.get_role(MODERATOR_ROLE_ID)
        mod_ping = moderator_role.mention if moderator_role else f"Moderators (Role ID {MODERATOR_ROLE_ID} not found)"

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

            else: # Includes "IGNORE" or unexpected actions
                if ai_decision.get("violation"): # If violation is true but action is IGNORE
                     action_taken_message = "Action Taken: **None** (AI suggested IGNORE despite flagging violation - Review Recommended)."
                     notification_embed.color = discord.Color.light_grey()
                     print(f"AI flagged violation ({rule_violated}) but suggested IGNORE for message by {message.author}. Notifying mods for review.")
                else:
                    # This case shouldn't be reached if called correctly, but handle defensively
                    print(f"No action taken for message by {message.author} (AI Action: {action}, Violation: False)")
                    return # Don't notify if no violation and action is IGNORE

            # --- Send Notification to Moderators ---
            if moderator_role:
                # Find a channel to send the notification (e.g., a dedicated mod-log channel)
                # For simplicity, sending to the channel where violation occurred, but pinging role.
                # Consider creating a dedicated mod log channel and sending there instead.
                log_channel = message.channel # Or replace with: self.bot.get_channel(YOUR_MOD_LOG_CHANNEL_ID)
                if log_channel:
                    final_message = f"{mod_ping}\n{action_taken_message}"
                    await log_channel.send(content=final_message, embed=notification_embed)
                else:
                    print(f"ERROR: Could not find channel {message.channel.id} to send mod notification.")
            else:
                print(f"ERROR: Moderator role ID {MODERATOR_ROLE_ID} not found.")


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

        # --- Rule 6 Check (Channel Usage - Basic) ---
        # Simple check for common bot command prefixes in wrong channels
        common_prefixes = ('!', '?', '.', '$', '%', '/', '-') # Add more if needed
        is_likely_bot_command = message.content.startswith(common_prefixes)
        is_in_bot_commands_channel = message.channel.id == BOT_COMMANDS_CHANNEL_ID
        # Also check if it's in the suggestions channel (Rule 7 context)
        is_in_suggestions_channel = message.channel.id == SUGGESTIONS_CHANNEL_ID

        # If it looks like a command AND it's NOT in the commands channel...
        if is_likely_bot_command and not is_in_bot_commands_channel:
            # Add exceptions here if needed (e.g., specific channels where commands ARE allowed)
            # if message.channel.id in [ALLOWED_COMMAND_CHANNELS]:
            #     pass # Skip rule 6 check for these channels
            # else:
                try:
                    await message.delete()
                    warning = await message.channel.send(
                        f"{message.author.mention}, please use bot commands only in <#{BOT_COMMANDS_CHANNEL_ID}> (Rule 6).",
                        delete_after=20 # Delete the warning after 20 seconds
                    )
                    print(f"Deleted message from {message.author} in #{message.channel.name} for violating Rule 6 (Bot Command).")
                    # Optionally log this to mods if it happens frequently
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
        is_nsfw_channel = message.channel.id in NSFW_CHANNEL_IDS or \
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
