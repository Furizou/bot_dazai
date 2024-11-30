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

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Gives access to the bot instance
        
        
        # Load the YouTube API key here
        self.YOUTUBE_API_KEY: Final[str] = os.getenv('YOUTUBE_API_KEY')
        # print(f"YOUTUBE_API_KEY: {self.YOUTUBE_API_KEY}")  # Temporary for debugging

        if not self.YOUTUBE_API_KEY:
            print("YOUTUBE_API_KEY is not set. Please set the environment variable.")
            # Alternatively, you can raise an exception
            raise ValueError("YOUTUBE_API_KEY environment variable not set.")

    # ---------------------- Commands ----------------------

    @commands.command(name='play')
    async def play_music(self, ctx, *, url_or_query: str):
        await self._play_music(ctx, url_or_query)

    @commands.command(name='qplay')
    async def quickplay_music(self, ctx, *, url_or_query: str):
        await self._quickplay_music(ctx, url_or_query)

    @commands.command(name='skip')
    async def skip_music(self, ctx):
        await self._skip_music(ctx)

    @commands.command(name='queue')
    async def show_queue(self, ctx):
        await self._show_queue(ctx)

    @commands.command(name='prune')
    async def prune_queue(self, ctx):
        await self._prune_queue(ctx)

    @commands.command(name='pause')
    async def pause_music(self, ctx):
        await self._pause_music(ctx)

    @commands.command(name='resume')
    async def resume_music(self, ctx):
        await self._resume_music(ctx)

    @commands.command(name='stop')
    async def stop_music(self, ctx):
        await self._stop_music(ctx)

    # ---------------------- Helper Methods ----------------------

    async def _play_music(self, ctx, url_or_query: str):
        voice_channel = ctx.author.voice.channel
        voice_channel_id = voice_channel.id

        # Ensure the music queue is initialized for the voice channel
        if voice_channel_id not in music_queue:
            music_queue[voice_channel_id] = []

        try:
            # Connect to the voice channel if not already connected
            if (voice_channel_id not in voice_client_dict) or (not voice_client_dict[voice_channel_id].is_connected()):
                try:
                    voice_client = await voice_channel.connect()
                    voice_client_dict[voice_channel_id] = voice_client
                except discord.ClientException as e:
                    # Already connected to a voice channel
                    voice_client = voice_client_dict[voice_channel_id]
                except Exception as e:
                    print(f"Error connecting to voice channel: {e}")
                    await ctx.reply("Failed to connect to the voice channel.", mention_author=False)
                    return
            else:
                voice_client = voice_client_dict[voice_channel_id]

            # Check if it's a URL or search query
            if not url_or_query.startswith('http'):
                # It's a search query
                entries = await self.search_youtube(url_or_query)

                if not entries:
                    await ctx.reply("No results found.", mention_author=False)
                    return
                
                selected_entry = await self.select_song(ctx=ctx, entries=entries, url_or_query=url_or_query)
            else:
                # It's a direct URL
                selected_entry = {'url': url_or_query}

            # -------------------- adding to queue loading ----------------------
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
                return
            # song_info = await self.extract_song_info(selected_url)
            song_info['requested_by'] = ctx.author
            
            # Add to the queue for the voice channel
            music_queue[voice_channel_id].append(song_info)
            print(f"Added to queue in {voice_channel.name}: {song_info['title']}")
    
            # Send an embed message with the song info
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
            
            # Cancel any existing timeout timer
            await self.cancel_timeout_timer(voice_channel)

            # If nothing is playing, start playing the next song in the queue
            if not voice_client_dict[voice_channel_id].is_playing():
                await self.play_next_in_queue(voice_channel, ctx.channel)

        except Exception as e:
            print(f"Error in play_music: {e}")
            await ctx.reply("Failed to play the requested song.", mention_author=False)

    async def _quickplay_music(self, ctx, url_or_query: str):
        voice_channel = ctx.author.voice.channel
        voice_channel_id = voice_channel.id

        # Ensure the music queue is initialized for the voice channel
        if voice_channel_id not in music_queue:
            music_queue[voice_channel_id] = []

        try:
            # Connect to the voice channel if not already connected
            if voice_channel_id not in voice_client_dict or not voice_client_dict[voice_channel_id].is_connected():
                voice_client = await voice_channel.connect()
                voice_client_dict[voice_channel_id] = voice_client
            else:
                voice_client = voice_client_dict[voice_channel_id]

            # Check if it's a URL or search query
            if not url_or_query.startswith('http'):
                # It's a search query
                entries = await self.search_youtube(url_or_query)

                if not entries:
                    await ctx.reply("No results found.", mention_author=False)
                    return
                
                selected_entry = await self.select_song(ctx=ctx, entries=entries, url_or_query=url_or_query)
            else:
                # It's a direct URL
                selected_entry = {'url': url_or_query}

            # -------------------- adding to queue loading ----------------------
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
                return
            # song_info = await self.extract_song_info(selected_url)
            song_info['requested_by'] = ctx.author

            # Insert the quickplay song after the current song in the queue
            music_queue[voice_channel_id].insert(1, song_info)

            print(f"Quickplaying in {voice_channel.name}: {song_info['title']}")

            # Send an embed message with the quickplay song info
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

            # Cancel any existing timeout timer
            await self.cancel_timeout_timer(voice_channel)

            # Skip the current song (which will remove it from the queue)
            await self._skip_music(ctx)

        except Exception as e:
            print(f"Error in quickplay_music: {e}")
            await ctx.reply("Failed to quickplay the requested song.", mention_author=False)

    async def _skip_music(self, ctx):
        voice_channel = ctx.author.voice.channel
        voice_channel_id = voice_channel.id
        try:
            # Stop current playback
            if voice_channel_id in voice_client_dict and voice_client_dict[voice_channel_id].is_playing():
                voice_client_dict[voice_channel_id].stop()

            # Do not remove the current song or call play_next_in_queue here
            # The after_playing callback will handle this

            await ctx.reply(f"Skipped to the next song in {voice_channel.name}.", mention_author=False)

        except Exception as e:
            print(f"Error in skip_music for {voice_channel.name}: {e}")
            await ctx.reply("Unable to skip the song.", mention_author=False)

    async def _show_queue(self, ctx):
        voice_channel = ctx.author.voice.channel
        voice_channel_id = voice_channel.id

        # Check if the queue is empty
        if voice_channel_id not in music_queue or len(music_queue[voice_channel_id]) == 0:
            embed = discord.Embed(
                description=f"The queue is empty in {voice_channel.name}.",
                color=0x8A3215
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        # Get the current song
        current_song = music_queue[voice_channel_id][0]
        queue_length = len(music_queue[voice_channel_id])

        # Generate queue list using 'webpage_url' for hyperlinks
        queue_lines = [
            f"({idx+1}). **[{song['title']}]({song['webpage_url']})** • `{self.format_duration(song['duration'])}` • <@{song['requested_by'].id}>"
            for idx, song in enumerate(music_queue[voice_channel_id][1:])
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

        await ctx.reply(embed=embed, mention_author=False)

    async def _pause_music(self, ctx):
        voice_channel_id = ctx.author.voice.channel.id
        try:
            voice_client_dict[voice_channel_id].pause()
            await ctx.reply("Music paused.", mention_author=False)
        except Exception as e:
            print(f"Error in pause_music: {e}")
            await ctx.reply("Unable to pause the music.", mention_author=False)

    async def _resume_music(self, ctx):
        voice_channel_id = ctx.author.voice.channel.id
        try:
            voice_client_dict[voice_channel_id].resume()
            await ctx.reply("Music resumed.", mention_author=False)
        except Exception as e:
            print(f"Error in resume_music: {e}")
            await ctx.reply("Unable to resume the music.", mention_author=False)

    async def _stop_music(self, ctx):
        voice_channel = ctx.author.voice.channel
        voice_channel_id = voice_channel.id
        try:
            # Stop playback and disconnect, but do not clear the queue
            if voice_channel_id in voice_client_dict and voice_client_dict[voice_channel_id].is_connected():
                await voice_client_dict[voice_channel_id].disconnect()
                del voice_client_dict[voice_channel_id]
            await ctx.reply(f"Playback stopped and disconnected from {voice_channel.name}.", mention_author=False)
        except Exception as e:
            print(f"Error in stop_music for {voice_channel.name}: {e}")
            await ctx.reply(f"Unable to stop playback in {voice_channel.name}.", mention_author=False)

    async def _prune_queue(self, ctx):
        voice_channel = ctx.author.voice.channel
        voice_channel_id = voice_channel.id
        try:
            if voice_channel_id in music_queue:
                # Clear the queue
                music_queue[voice_channel_id].clear()
                await ctx.reply(f"The queue for {voice_channel.name} has been cleared.", mention_author=False)
            else:
                await ctx.reply(f"No queue exists for {voice_channel.name}.", mention_author=False)
        except Exception as e:
            print(f"Error in prune_queue for {voice_channel.name}: {e}")
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

            # Send an embed message with the current song info
            embed = discord.Embed(
                title=current_song["title"],
                url=current_song["webpage_url"],
                color=0x8A3215
            )
            embed.set_author(name="🎵 Now Playing")
            if thumbnail := current_song['thumbnail']:
                embed.set_thumbnail(url=thumbnail)

            embed.description = f"•`{self.format_duration(current_song['duration'])}`\n• <@{current_song['requested_by'].id}>"
            embed.set_footer(
                text=f"Queue Length: {len(music_queue[voice_channel_id])}"
            )
            await text_channel.send(embed=embed)

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
                    'duration': None,  # Will update later
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
    
    async def select_song(self, ctx, entries: list, url_or_query):
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
        await ctx.reply(embed=embed, mention_author=False)

        # Wait for the user's response
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Wait for the user's response
            reply = await self.bot.wait_for('message', check=check, timeout=30)
            if not reply.content.isdigit():
                await ctx.reply("Invalid input. The command has been canceled.", mention_author=False)
                return

            index = int(reply.content) - 1
            if 0 <= index < len(entries):
                selected_entry = entries[index]
            else:
                await ctx.reply("Invalid selection. The command has been canceled.", mention_author=False)
                return
        except asyncio.TimeoutError:
            await ctx.reply("No selection made in time. The command has been canceled.", mention_author=False)
            return
        
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