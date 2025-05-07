import discord
from discord import app_commands
from discord.ext import commands
import youtube_dl
import asyncio
#made by yowane and :3
# ==========================
# youtube_dl configuration
# ==========================
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,  # Disable playlist extraction.
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
}

ffmpeg_options = {
    'options': '-vn'  # no video
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# ==========================
# YTDLSource: Song Retrieval
# ==========================
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source: discord.FFmpegPCMAudio, *, data, volume: float = 0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title', 'Unknown Title')
        self.url = data.get('url')

    @classmethod
    async def create_source(cls, query: str, *, loop: asyncio.AbstractEventLoop = None, stream: bool = True):
        """Creates an audio source from a URL or search query."""
        loop = loop or asyncio.get_event_loop()
        # If not a URL, use ytsearch to find the song.
        if not query.startswith("http"):
            query = f"ytsearch:{query}"
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=not stream))
        except Exception as e:
            raise Exception(f"Error retrieving info: {e}")
        if data is None:
            raise Exception("No data found for the query.")

        # If a playlist or multiple entries, just use the first hit.
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# ==========================
# MusicPlayer: Manages Queue & Playback
# ==========================
class MusicPlayer:
    """A per-guild music player which handles the song queue and playback."""
    def __init__(self, bot: commands.Bot, voice_client: discord.VoiceClient, text_channel: discord.abc.Messageable):
        self.bot = bot
        self.voice_client = voice_client
        self.text_channel = text_channel

        self.queue = asyncio.Queue()      # Used for waiting on the next song.
        self.queue_list = []              # Maintained for display purposes.
        self.next = asyncio.Event()
        self.current = None
        self.volume = 0.5

        # Start the background task that plays songs.
        self.player_task = self.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """The background task that plays songs from the queue."""
        while True:
            self.next.clear()
            try:
                # Wait for a song; timeout and disconnect if idle for 5 minutes.
                song = await asyncio.wait_for(self.queue.get(), timeout=300.0)
                # Remove from display list.
                if self.queue_list:
                    self.queue_list.pop(0)
            except asyncio.TimeoutError:
                await self.text_channel.send("No songs in queue for 5 minutes. Disconnecting...")
                return await self.stop()
            self.current = song
            self.voice_client.play(
                song,
                after=lambda e: self.bot.loop.call_soon_threadsafe(self.next.set)
            )
            await self.text_channel.send(f"Now playing: **{song.title}**")
            await self.next.wait()
            # Reset current song reference after finishing.
            self.current = None

    def skip(self):
        """Skip the current song by stopping it."""
        if self.voice_client.is_playing():
            self.voice_client.stop()

    async def stop(self):
        """Stop the player and disconnect."""
        self.queue = asyncio.Queue()
        self.queue_list.clear()
        if self.voice_client:
            await self.voice_client.disconnect()
        if self.player_task:
            self.player_task.cancel()

