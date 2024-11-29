from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message
from responses import get_response
from apps.ffmpeg_setup import voice_client_dict, ytdl, yt_dl_options, ffmpeg_options
import yt_dlp

# STEP 0: load env
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

# STEP 1: bot setup
intents: Intents = Intents.default()
intents.message_content = True #NOQA
client: Client = Client(intents=intents)

# MUSICS
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

# STEP 2: msg functionality
async def send_message(message: Message, user_message: str) -> None:
    if not user_message:
        print('(Message was empty because intents was not enabled probably)')
        return
    
    if is_private := user_message[0] == '?':
        user_message = user_message[1:]
        
    try:
        response: str = await get_response(user_message, message)
        
        if not response:
            response = "Sorry, I couldn't process that request."
        
        if is_private:
            await message.author.send(response)
        else:
            await message.channel.send(response)
        # await message.author.send(response) if is_private else await message.channel.send(response)
        
    except Exception as e:
        print(e)
        
# STEP 3: handling startup
@client.event
async def on_ready() -> None:
    print(f'{client.user} is now running!')
    
# STEP 4: Handling incoming
@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return
    
    # Check if the message is empty
    if not message.content:
        return
    
    if message.content[0] != '>':
        return
    
    username: str = str(message.author)
    user_message: str = message.content[1:]
    channel: str = str(message.channel)
    
    print(f'[{channel}] {username}: "{user_message}"')
    await send_message(message, user_message)
    
# STEP 5: main entry point
def main() -> None:
    client.run(token=TOKEN)
    

if __name__ == '__main__':
    main()