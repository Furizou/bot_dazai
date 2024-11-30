import asyncio
from random import choice, randint
import re
import time
import urllib.parse
import urllib.request
from discord import Message
import discord
import urllib
# from main import voice_client_dict, ytdl, ffmpeg_options
from apps.ffmpeg_setup import voice_client_dict, ytdl, ffmpeg_options, music_queue, timeout_timers

async def get_response(user_input: str, message: Message) -> str:
    lowered: str = user_input.lower()
    print(lowered)
    
    if lowered == '':
        return 'apaan'
    elif lowered.startswith('play'):
        result = await play_music(message)
        return result
    
    elif lowered.startswith('qplay'):
        result = await quickplay_music(message)
        return result
    
    elif lowered.startswith('skip'):
        result = await skip_music(message)
        return result
    
    elif lowered.startswith('queue'):
        result = await show_queue(message)
        return result
    
    elif lowered.startswith('prune'):
        result = await prune_queue(message)
        return result
    
    elif lowered.startswith('pause'):
        result = await pause_music(message)
        return f"Music paused..."
        
    elif lowered.startswith('resume'):
        result = await resume_music(message)
        return f"Music resumed..."
    
    elif lowered.startswith('stop'):
        result = await stop_music(message)
        return f"dadah"
        
    elif 'hello' in lowered:
        return 'HAI COK'
    elif 'judol' in lowered:
        return f'Selamat kamu dapat nomor: {randint(1,6)}'
    else:
        # return choice(['Ngomong apa sih nyet',
        #                'Sorry gapaham',
        #                'Mana kutau kau mau apa',])
        return choice(['Ngomong apa sih',
                'Sorry gapaham',
                'Mana kutau kau mau apa',])

    # raise NotImplementedError('Code is missing...')

async def quickplay_music(message: Message):
    voice_channel = message.author.voice.channel  # Get the user's voice channel
    voice_channel_id = voice_channel.id

    # Ensure the music queue is initialized for the voice channel
    if voice_channel_id not in music_queue:
        music_queue[voice_channel_id] = []

    try:
        # Connect to the voice channel if not already connected
        if voice_channel_id not in voice_client_dict or voice_client_dict[voice_channel_id] is None:
            voice_client = await voice_channel.connect()
            voice_client_dict[voice_channel_id] = voice_client

        url = message.content.split()[1]
        loop = asyncio.get_event_loop()

        # Use yt-dlp to extract song metadata
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if ("tiktok.com" in url) and (not data.get("url")):
            return "This TikTok video is not compatible for playback."

        # Handle playlists by taking the first entry
        if 'entries' in data:
            data = data['entries'][0]

        song_url = data['url']
        song_title = data.get('title', 'Unknown Title')
        song_duration = data.get('duration', 0)
        thumbnail = data.get('thumbnail', None)
        webpage_url = data.get('webpage_url')  # The original video URL

        # Prepare the quickplay song dictionary
        quickplay_song = {
            'title': song_title,
            'url': song_url,
            'webpage_url': webpage_url,
            'duration': song_duration,
            'thumbnail': thumbnail,
            'requested_by': message.author
        }

        # Insert the quickplay song after the current song in the queue
        music_queue[voice_channel_id].insert(1, quickplay_song)

        print(f"Quickplaying in {voice_channel.name}: {song_title}")

        # Send an embed message with the quickplay song info
        embed = discord.Embed(
            title=song_title,
            url=webpage_url,
            description=f"Queue Length: {len(music_queue[voice_channel_id])}",
            color=0x8A3215,
        )
        embed.set_author(name="Quickplaying 😎")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        await message.channel.send(embed=embed)

        # Cancel any existing timeout timer
        await cancel_timeout_timer(voice_channel)

        # Skip the current song (which will remove it from the queue)
        await skip_music(message)

        return f"Now Quickplaying: {song_title}"
    except Exception as e:
        print(f"Error in quickplay_music: {e}")
        return "Failed to quickplay the requested song."

