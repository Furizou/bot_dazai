from typing import Final
import discord
from discord.ext import commands
import asyncio
import yt_dlp
from yt_dlp.utils import DownloadError
from apps.ffmpeg_setup import voice_client_dict, ytdl, ffmpeg_options, music_queue, timeout_timers
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
import os

from discord.ui import View, Button
from discord import ButtonStyle, Message
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

class MusicControlView(View):
    def __init__(self, voice_channel_id: int, music_cog: commands.Cog):
        super().__init__(timeout=None)  # Persistent view
        self.voice_channel_id = voice_channel_id
        self.music_cog = music_cog  # Reference to MusicCog to call its methods

    async def is_authorized(self, interaction: discord.Interaction) -> bool:
        """
        Checks if the user is in the same voice channel as the bot.
        Sends an ephemeral message if the check fails.

        Args:
            interaction (discord.Interaction): The interaction triggering the button.

        Returns:
            bool: True if authorized, False otherwise.
        """
        user_voice = interaction.user.voice
        if not user_voice or user_voice.channel.id != self.voice_channel_id:
            await interaction.response.send_message(
                "You must be in the voice channel to use this button.", 
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Pause", style=ButtonStyle.grey, emoji="⏯️")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle between pausing and resuming the music."""
        # Authorization Check
        if not await self.is_authorized(interaction):
            return

        # Retrieve the voice client
        voice_client = voice_client_dict.get(self.voice_channel_id)
        if not voice_client:
            await interaction.response.send_message(
                "I'm not connected to a voice channel.", 
                ephemeral=True
            )
            return

        if voice_client.is_playing():
            await self.music_cog._pause_music(interaction)
            button.label = "Resume"
            button.style = ButtonStyle.success
            await interaction.message.edit(view=self)
        elif voice_client.is_paused():
            await self.music_cog._resume_music(interaction)
            button.label = "Pause"
            button.style = ButtonStyle.grey
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message(
                "No music is playing currently.", 
                ephemeral=True  # User-specific message
            )
    
    @discord.ui.button(label="Skip", style=ButtonStyle.grey, emoji="⏭️")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip to the next music queue."""
        # Authorization Check
        if not await self.is_authorized(interaction):
            return

        # Call the show_queue method from MusicCog
        await self.music_cog._skip_music(interaction)

    @discord.ui.button(label="Stop", style=ButtonStyle.grey, emoji="⏹️")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop the music playback and disconnect the bot."""
        # Authorization Check
        if not await self.is_authorized(interaction):
            return

        # Call the stop_music method from MusicCog
        await self.music_cog._stop_music(interaction)

        # Disable all buttons after stopping
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        await interaction.response.send_message(
            f"Playback stopped and disconnected from {interaction.user.voice.channel.name}.", 
            ephemeral=False  # Public message
        )

    @discord.ui.button(label="Show Queue", style=ButtonStyle.grey, emoji="📜")
    async def show_queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Display the current music queue."""
        # Authorization Check
        if not await self.is_authorized(interaction):
            return

        # Call the show_queue method from MusicCog
        await self.music_cog._show_queue(interaction)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Gives access to the bot instance
        
        # Load the YouTube API key here
        self.YOUTUBE_API_KEY: Final[str] = os.getenv('YOUTUBE_API_KEY')
        
        # --- Spotify Setup ---
        self.SPOTIFY_CLIEND_ID: Final[str] = os.getenv("SPOTIFY_CLIENT_ID")
        self.SPOTIFY_CLIENT_SECRET: Final[str] = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=self.SPOTIFY_CLIEND_ID,
                client_secret=self.SPOTIFY_CLIENT_SECRET
            )
        )
        # --- end of Spotify Setup ---

        if not self.YOUTUBE_API_KEY:
            print("YOUTUBE_API_KEY is not set. Please set the environment variable.")
            # Alternatively, you can raise an exception
            raise ValueError("YOUTUBE_API_KEY environment variable not set.")

    # ---------------------- Commands ----------------------

    @commands.command(name='play', help="Play a song from YouTube/Spotify using a URL or search query.")
    async def play_music(self, ctx, *, url_or_query: str):
        await self._play_music(ctx, url_or_query)

    @commands.command(name='qplay', help="Quickplay: Immediately play a song, ignoring queue")
    async def quickplay_music(self, ctx, *, url_or_query: str):
        await self._quickplay_music(ctx, url_or_query)

    @commands.command(name='skip', help="Skip the current song and play the next one in the queue.")
    async def skip_music(self, ctx):
        await self._skip_music(ctx)

    @commands.command(name='queue', help="Display the current music queue.")
    async def show_queue_command(self, ctx):
        await self._show_queue(ctx)

    @commands.command(name='prune', help="Clear the music queue.")
    async def prune_queue(self, ctx):
        await self._prune_queue(ctx)

    @commands.command(name='pause', help="Pause the current music playback.")
    async def pause_music(self, ctx):
        await self._pause_music(ctx)

    @commands.command(name='resume', help="Resume the paused music.")
    async def resume_music(self, ctx):
        await self._resume_music(ctx)

    @commands.command(name='stop', help="Stop music and disconnect from the VC.")
    async def stop_music(self, ctx):
        await self._stop_music(ctx)

    # ---------------------- Helper Methods ----------------------
    async def _handle_song_request(self, ctx, url_or_query: str) -> dict | None:
        """
        A helper that handles the main steps of:
        - Checking user/bot permissions
        - Pre-loading embed
        - Checking if it's YT search, direct link, or Spotify link
        - Searching or extracting via yt_dlp
        - Returning the final song_info dict

        Returns:
        A dict containing song_info
        or None if user canceled/ invalid/ or error occurred.
        """

        # 1) Validate necessary permissions
        bot_permissions = ctx.channel.permissions_for(ctx.guild.me)
        if not bot_permissions.send_messages or not bot_permissions.read_message_history:
            print("I need the **Send Messages** and **Read Message History** permissions to function properly.")
            await ctx.send("I need the **Send Messages** and **Read Message History** permissions to function properly.")
            return None

        # 2) Create a 'pre_loading' embed
        pre_loading_embed = discord.Embed(
            title="Processing your request...",
            description="Please wait while we query the requested song. 🎵",
            color=0x8A3215,
        )
        pre_loading_message = None

        selected_entry = None

        # 3) Distinguish between search query, Spotify link, or direct link
        if not url_or_query.startswith('http'):
            pre_loading_message = await ctx.reply(embed=pre_loading_embed, mention_author=False)

            entries = await self.search_youtube(url_or_query)
            if not entries:
                await ctx.reply("No results found.", mention_author=False)
                return None

            selected_entry = await self.select_song(
                ctx=ctx,
                entries=entries,
                url_or_query=url_or_query,
                loading_message=pre_loading_message
            )
            if not selected_entry:  # User canceled or invalid selection
                return None

        elif "spotify.com/track/" in url_or_query:
            pre_loading_message = await ctx.reply(embed=pre_loading_embed, mention_author=False)
            
            selected_entry = await self.search_spotify(ctx=ctx, url=url_or_query)
            if not selected_entry:  # canceled or invalid
                return None

        else:
            selected_entry = {'url': url_or_query}

        # Remove the pre-loading message if its been used
        if pre_loading_message:
            await pre_loading_message.delete() 

        # 4) Create a loading embed for the actual extraction (yt_dlp)
        loading_embed = discord.Embed(
            title="Processing your request...",
            description="Please wait while we retrieve the song information. 🎵",
            color=0x8A3215,
        )
        loading_message = await ctx.reply(embed=loading_embed, mention_author=False)

        selected_url = selected_entry['url']
        try:
            song_info = await self.extract_song_info(selected_url)
        except ValueError as e:
            await loading_message.edit(embed=discord.Embed(
                title="Error",
                description=str(e),
                color=0xFF0000
            ))
            return None

        # If success, attach the 'requested_by' field
        song_info['requested_by'] = ctx.author

        # Return both the final song_info and the in-progress loading_message
        # so the caller can finalize the embed
        return {
            'song_info': song_info,
            'loading_message': loading_message
        }
    
    async def _prepare_voice_client_and_queue(self, ctx) -> tuple[discord.VoiceClient | None, int | None]:
        """
        Ensures we have a voice client connected in the user's voice channel
        and that the queue dictionary is initialized for that channel.

        Returns:
        (voice_client, voice_channel_id)
        or (None, None) if a critical error occurred (like no voice channel, or failure to connect).
        """
        # 1) Check if the user is in a voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.reply("You must be in a voice channel to use this command.", mention_author=False)
            return (None, None)

        voice_channel = ctx.author.voice.channel
        voice_channel_id = voice_channel.id

        # 2) Initialize the queue for this channel if not present
        if voice_channel_id not in music_queue:
            music_queue[voice_channel_id] = []

        # 3) Connect to the channel if the bot is not already connected
        if (voice_channel_id not in voice_client_dict) or (not voice_client_dict[voice_channel_id].is_connected()):
            try:
                voice_client = await voice_channel.connect()
                voice_client_dict[voice_channel_id] = voice_client
            except discord.ClientException:
                voice_client = voice_client_dict.get(voice_channel_id)  # fallback
            except Exception as e:
                print(f"Error connecting to voice channel: {e}")
                await ctx.reply("Failed to connect to the voice channel.", mention_author=False)
                return (None, None)
        else:
            voice_client = voice_client_dict[voice_channel_id]

        return (voice_client, voice_channel_id)

    async def _play_music(self, ctx, url_or_query: str):
        voice_client, voice_channel_id = await self._prepare_voice_client_and_queue(ctx)
        if not voice_client:    # something failed or user canceled
            return

        request_result = await self._handle_song_request(ctx, url_or_query)
        if not request_result:  # something failed or user canceled
            return  

        # Insert the returned track at the END of the queue
        song_info = request_result['song_info']
        loading_message = request_result['loading_message']
        music_queue[voice_channel_id].append(song_info)
        print(f"Added to queue in {ctx.author.voice.channel.name}: {song_info['title']}")

        # Update loading_message embed
        embed = discord.Embed(
            title=song_info['title'],
            url=song_info['url'],
            description=f"Queue Length: {len(music_queue[voice_channel_id])}",
            color=0x8A3215,
        )
        embed.set_author(name="Added to Queue 🎶")
        if thumbnail := song_info['thumbnail']:
            embed.set_thumbnail(url=thumbnail)
        await loading_message.edit(embed=embed)

        # Cancel idle timer, then if nothing is playing, start
        await self.cancel_timeout_timer(ctx.author.voice.channel)
        if not voice_client_dict[voice_channel_id].is_playing():
            await self.play_next_in_queue(ctx.author.voice.channel, ctx.channel)

    async def _quickplay_music(self, ctx, url_or_query: str):
        voice_client, voice_channel_id = await self._prepare_voice_client_and_queue(ctx)
        if not voice_client:
            return

        request_result = await self._handle_song_request(ctx, url_or_query)
        if not request_result:
            return

        song_info = request_result['song_info']
        loading_message = request_result['loading_message']

        # Insert the track at index 1 for a quickplay
        music_queue[voice_channel_id].insert(1, song_info)
        print(f"Quickplaying in {ctx.author.voice.channel.name}: {song_info['title']}")

        # Update loading_message embed
        embed = discord.Embed(
            title=song_info['title'],
            url=song_info['url'],
            description=f"Queue Length: {len(music_queue[voice_channel_id])}",
            color=0x8A3215,
        )
        embed.set_author(name="Quickplaying 🎵")
        if thumbnail := song_info['thumbnail']:
            embed.set_thumbnail(url=thumbnail)
        await loading_message.edit(embed=embed)

        # Cancel idle timer and skip the current track
        await self.cancel_timeout_timer(ctx.author.voice.channel)
        await self._skip_music(ctx)

    async def _skip_music(self, ctx: commands.Context | discord.Interaction, interaction=False):
        # Determine if the caller is a Context or an Interaction
        if isinstance(ctx, discord.Interaction):
            user = ctx.user
            interaction = True
        else:
            user = ctx.author

        voice_channel = user.voice.channel
        voice_channel_id = voice_channel.id
        try:
            # ----------------- Embed Message ------------------
            song_info = music_queue[voice_channel_id][0]            
            embed = discord.Embed(
                title="**⏭️ Skipping Music..**",
                description=f"[{song_info['title']}]({song_info['url']})",
                color=0x8A3215,
            )
            if thumbnail := song_info['thumbnail']:
                embed.set_thumbnail(url=thumbnail)
            embed.set_footer(
                icon_url=user.display_avatar.url, 
                text=f"Skipped by: {user.display_name}"
            )
            
            if interaction:
                await ctx.response.send_message(embed=embed, ephemeral=False)
            else: 
                await ctx.reply(embed=embed, mention_author=False)
            # --------------------------------------------------
            
            # Stop current playback
            if voice_channel_id in voice_client_dict and voice_client_dict[voice_channel_id].is_playing():
                voice_client_dict[voice_channel_id].stop()

            # Do not remove the current song or call play_next_in_queue here
            # The after_playing callback will handle this

        except Exception as e:
            print(f"Error in skip_music for {voice_channel.name}: {e}")
            await ctx.reply(
                "Unable to skip the song.", 
                mention_author=False
            )

    async def _show_queue(self, ctx: commands.Context | discord.Interaction, interaction=False):
        if isinstance(ctx, discord.Interaction):
            voice_channel = ctx.user.voice.channel
            interaction = True
        else:
            voice_channel = ctx.author.voice.channel
        
        # Check if the queue is empty
        if voice_channel.id not in music_queue or len(music_queue[voice_channel.id]) == 0:
            embed = discord.Embed(
                description=f"The queue is empty in {voice_channel.name}.",
                color=0x8A3215
            )
            await ctx.reply(embed=embed, mention_author=False)

        # Get the current song
        current_song = music_queue[voice_channel.id][0]
        queue_length = len(music_queue[voice_channel.id])

        # Generate queue list using 'webpage_url' for hyperlinks
        queue_lines = [
            f"({idx+1}). **[{song_info['title']}]({song_info['webpage_url']})** • `{self.format_duration(song_info['duration'])}` • <@{song_info['requested_by'].id}>"
            for idx, song_info in enumerate(music_queue[voice_channel.id][1:])
        ]

        # Split queue list into chunks of 1024 characters
        chunks = []
        current_chunk = ""
        for line in queue_lines:
            if len(current_chunk) + len(line) + 1 > 1024:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += ("\n" + line) if current_chunk else line
        if current_chunk:
            chunks.append(current_chunk)

        # Create the embed
        embed = discord.Embed(color=0x8A3215)
        embed.set_author(
            name=f"Music Queue for {ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        embed.add_field(
            name="**Now Playing:**",
            value=f"**[{current_song['title']}]({current_song['webpage_url']})** • `{self.format_duration(current_song['duration'])}` • <@{current_song['requested_by'].id}>",
            inline=False
        )

        # Add queue chunks as fields
        if queue_length > 1:
            for i, chunk in enumerate(chunks, start=1):
                embed.add_field(
                    name=f"**Queue list (Part {i}):**",
                    value=chunk,
                    inline=False
                )
        else:
            embed.add_field(
                name="**Queue list:**",
                value="No more songs in the queue.",
                inline=False
            )

        # Footer with queue length
        embed.set_footer(
            text=f"Queue Length: {queue_length}"
        )

        if interaction:
            return await ctx.response.send_message(embed=embed, ephemeral=False)
        await ctx.reply(embed=embed, mention_author=False)
            
    async def _pause_music(self, ctx: commands.Context | discord.Interaction, interaction=False):
        
        # Determine if the caller is a Context or an Interaction
        if isinstance(ctx, discord.Interaction):
            user = ctx.user
            interaction = True
        else:
            user = ctx.author

        voice_channel = user.voice.channel
        try:
            # ----------------- Embed Message ------------------
            song_info = music_queue[voice_channel.id][0]            
            embed = discord.Embed(
                title="**⏸️ Pausing Music..**",
                description=f"[{song_info['title']}]({song_info['url']})",
                color=0x8A3215,
            )
            if thumbnail := song_info['thumbnail']:
                embed.set_thumbnail(url=thumbnail)
            embed.set_footer(
                icon_url=user.display_avatar.url, 
                text=f"Paused by: {user.display_name}"
            )
            if interaction:
                await ctx.response.send_message(embed=embed, ephemeral=False)
            else: 
                await ctx.reply(embed=embed, mention_author=False)
            # -------------------------------------------------
            
            voice_client_dict[voice_channel.id].pause()
        except Exception as e:
            print(f"Error in pause_music: {e}")
            await ctx.reply("Unable to pause the music.", mention_author=False)

    async def _resume_music(self, ctx: commands.Context | discord.Interaction, interaction=False):
        
        # Determine if the caller is a Context or an Interaction
        if isinstance(ctx, discord.Interaction):
            user = ctx.user
            interaction = True
        else:
            user = ctx.author
        
        voice_channel_id = user.voice.channel.id
        try:
            # ----------------- Embed Message ------------------
            song_info = music_queue[voice_channel_id][0]            
            embed = discord.Embed(
                title="**⏯️ Resuming Music..**",
                description=f"[{song_info['title']}]({song_info['url']})",
                color=0x8A3215,
            )
            if thumbnail := song_info['thumbnail']:
                embed.set_thumbnail(url=thumbnail)
            embed.set_footer(
                icon_url=user.display_avatar.url, 
                text=f"Resumed by: {user.display_name}"
            )
            
            if interaction:
                await ctx.response.send_message(embed=embed, ephemeral=False)
            else: 
                await ctx.reply(embed=embed, mention_author=False)
            # -------------------------------------------------
            
            voice_client_dict[voice_channel_id].resume()
        except Exception as e:
            print(f"Error in resume_music: {e}")
            await ctx.reply("Unable to resume the music.", mention_author=False)

    async def _stop_music(self, ctx: commands.Context | discord.Interaction, interaction=False):
        # Determine if the caller is a Context or an Interaction
        if isinstance(ctx, discord.Interaction):
            user = ctx.user
            interaction = True
        else:
            user = ctx.author

        voice_channel = user.voice.channel
        voice_channel_id = voice_channel.id
            
        try:
            # ----------------- Embed Message ------------------  
            if song_info := music_queue[voice_channel_id]:
                song_info = song_info[0]
                description = f"[{song_info['title']}]({song_info['url']})"
            else:
                description = f"Thankyou for using {self.bot.user.mention}"

            embed = discord.Embed(
                title="**⏹️ Stopping Music...**",
                description=description,
                color=0x8A3215,
            )
            if song_info and (thumbnail := song_info['thumbnail']):
                embed.set_thumbnail(url=thumbnail)
            embed.set_footer(
                icon_url=user.display_avatar.url, 
                text=f"Stopped by: {user.display_name}"
            )
            
            if interaction:
                await ctx.response.send_message(embed=embed, ephemeral=False)
            else: 
                await ctx.reply(embed=embed, mention_author=False)
            # --------------------------------------------------
            
            # Stop playback and disconnect, but do not clear the queue
            if voice_channel_id in voice_client_dict and voice_client_dict[voice_channel_id].is_connected():
                await voice_client_dict[voice_channel_id].disconnect()
                del voice_client_dict[voice_channel_id]
        except Exception as e:
            print(f"Error in stop_music for {voice_channel.name}: {e}")
            await ctx.reply(f"Unable to stop playback in {voice_channel.name}.", mention_author=False)

    async def _prune_queue(self, ctx_or_interaction):
        """
        Modify the _prune_queue method to handle both Context and Interaction objects.
        """
        # Determine if the caller is a Context or an Interaction
        if isinstance(ctx_or_interaction, commands.Context):
            ctx = ctx_or_interaction
            interaction = None
        elif isinstance(ctx_or_interaction, discord.Interaction):
            interaction = ctx_or_interaction
            ctx = await self.bot.get_context(ctx_or_interaction.message)
        else:
            return

        voice_channel = ctx.author.voice.channel
        voice_channel_id = voice_channel.id
        try:
            if voice_channel_id in music_queue:
                # Clear the queue
                music_queue[voice_channel_id].clear()
                if interaction:
                    await interaction.response.send_message(f"The queue for {voice_channel.name} has been cleared.", ephemeral=True)
                else:
                    await ctx.reply(f"The queue for {voice_channel.name} has been cleared.", mention_author=False)
            else:
                if interaction:
                    await interaction.response.send_message(f"No queue exists for {voice_channel.name}.", ephemeral=True)
                else:
                    await ctx.reply(f"No queue exists for {voice_channel.name}.", mention_author=False)
        except Exception as e:
            print(f"Error in prune_queue for {voice_channel.name}: {e}")
            if interaction:
                await interaction.response.send_message(f"Unable to clear the queue for {voice_channel.name}.", ephemeral=True)
            else:
                await ctx.reply(f"Unable to clear the queue for {voice_channel.name}.", mention_author=False)

    async def play_next_in_queue(self, voice_channel, text_channel):
        voice_channel_id = voice_channel.id

        # Check if the queue is empty
        if voice_channel_id not in music_queue or len(music_queue[voice_channel_id]) == 0:
            # Start timeout timer for inactivity only if not already set
            if voice_channel_id not in timeout_timers:
                await self.start_timeout_timer(voice_channel)
                print(f"Queue is empty in {voice_channel.name}. Timeout timer started.")
            return  # Exit if queue is empty

        # Get the current song
        current_song = music_queue[voice_channel_id][0]

        try:
            # Use the direct audio URL
            source = current_song['url']

            # Play the current song
            player = discord.FFmpegOpusAudio(source, **ffmpeg_options)
            voice_client = voice_client_dict[voice_channel_id]

            # Get the main event loop
            loop = asyncio.get_running_loop()

            # Define the after callback
            def after_playing(error):
                """Triggered when the current song finishes."""
                if error:
                    print(f"Error during playback in {voice_channel.name}: {error}")
                else:
                    print(f"Finished playing: {current_song['title']}")

                # Schedule the coroutine on the main event loop
                asyncio.run_coroutine_threadsafe(
                    self.handle_next_song(voice_channel, text_channel),
                    loop
                )

            voice_client.play(player, after=after_playing)

            # Create and attach the MusicControlView
            music_cog = self  # Since we're inside MusicCog
            view = MusicControlView(voice_channel_id=voice_channel_id, music_cog=music_cog)

            # Send an embed message with the current song info and attach the view
            embed = discord.Embed(
                title=current_song["title"],
                url=current_song["webpage_url"],
                color=0x8A3215
            )
            embed.set_author(name="🎵 Now Playing")
            if thumbnail := current_song['thumbnail']:
                embed.set_thumbnail(url=thumbnail)

            embed.description = f"• `{self.format_duration(current_song['duration'])}`\n• <@{current_song['requested_by'].id}>"
            embed.set_footer(
                text=f"Queue Length: {len(music_queue[voice_channel_id])}"
            )
            await text_channel.send(embed=embed, view=view)

            print(f"Now playing in {voice_channel.name}: {current_song['title']}")

        except Exception as e:
            print(f"Error playing next song in {voice_channel.name}: {e}")

    async def handle_next_song(self, voice_channel, text_channel):
        """Handle the transition to the next song or start the timeout timer."""
        voice_channel_id = voice_channel.id

        # Remove the current song from the queue if it's still there
        if voice_channel_id in music_queue and len(music_queue[voice_channel_id]) > 0:
            music_queue[voice_channel_id].pop(0)

        # If the queue has more songs, play the next one
        if len(music_queue[voice_channel_id]) > 0:
            await self.play_next_in_queue(voice_channel, text_channel)
        else:
            # Start the timeout timer if the queue is empty
            print(f"Queue is empty in {voice_channel.name}. Starting timeout timer.")
            await self.start_timeout_timer(voice_channel)

    async def start_timeout_timer(self, voice_channel):
        voice_channel_id = voice_channel.id

        # Cancel any existing timer for this voice channel
        if voice_channel_id in timeout_timers:
            print(f"Timeout timer already running for {voice_channel.name}.")
            return  # Avoid redundant timers

        # Start a new timer
        async def timeout_task():
            await asyncio.sleep(600)  # Timeout period: 10 minutes
            if voice_channel_id in voice_client_dict and voice_client_dict[voice_channel_id] is not None:
                await voice_client_dict[voice_channel_id].disconnect()
                del voice_client_dict[voice_channel_id]
                print(f"Disconnected from {voice_channel.name} due to inactivity.")

        timeout_timers[voice_channel_id] = self.bot.loop.create_task(timeout_task())

    async def cancel_timeout_timer(self, voice_channel):
        voice_channel_id = voice_channel.id
        if voice_channel_id in timeout_timers:
            timeout_timers[voice_channel_id].cancel()
            del timeout_timers[voice_channel_id]
            print(f"Timeout canceled for {voice_channel.name} due to activity.")

    async def search_spotify(self, ctx, url: str):
        track_id = ''
        parts = url.split("/track/")
        if len(parts) > 1:
            track_part = parts[1]
            # handle possible query params, e.g. ?si=...
            track_id = track_part.split("?")[0]
        else:
            track_id = url # TODO: might fail (invalid link, give error or smth)
        
        # 2. Retrieve metadata from Spotify, convert to ytsearch query
        track_info = self.spotify.track(track_id)
        track_name = track_info['name']
        artists = ", ".join(artist['name'] for artist in track_info['artists'])
        query = f"{artists} - {track_name}"
        
        # 4. Search youtube normally (TAKES THE FIRST ENTRY! TODO: UPDATE)
        youtube_entries = await self.search_youtube(query)
        if not youtube_entries:
            return None  # no results on YouTube
        
        selected_entry = youtube_entries[0] # takes just the first entries
        return selected_entry
        
    async def search_youtube(self, query, max_results=5):
        try:
            if not self.YOUTUBE_API_KEY:
                print("YOUTUBE_API_KEY is not set.")
                # await ctx.send("Internal error: API key not set.")
                return []

            youtube = build('youtube', 'v3', developerKey=self.YOUTUBE_API_KEY)

            request = youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                type='video',
                videoEmbeddable='true',  # Filters out non-embeddable videos
            )
            response = request.execute()
            entries = []
            video_ids = []
            for item in response['items']:
                video_id = item['id']['videoId']
                video_ids.append(video_id)
                title = item['snippet']['title']
                thumbnail = item['snippet']['thumbnails']['high']['url']
                entries.append({
                    'title': title,
                    'id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'duration': None,  # TODO: Will update later
                    'thumbnail': thumbnail
                })
            # Get durations in a batch request
            video_request = youtube.videos().list(
                part='contentDetails',
                id=','.join(video_ids)
            )
            video_response = video_request.execute()
            durations = {}
            for item in video_response['items']:
                video_id = item['id']
                duration_iso = item['contentDetails']['duration']
                duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
                durations[video_id] = duration_seconds
            # Update entries with durations
            for entry in entries:
                entry['duration'] = durations.get(entry['id'], 0)
            return entries
        except HttpError as e:
            print(f"HTTP error occurred: {e}")
            # await ctx.send("Failed to fetch search results from YouTube.")
            return []
        except Exception as e:
            print(f"Error fetching search results: {e}")
            # await ctx.send("An unexpected error occurred while searching YouTube.")
            return []

    async def select_song(self, ctx, entries: list, url_or_query: str, loading_message:Message = None):
        # Generate the search results list
        search_result = [
            f"({idx+1}). **[{entry['title']}]({entry['url']})** • `{self.format_duration(entry['duration'])}`"
            for idx, entry in enumerate(entries)
        ]

        # Create and send the embed with search results
        embed = discord.Embed(color=0x8A3215)
        embed.add_field(
            name=f"**Search Results for '{url_or_query}':**",
            value='\n'.join(search_result),
            inline=False
        )
        embed.set_footer(
            text=f"Please select the desired song by typing a number between 1 and {len(entries)}."
        )
        
        if loading_message:
            await loading_message.edit(embed=embed)
        else:
            await ctx.reply(embed=embed, mention_author=False)

        # Wait for the user's response
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Wait for the user's response
            reply = await self.bot.wait_for('message', check=check, timeout=30)
            if not reply.content.isdigit():
                await ctx.reply("Invalid input. The command has been canceled.", mention_author=False)
                return None

            index = int(reply.content) - 1
            if 0 <= index < len(entries):
                selected_entry = entries[index]
            else:
                await ctx.reply("Invalid selection. The command has been canceled.", mention_author=False)
                return None
        except asyncio.TimeoutError:
            await ctx.reply("No selection made in time. The command has been canceled.", mention_author=False)
            return None
        
        return selected_entry

    async def extract_song_info(self, url):
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except DownloadError as e:
            error_message = str(e)
            if 'Sign in to confirm your age' in error_message:
                print("Age-restricted content detected.")
                raise ValueError("This video is age-restricted and cannot be played.")
            else:
                print(f"Error extracting song info: {e}")
                raise ValueError("An error occurred while extracting song information.")
        except Exception as e:
            print(f"Error extracting song info: {e}")
            raise ValueError("An error occurred while extracting song information.")

        if 'entries' in data:
            data = data['entries'][0]

        # Extract song information
        song_info = {
            'url': data['url'],
            'title': data.get('title', 'Unknown Title'),
            'duration': data.get('duration', 0),
            'thumbnail': data.get('thumbnail', None),
            'webpage_url': data.get('webpage_url'),
        }
        return song_info

    def format_duration(self, seconds: int) -> str:
        """Convert seconds to MM:SS format."""
        minutes, seconds = divmod(int(seconds), 60)
        return f"{minutes}:{seconds:02d}"