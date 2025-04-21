import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv("/home/server/keys.env")
discord_token = os.getenv("DISCORD_TOKEN")

# Ensure token is set
if not discord_token:
    raise ValueError("Missing DISCORD_TOKEN environment variable.")

# Configure bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load cog files dynamically
async def load_cogs():
    for filename in os.listdir("/home/server/wdiscordbot/cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename}")
            except Exception as e:
                print(f"Failed to load cog {filename}: {e}")

@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync slash commands after bot is ready
    print(f"Logged in as {bot.user}")
    print("Slash commands synced.")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(discord_token)

asyncio.run(main())