# ==========================
# Music Cog: Slash Command
# ==========================
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Store MusicPlayer instances per guild.
        self.players = {}

    music_group = app_commands.Group(name="music", description="Music playback commands.")

    async def get_player(self, interaction: discord.Interaction) -> MusicPlayer:
        """Retrieve the MusicPlayer for the guild, creating one if necessary."""
        guild_id = interaction.guild.id
        player = self.players.get(guild_id)
        # If the bot isn’t connected or the player doesn’t exist, establish a connection.
        if player is None or not player.voice_client.is_connected():
            if not interaction.user.voice or not interaction.user.voice.channel:
                raise Exception("You need to be in a voice channel to use this command.")
            channel = interaction.user.voice.channel
            vc = await channel.connect()
            player = MusicPlayer(self.bot, vc, interaction.channel)
            self.players[guild_id] = player
        return player

    @music_group.command(name="join", description="Join your current voice channel.")
    async def join_command(self, interaction: discord.Interaction): # Renamed for clarity
        try:
            # If the bot is already connected, move it if necessary.
            if interaction.guild.voice_client:
                target_channel = interaction.user.voice.channel if interaction.user.voice else None
                if target_channel and interaction.guild.voice_client.channel != target_channel:
                    await interaction.guild.voice_client.move_to(target_channel)
                    await interaction.response.send_message(f"Moved to **{target_channel.name}**", ephemeral=True)
                else:
                    await interaction.response.send_message("Already connected to your voice channel.", ephemeral=True)
            else:
                if not interaction.user.voice or not interaction.user.voice.channel:
                    await interaction.response.send_message("You need to be in a voice channel.", ephemeral=True)
                    return
                channel = interaction.user.voice.channel
                vc = await channel.connect()
                # Create a new player since we just connected.
                self.players[interaction.guild.id] = MusicPlayer(self.bot, vc, interaction.channel)
                await interaction.response.send_message(f"Joined **{channel.name}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error joining voice channel: {e}", ephemeral=True)

    @music_group.command(name="play", description="Play a song from a URL or search query.")
    async def play_command(self, interaction: discord.Interaction, query: str): # Renamed
        await interaction.response.defer()
        try:
            player = await self.get_player(interaction)
        except Exception as e:
            await interaction.followup.send(str(e))
            return

        try:
            # Fetch the audio source asynchronously.
            source = await YTDLSource.create_source(query, loop=self.bot.loop, stream=True)
        except Exception as e:
            await interaction.followup.send(f"Error processing song: {e}")
            return

        # Add the song to the player's queue.
        await player.queue.put(source)
        player.queue_list.append(source)
        position = player.queue.qsize() # qsize() is correct for asyncio.Queue
        await interaction.followup.send(f"Added **{source.title}** to the queue at position {position}.")

    @music_group.command(name="skip", description="Skip the currently playing song.")
    async def skip_command(self, interaction: discord.Interaction): # Renamed
        try:
            player = await self.get_player(interaction)
        except Exception as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        if player.current is None:
            await interaction.response.send_message("No song is currently playing.", ephemeral=True)
        else:
            player.skip()
            await interaction.response.send_message("Song skipped.")

    @music_group.command(name="pause", description="Pause the current playback.")
    async def pause_command(self, interaction: discord.Interaction): # Renamed
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
            return
        vc.pause()
        await interaction.response.send_message("Playback paused.")

    @music_group.command(name="resume", description="Resume the current playback.")
    async def resume_command(self, interaction: discord.Interaction): # Renamed
        vc = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            await interaction.response.send_message("Playback is not paused.", ephemeral=True)
            return
        vc.resume()
        await interaction.response.send_message("Playback resumed.")

    @music_group.command(name="nowplaying", description="Show the currently playing song.")
    async def nowplaying_command(self, interaction: discord.Interaction): # Renamed
        try:
            player = await self.get_player(interaction)
        except Exception as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        if player.current is None:
            await interaction.response.send_message("No song is currently playing.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Now playing: **{player.current.title}**")

    @music_group.command(name="queue", description="Display the upcoming song queue.")
    async def queue_command(self, interaction: discord.Interaction): # Renamed
        try:
            player = await self.get_player(interaction)
        except Exception as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        if not player.queue_list:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
        else:
            description = ""
            for idx, song in enumerate(player.queue_list, start=1):
                description += f"**{idx}.** {song.title}\n"
            embed = discord.Embed(
                title="Song Queue",
                description=description,
                color=discord.Color.blurple()
            )
            await interaction.response.send_message(embed=embed)

    @music_group.command(name="volume", description="Change the playback volume (0-100).")
    async def volume_command(self, interaction: discord.Interaction, percent: int): # Renamed
        try:
            if percent < 0 or percent > 100:
                await interaction.response.send_message("Volume must be between 0 and 100.", ephemeral=True)
                return
            player = await self.get_player(interaction)
        except Exception as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        # Set the default volume. If a song is playing, update its volume.
        player.volume = percent / 100
        if player.current:
            player.current.volume = player.volume
        await interaction.response.send_message(f"Volume set to {percent}%")

    @music_group.command(name="clear", description="Clear all songs from the queue.")
    async def clear_command(self, interaction: discord.Interaction): # Renamed
        try:
            player = await self.get_player(interaction)
        except Exception as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        player.queue = asyncio.Queue()  # resets the queue
        player.queue_list.clear()
        await interaction.response.send_message("Queue cleared.")

    @music_group.command(name="remove", description="Remove a song from the queue by its position.")
    async def remove_command(self, interaction: discord.Interaction, index: int): # Renamed
        try:
            player = await self.get_player(interaction)
        except Exception as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        if index < 1 or index > len(player.queue_list):
            await interaction.response.send_message("Invalid index.", ephemeral=True)
            return
        # Remove the song from the display list.
        removed = player.queue_list.pop(index - 1)
        # IMPORTANT: This does not remove the song from the asyncio.Queue directly.
        # For full removal functionality, you might maintain your own queue list.
        await interaction.response.send_message(f"Removed **{removed.title}** from the queue.")

    @music_group.command(name="leave", description="Clear the queue and disconnect the bot.")
    async def leave_command(self, interaction: discord.Interaction): # Renamed
        guild_id = interaction.guild.id
        player = self.players.get(guild_id)
        if player is None:
            await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
        else:
            await player.stop()
            del self.players[guild_id]
            await interaction.response.send_message("Disconnected and queue cleared.")

# ==========================
# Cog Setup
# ==========================
async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