async def play_music(message: Message):
    voice_channel = message.author.voice.channel  # Get the user's voice channel
    voice_channel_id = voice_channel.id
    
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='

    # Ensure the music queue is initialized for the voice channel
    if voice_channel_id not in music_queue:
        music_queue[voice_channel_id] = []

    try:
        # Connect to the voice channel if not already connected
        if voice_channel_id not in voice_client_dict or voice_client_dict[voice_channel_id] is None:
            voice_client = await voice_channel.connect()
            voice_client_dict[voice_channel_id] = voice_client

        url = message.content.split()[1]
        if youtube_base_url not in url:
            await message.channel.send('tessszz')
            # query_string = urllib.parse.urlencode({
            #     'search_query': ' '.join(message.content.split()[1:])
            # })
            
            # content = urllib.request.urlopen(
            #     youtube_results_url + query_string
            # )
            
            # search_queries = re.findall(r'/watch\?v=(.{11})', content.read().decode())
            # search_result = []
            
            entries = await search_youtube(' '.join(message.content.split()[1:]))

            if not entries:
                await message.channel.send("No results found.")
                return
            
            search_result = [
                f"({idx+1}). **[{entry['title']}]({entry['webpage_url']})** • `{format_duration(entry['duration'])}`"
                for idx, entry in enumerate(entries)
            ]

            await message.channel.send('disini')
            embed = discord.Embed(color=0x8A3215)
            
            embed.add_field(
                name=f"**📻 Music Query for {url}:**",
                value='\n'.join(search_result),
                inline=False
            )

            # Footer with queue length
            embed.set_footer(
                text=f"please select the desired music"
            )            
            await message.channel.send(embed=embed)
            # await message.channel.send('tesss')
            
            return    

        # Use yt-dlp to extract song metadata
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if ("tiktok.com" in url) and (not data.get("url")):
            return "This TikTok video is not compatible for playback."

        # Handle playlists by taking the first entry
        if 'entries' in data:
            data = data['entries'][0]

        song_url = data['url']
        song_title = data.get('title', 'Unknown Title')
        song_duration = data.get('duration', 0)
        thumbnail = data.get('thumbnail', None)
        webpage_url = data.get('webpage_url')  # The original video URL

        # Add to the queue for the voice channel
        music_queue[voice_channel_id].append({
            'title': song_title,
            'url': song_url,
            'webpage_url': webpage_url,
            'duration': song_duration,
            'thumbnail': thumbnail,
            'requested_by': message.author
        })
        print(f"Added to queue in {voice_channel.name}: {song_title}")
        
        # Send an embed message with the current song info
        embed = discord.Embed(
            title=song_title,
            url=song_url,  # Use webpage_url for the embed
            description=f"Queue Length: {len(music_queue[voice_channel_id])}",
            color=0x8A3215,
        )
        
        embed.set_author(name="Added to Queue 😍")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        await message.channel.send(embed=embed)

        # Cancel any existing timeout timer
        await cancel_timeout_timer(voice_channel)

        # If nothing is playing, start playing the next song in the queue
        if not voice_client_dict[voice_channel_id].is_playing():
            await play_next_in_queue(voice_channel, message.channel)

        return song_title
    except Exception as e:
        print(f"Error in play_music: {e}")
        return "Failed to play the requested song."

async def play_next_in_queue(voice_channel, text_channel):
    voice_channel_id = voice_channel.id

    # Check if the queue is empty
    if voice_channel_id not in music_queue or len(music_queue[voice_channel_id]) == 0:
        # Start timeout timer for inactivity only if not already set
        if voice_channel_id not in timeout_timers:
            await start_timeout_timer(voice_channel)
            print(f"Queue is empty in {voice_channel.name}. Timeout timer started.")
        return  # Exit if queue is empty

    # Get the current song
    current_song = music_queue[voice_channel_id][0]

    try:
        # Do not stop any existing playback here

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
                handle_next_song(voice_channel, text_channel),
                loop
            )

        voice_client.play(player, after=after_playing)

        # Send an embed message with the current song info
        embed = discord.Embed(
            title=current_song["title"],
            url=current_song["webpage_url"],  # Use webpage_url for the embed
            color=0x8A3215
        )
        embed.set_author(name="🎵 Now Playing")
        if thumbnail := current_song['thumbnail']:
            embed.set_thumbnail(url=thumbnail)
                
        embed.description = f"•`{format_duration(current_song['duration'])}`\n• <@{current_song['requested_by'].id}>"
        embed.set_footer(
            text=f"Song By: {current_song.get('uploader', 'Unknown')} • Today at {discord.utils.utcnow().strftime('%H:%M')}."
        )
        await text_channel.send(embed=embed)

        print(f"Now playing in {voice_channel.name}: {current_song['title']}")

    except Exception as e:
        print(f"Error playing next song in {voice_channel.name}: {e}")

async def handle_next_song(voice_channel, text_channel):
    """Handle the transition to the next song or start the timeout timer."""
    voice_channel_id = voice_channel.id

    # Remove the current song from the queue if it's still there
    if voice_channel_id in music_queue and len(music_queue[voice_channel_id]) > 0:
        music_queue[voice_channel_id].pop(0)

    # If the queue has more songs, play the next one
    if len(music_queue[voice_channel_id]) > 0:
        await play_next_in_queue(voice_channel, text_channel)
    else:
        # Start the timeout timer if the queue is empty
        print(f"Queue is empty in {voice_channel.name}. Starting timeout timer.")
        await start_timeout_timer(voice_channel)
        
