import asyncio
from random import choice, randint
from discord import Message
import discord
# from main import voice_client_dict, ytdl, ffmpeg_options
from apps.ffmpeg_setup import voice_client_dict, ytdl, ffmpeg_options

async def get_response(user_input: str, message: Message) -> str:
    lowered: str = user_input.lower()
    print(lowered)
    
    if lowered == '':
        return 'apaan'
    elif lowered.startswith('play'):
        result = await play_music(message)
        return f"Now Playing: {result}"
    
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
    try:
        voice_client = await message.author.voice.channel.connect()
        voice_client_dict[voice_client.guild.id] = voice_client
    except Exception as e:
        print(e)
        
    try:
        url = message.content.split()[1]
        loop = asyncio.get_event_loop()
        
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        
        song_url = data['url']
        song_title = data.get('title', 'Unknown Title')  # Safeguard against missing title
        
        player = discord.FFmpegPCMAudio(song_url, **ffmpeg_options)
        
        voice_client_dict[message.guild.id].play(player)

        return song_title
    except Exception as e:
        print(e)
        
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
        
async def stop_music(message: Message):
    try:
        voice_client_dict[message.guild.id].stop()
        await voice_client_dict[message.guild.id].disconnect()
    except Exception as e:
        print(e)