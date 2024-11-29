import asyncio
from random import choice, randint
from discord import Message
import discord
# from main import voice_client_dict, ytdl, ffmpeg_options
from apps.ffmpeg_setup import voice_client_dict, ytdl, ffmpeg_options, music_queue, timeout_timers

async def get_response(user_input: str, message: Message) -> str:
    lowered: str = user_input.lower()
    print(lowered)
    
    if lowered == '':
        return 'apaan'
    elif lowered.startswith('play'):
        result = await play_music(message)
        return f"Now Playing: {result}"
    
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
        return f"dadah tod"
        
    elif 'hello' in lowered:
        return 'HAI COK'
    elif 'judol' in lowered:
        return f'Selamat kamu dapat nomor: {randint(1,6)}'
    else:
        return choice(['Ngomong apa sih nyet',
                       'Sorry gapaham',
                       'Mana kutau kau mau apa',])

    # raise NotImplementedError('Code is missing...')
    
async def play_music(message: Message):
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
        
        song_url = data['url']
        song_title = data.get('title', 'Unknown Title')  # Safeguard against missing title
        
        # Add to the queue for the voice channel
        music_queue[voice_channel_id].append({'title': song_title, 'url': song_url})
        print(f"Added to queue in {voice_channel.name}: {song_title}")
        
        # Cancel any existing timeout timer
        await cancel_timeout_timer(voice_channel)
        
        # If nothing is playing, start playing the next song in the queue
        if not voice_client_dict[voice_channel_id].is_playing():
            await play_next_in_queue(voice_channel)

        return song_title
    except Exception as e:
        print(f"Error in play_music: {e}")
        return "Failed to play the requested song."
        
async def play_next_in_queue(voice_channel):
    voice_channel_id = voice_channel.id

    # Check if the queue is empty
    if voice_channel_id not in music_queue or len(music_queue[voice_channel_id]) == 0:
        # Start timeout timer for inactivity only if not already set
        if voice_channel_id not in timeout_timers:
            await start_timeout_timer(voice_channel)
            print(f"Queue is empty in {voice_channel.name}. Timeout timer started.")
        return  # Exit if queue is empty

    # Get the current song (without popping it)
    current_song = music_queue[voice_channel_id][0]

    try:
        # Stop any existing playback (ensure ffmpeg cleanup)
        if voice_client_dict[voice_channel_id].is_playing():
            voice_client_dict[voice_channel_id].stop()

        # Play the current song
        player = discord.FFmpegPCMAudio(current_song['url'], **ffmpeg_options)

        # Use the main event loop for the after callback
        loop = asyncio.get_event_loop()

        def after_playing(error):
            if error:
                print(f"Error during playback in {voice_channel.name}: {error}")

            # Remove the current song from the queue after it finishes
            if voice_channel_id in music_queue and len(music_queue[voice_channel_id]) > 0:
                music_queue[voice_channel_id].pop(0)

            # Trigger the next song
            asyncio.run_coroutine_threadsafe(play_next_in_queue(voice_channel), loop)

        voice_client_dict[voice_channel_id].play(player, after=after_playing)
        print(f"Now playing in {voice_channel.name}: {current_song['title']}")
    except Exception as e:
        print(f"Error playing next song in {voice_channel.name}: {e}")
        
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

        # Remove the currently playing song from the queue
        if voice_channel_id in music_queue and len(music_queue[voice_channel_id]) > 0:
            music_queue[voice_channel_id].pop(0)

        # Trigger the next song if the queue is not empty
        if len(music_queue[voice_channel_id]) > 0:
            await play_next_in_queue(voice_channel)
        else:
            print(f"Queue is now empty in {voice_channel.name}")
            if voice_channel_id not in timeout_timers:
                await start_timeout_timer(voice_channel)

        return f"Skipped to the next song in {voice_channel.name}."
    except Exception as e:
        print(f"Error in skip_music for {voice_channel.name}: {e}")
        return "Unable to skip the song."

async def show_queue(message: Message):
    voice_channel = message.author.voice.channel
    voice_channel_id = voice_channel.id

    if voice_channel_id not in music_queue or len(music_queue[voice_channel_id]) == 0:
        return f"The queue is empty in {voice_channel.name}."
    
    # Display the current song and the rest of the queue
    queue_list = "\n".join(
        [f"{idx+1}. {song['title']}" for idx, song in enumerate(music_queue[voice_channel_id])]
    )
    return f"Current queue in {voice_channel.name}:\n{queue_list}\n\nCurrently playing: {music_queue[voice_channel_id][0]['title']}"
        
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
        timeout_timers[voice_channel_id].cancel()

    # Start a new timer
    async def timeout_task():
        await asyncio.sleep(600)  # Timeout period: 10 minutes
        # Leave the channel if still connected and idle
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