async def pause_music(message: Message):
    try:
        voice_client_dict[message.guild.id].pause()
    except Exception as e:
        print(e)
        
async def resume_music(message: Message):
    try:
        voice_client_dict[message.guild.id].resume()
    except Exception as e:
        print(e)
        
async def skip_music(message: Message):
    voice_channel = message.author.voice.channel
    voice_channel_id = voice_channel.id
    try:
        # Stop current playback
        if voice_client_dict[voice_channel_id].is_playing():
            voice_client_dict[voice_channel_id].stop()

        # Do not remove the current song or call play_next_in_queue here
        # The after_playing callback will handle this

        return f"Skipped to the next song in {voice_channel.name}."
    except Exception as e:
        print(f"Error in skip_music for {voice_channel.name}: {e}")
        return "Unable to skip the song."

async def show_queue(message: Message):
    voice_channel = message.author.voice.channel
    voice_channel_id = voice_channel.id

    # Check if the queue is empty
    if voice_channel_id not in music_queue or len(music_queue[voice_channel_id]) == 0:
        embed = discord.Embed(
            description=f"The queue is empty in {voice_channel.name}.",
            color=0x8A3215
        )
        await message.channel.send(embed=embed)
        return

    # Get the current song
    current_song = music_queue[voice_channel_id][0]
    queue_length = len(music_queue[voice_channel_id])

    # Generate queue list using 'webpage_url' for hyperlinks
    queue_lines = [
        f"({idx+1}). **[{song['title']}]({song['webpage_url']})** • `{format_duration(song['duration'])}` • <@{song['requested_by'].id}>"
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
        name=f"Music Queue for {message.guild.name}",
        icon_url=message.guild.icon.url if message.guild.icon else None
    )
    embed.add_field(
        name="**Now Playing:**",
        value=f"**[{current_song['title']}]({current_song['webpage_url']})** • `{format_duration(current_song['duration'])}` • <@{current_song['requested_by'].id}>",
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

    await message.channel.send(embed=embed)

        
async def stop_music(message: Message):
    voice_channel = message.author.voice.channel
    voice_channel_id = voice_channel.id
    try:
        # Stop playback and disconnect, but do not clear the queue
        if voice_channel_id in voice_client_dict and voice_client_dict[voice_channel_id].is_playing():
            voice_client_dict[voice_channel_id].stop()
        await voice_client_dict[voice_channel_id].disconnect()
        del voice_client_dict[voice_channel_id]
        return f"Playback stopped and disconnected from {voice_channel.name}."
    except Exception as e:
        print(f"Error in stop_music for {voice_channel.name}: {e}")
        return f"Unable to stop playback in {voice_channel.name}."

async def prune_queue(message: Message):
    voice_channel = message.author.voice.channel
    voice_channel_id = voice_channel.id
    try:
        if voice_channel_id in music_queue:
            # Clear the queue
            music_queue[voice_channel_id].clear()
            return f"The queue for {voice_channel.name} has been cleared."
        return f"No queue exists for {voice_channel.name}."
    except Exception as e:
        print(f"Error in prune_queue for {voice_channel.name}: {e}")
        return f"Unable to clear the queue for {voice_channel.name}."

async def start_timeout_timer(voice_channel):
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

    timeout_timers[voice_channel_id] = asyncio.create_task(timeout_task())
    
async def cancel_timeout_timer(voice_channel):
    voice_channel_id = voice_channel.id
    if voice_channel_id in timeout_timers:
        timeout_timers[voice_channel_id].cancel()
        del timeout_timers[voice_channel_id]
        print(f"Timeout canceled for {voice_channel.name} due to activity.")
        
def format_duration(seconds: int) -> str:
    """Convert seconds to MM:SS format."""
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}"


async def search_youtube(query, max_results=5):
    loop = asyncio.get_event_loop()
    try:
        search_url = f"ytsearch{max_results}:{query}"
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_url, download=False))
        return data['entries']
    except Exception as e:
        print(f"Error fetching search results: {e}")
        return []

# async def get_video_info(video_id):
#     """Asynchronously fetch video information using yt_dlp."""
#     video_url = f"https://www.youtube.com/watch?v={video_id}"
#     loop = asyncio.get_event_loop()
#     try:
#         data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))
#         title = data.get('title', 'Unknown Title')
#         webpage_url = data.get('webpage_url', video_url)
#         duration = data.get('duration', 0)
#         return {
#             'title': title,
#             'webpage_url': webpage_url,
#             'duration': duration
#         }
#     except Exception as e:
#         print(f"Error fetching info for video ID {video_id}: {e}")
#         return None