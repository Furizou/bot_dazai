import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help', help="Displays all commands categorized by cogs.")
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="**🔧 Bot Commands 🔧**",
            description="Available commands categorized by functionality:",
            color=discord.Color.blurple()
        )

        # TODO: Make the format better
        
        # Iterate over each cog and its commands
        for cog_name, cog in self.bot.cogs.items():
            commands_list = cog.get_commands()
            command_descriptions = ""
            for command in commands_list:
                # Skip hidden commands
                if command.hidden:
                    continue
                # Append command name and its help text
                command_help = command.help or "No description provided."
                command_descriptions += f"`{command.name}`: {command_help}\n"
            
            # Only add a field for cogs that have at least one visible command
            if command_descriptions:
                embed.add_field(name=cog_name, value=command_descriptions, inline=False)
        
        prefix = self.bot.prefixes_dict.get(str(ctx.guild.id), '>')
        embed.set_footer(
            icon_url=ctx.guild.icon.url,
            text=f"Current server\'s prefix is {prefix}"
        )
        await ctx.send(embed=embed)