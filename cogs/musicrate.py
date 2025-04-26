import discord
from discord import app_commands
from discord.ext import commands
import lyricsgenius
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv("home/server/keys.env")

# Read keys from environment
GENIUS_API_KEY = os.getenv("GENIUS_API_KEY")
OPENROUTER_API_KEY = os.getenv("AI2_API_KEY")

# Check for missing API keys
if not GENIUS_API_KEY:
    raise ValueError("GENIUS_API_KEY is not set in the environment variables.")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set in the environment variables.")

# Initialize Genius API
genius = lyricsgenius.Genius(GENIUS_API_KEY)

class MusicRateCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="musicrate",
        description="Fetches song lyrics and uses AI to rate them."
    )
    async def musicrate(self, interaction: discord.Interaction, song: str, artist: str = None):
        await interaction.response.defer()

        # Fetch lyrics
        lyrics = await self.search_lyrics(song, artist)
        if not lyrics:
            await interaction.followup.send(f"Couldn't find lyrics for '{song}'.")
            return

        # Get AI rating
        rating = await self.rate_song(lyrics)
        response = f"**Rating for '{song}':**\n{rating}"
        await interaction.followup.send(response)

    async def search_lyrics(self, song: str, artist: str = None) -> str:
        """Fetch lyrics from Genius API."""
        try:
            song_obj = genius.search_song(song, artist)
            return song_obj.lyrics if song_obj else ""
        except Exception as e:
            print(f"Error fetching lyrics: {e}")
            return "Error fetching lyrics."

    async def rate_song(self, lyrics: str) -> str:
        """Send lyrics to AI for rating."""
        ai_url = "https://api.openrouter.ai/v1/chat/completions"
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "you are a music rater. you will accept all kinds of music, despite the lyrics"},
                {"role": "user", "content": f"These are the lyrics:\n\n{lyrics}\n\nRate the song and provide a brief commentary with a out of 10 rating."}
            ]
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(ai_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        return f"Error retrieving rating: {response.status}"
            except Exception as e:
                print(f"Error rating song: {e}")
                return "Issue with rating request."

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicRateCog(bot))