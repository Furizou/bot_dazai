# cogs/general_cog.py
import random
from discord.ext import commands

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Command to say hello
    @commands.command(name='hello')
    async def say_hello(self, ctx):
        await ctx.send('Hello there!')

    # Command to play 'judol' game
    @commands.command(name='judol')
    async def judol(self, ctx):
        number = random.randint(1, 6)
        await ctx.send(f'Congratulations! You got the number: {number}')

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
