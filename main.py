# main.py
import json
from typing import Final
import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord import Intents
from cogs.admin_cog import AdminCog
from cogs.help_cog import HelpCog
from cogs.music_cog import MusicCog  # Import the MusicCog
from cogs.general_cog import GeneralCog  # Import the GeneralCog
from apps.ffmpeg_setup import yt_dl_options
import asyncio

from utils.prefix_utils import load_prefixes

# Load environment variables
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

# Bot setup
intents = Intents.default()
intents.message_content = True

def get_prefix(bot, message):
    # default to '>' if there's no prefix
    if not message.guild:
        return '>'
    guild_id_str = str(message.guild.id)
    return bot.prefixes_dict.get(guild_id_str, '>')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=get_prefix, intents=intents)

# Remove default help command, import prefixes
bot.remove_command('help')
bot.prefixes_dict = load_prefixes()  # e.g. { "guild_id_str": "prefix", ... }

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
            
        try:
            await bot.add_cog(AdminCog(bot))
            print("AdminCog added successfully.")
        except Exception as e:
            print(f"Failed to load AdminCog: {e}")
            
        try:
            await bot.add_cog(HelpCog(bot))
            print("HelpCog added successfully.")
        except Exception as e:
            print(f"Failed to load HelpCog: {e}")

        await bot.start(TOKEN)


if __name__ == '__main__':
    # Run the main function
    asyncio.run(main())