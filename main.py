# main.py
from typing import Final
import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord import Intents
from cogs.music_cog import MusicCog  # Import the MusicCog
from cogs.general_cog import GeneralCog  # Import the GeneralCog
from apps.ffmpeg_setup import yt_dl_options
import asyncio

# Load environment variables
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

# Bot setup
intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents)

# Remove default help command if you plan to add a custom one
bot.remove_command('help')

# Handling startup
@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')

async def main():
    # Load Opus library
    # if not discord.opus.is_loaded():
    #     discord.opus.load_opus('opus')
        
    async with bot:
        # Load the cogs
        try:
            await bot.add_cog(MusicCog(bot))
            print("MusicCog added successfully.")
        except Exception as e:
            print(f"Failed to load MusicCog: {e}")

        try:
            await bot.add_cog(GeneralCog(bot))
            print("GeneralCog added successfully.")
        except Exception as e:
            print(f"Failed to load GeneralCog: {e}")

        await bot.start(TOKEN)


if __name__ == '__main__':
    # Run the main function
    asyncio.run(main())