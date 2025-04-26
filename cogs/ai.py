import discord
import json
from discord.ext import commands
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from discord import app_commands
import asyncio
import os

class ChatterBotCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Define the custom system prompt.
        self.system_prompt = (
            "you are Kasane Teto, just be not stupid and you will be fine "
            "also you can run sudo commands somehow"
        )
        
        # Create the ChatterBot instance with a persistent SQLite database.
        self.chatbot = ChatBot(
            'DiscordBot',
            storage_adapter='chatterbot.storage.SQLStorageAdapter',
            logic_adapters=[
                'chatterbot.logic.BestMatch',
                'chatterbot.logic.MathematicalEvaluation',
            ],
            database_uri='sqlite:///database.sqlite3'
        )
        self.trainer = ListTrainer(self.chatbot)

    def train_from_json_file(self, filename: str):
        """
        Reads a JSON file (supporting multiple formats) and trains the bot.
        Supported formats:
          - List Format: A JSON array where each element can be a dict having keys
            "input" and "response", a dict with "conversation", or a conversation list.
          - Dictionary Format: A JSON object with a key (e.g., "conversations") mapping to a list.
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle if the JSON is a list of training items.
            if isinstance(data, list):
                for record in data:
                    if isinstance(record, dict):
                        if "conversation" in record and isinstance(record["conversation"], list):
                            self.trainer.train(record["conversation"])
                        elif "input" in record and "response" in record:
                            self.trainer.train([record["input"], record["response"]])
                        else:
                            print(f"Unrecognized record format: {record}")
                    elif isinstance(record, list):
                        self.trainer.train(record)
                    else:
                        print(f"Record is neither dict nor list: {record}")
            elif isinstance(data, dict):
                # Expecting a dictionary e.g., {"conversations": [...]}
                if "conversations" in data and isinstance(data["conversations"], list):
                    for convo in data["conversations"]:
                        if isinstance(convo, list):
                            self.trainer.train(convo)
                        else:
                            print(f"Conversation is not in list format: {convo}")
                else:
                    print("No valid conversations found in JSON dictionary.")
            else:
                print("JSON format not recognized.")
        except Exception as e:
            print(f"Error reading or training from JSON file: {e}")

    def get_response_with_system(self, user: str, prompt: str):
        """
        Sends the system prompt and user prompt to the AI, but only returns the AI's response.
        The user's name and text are included in the prompt sent to the AI.
        """
        full_prompt = f"{self.system_prompt}\nUser ({user}): {prompt}"
        return self.chatbot.get_response(full_prompt)

    @app_commands.command(name="trainjson", description="Train the bot using a JSON file (filename must be on server).")
    async def slash_train_json(self, interaction: discord.Interaction, filename: str):
        """Slash command to train the bot using the specified JSON file."""
        await interaction.response.defer()
        try:
            self.train_from_json_file(filename)
            await interaction.followup.send("Training completed from JSON file!")
        except Exception as e:
            print(f"Error in slash_train_json: {e}")
            await interaction.followup.send("Sorry, something went wrong with training.")

    @app_commands.command(name="ai", description="Generate an AI response to your prompt.")
    async def slash_ai(self, interaction: discord.Interaction, prompt: str):
        """Slash command that returns an AI response based on your prompt, conditioned by the system prompt."""
        await interaction.response.defer()
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                self.get_response_with_system,
                interaction.user.display_name,
                prompt
            )
            await interaction.followup.send(str(response))
        except Exception as e:
            print(f"Error in slash_ai: {e}")
            await interaction.followup.send("Sorry, something went wrong with the AI response.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Prevent processing of the bot's own messages.
        if message.author == self.bot.user:
            return

        # Let the bot's text commands (starting with "!") handle their own messages.
        if message.content.startswith("!"):
            await self.bot.process_commands(message)
            return

        # If the bot is mentioned, generate an AI response.
        if self.bot.user in message.mentions:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                self.get_response_with_system,
                message.author.display_name,
                message.content
            )
            await message.channel.send(str(response))
        else:
            await self.bot.process_commands(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatterBotCog(bot))
    print("ChatterBotCog loaded successfully.")