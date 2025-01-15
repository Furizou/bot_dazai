from discord.ext import commands
from utils.prefix_utils import save_prefixes

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='setprefix', help="Change the command prefix. (Admin only)")
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, new_prefix: str):
        guild_id_str = str(ctx.guild.id)
        old_prefix = self.bot.prefixes_dict.get(guild_id_str, '>')

        # Update in-memory dictionary
        self.bot.prefixes_dict[guild_id_str] = new_prefix

        # Save to JSON
        save_prefixes(self.bot.prefixes_dict)

        await ctx.reply(f"Prefix changed from `{old_prefix}` to `{new_prefix}` for this server.", mention_author=False)