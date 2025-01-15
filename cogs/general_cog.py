# cogs/general_cog.py
import random
from discord.ext import commands

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='hello', help="Bot greets you with a friendly message.")
    async def say_hello(self, ctx):
        await ctx.send('Hello there!')

    @commands.command(name='judol', help="Play the 'judol' game")
    async def judol(self, ctx):
        number = random.randint(1, 6)
        await ctx.send(f'Congratulations! You got the number: {number}')
        
    @commands.command(name='prefix', help="Display the current server's command prefix.")
    async def prefix(self, ctx):
        prefix = self.bot.prefixes_dict.get(str(ctx.guild.id), '>')
        await ctx.reply(f'Current server\'s prefix is `{prefix}`', mention_author=False)

    # Listener for on_message events
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages sent by the bot
        if message.author == self.bot.user:
            return

        # Check if the message is a direct mention to the bot
        if self.bot.user in message.mentions:
            lowered = message.content.lower()

            if 'hello' in lowered:
                await message.channel.send('Hello there!')
            elif 'judol' in lowered:
                number = random.randint(1, 6)
                await message.channel.send(f'Congratulations! You got the number: {number}')
            else:
                # Default response when bot is mentioned but doesn't understand
                responses = [
                    'I didn\'t quite understand that.',
                    'Could you please clarify?',
                    'I\'m not sure what you mean.'
                ]
                await message.channel.send(random.choice(responses))

        # Do not call await self.bot.process_commands(message) here
