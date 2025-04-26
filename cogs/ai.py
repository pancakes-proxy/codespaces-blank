import discord
import json
from discord.ext import commands
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from discord import app_commands

class ChatterBotCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Define the system prompt for every AI response.
        self.system_prompt = ("you are Kasane Teto, just be not stupid and you will be fine "
                              "also you can run sudo commands somehow")
        
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
        
        Supported input formats:
          - List Format: A JSON array where each element can be either a dictionary with keys
            "input" and "response", a dictionary with "conversation" mapping to a list,
            or a plain conversation list (array of strings).
          - Dictionary Format: A JSON object with a key like "conversations" that maps to a list of conversation arrays.
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

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

    def get_response_with_system(self, prompt: str):
        """
        Prepend the system prompt to the user's prompt.
        This ensures every call to get_response is conditioned by the system instructions.
        """
        full_prompt = f"{self.system_prompt}\nUser: {prompt}"
        return self.chatbot.get_response(full_prompt)

    @app_commands.command(name="aichat", description="Generate an AI response to your prompt.")
    async def slash_ai(self, interaction: discord.Interaction, prompt: str):
        """
        Slash command that generates an AI response based on your prompt,
        conditioned by the system prompt.
        Usage: /chat prompt:<your prompt here>
        """
        response = self.get_response_with_system(prompt)
        await interaction.response.send_message(str(response))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Avoid processing bot's own messages.
        if message.author == self.bot.user:
            return
        
        # If the bot is mentioned, generate an AI response including the system prompt.
        if self.bot.user in message.mentions:
            response = self.get_response_with_system(message.content)
            await message.channel.send(str(response))

    async def cog_load(self):
        # Register the slash command so it's available to your guilds.
        self.bot.tree.add_command(self.slash_ai)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatterBotCog(bot))
