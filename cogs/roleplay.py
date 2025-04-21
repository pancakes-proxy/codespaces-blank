import discord
from discord.ext import commands
from discord import app_commands
from enum import Enum
import random

class CustomCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    cog = CustomCommandsCog(bot)
    bot.tree.add_command(coinflip)
    bot.tree.add_command(wave)
    bot.tree.add_command(swisschesse)
    bot.tree.add_command(diddle)
    bot.tree.add_command(publicexecution)
    bot.tree.add_command(deport)
    bot.tree.add_command(snatch)
    bot.tree.add_command(caughtlacking)
    bot.tree.add_command(slap)
    bot.tree.add_command(triplebaka)
    bot.tree.add_command(spotify)
    bot.tree.add_command(hug)
    bot.tree.add_command(kiss)
    bot.tree.add_command(punch)
    bot.tree.add_command(kick)
    bot.tree.add_command(banhammer)
    bot.tree.add_command(rps)
    bot.tree.add_command(marry)
    bot.tree.add_command(divorce)
    bot.tree.add_command(slay)
    await bot.add_cog(cog)
    await bot.tree.sync()
    
    def __init__(self, bot):
        self.bot = bot
class CoinSide(Enum):
    HEADS = "heads"
    TAILS = "tails"

@app_commands.command(name="coinflip", description="Flip a coin by picking heads or tails.")
async def coinflip(interaction: discord.Interaction, side: CoinSide):
    number = random.randint(1, 100)
    result = "heads" if number % 2 == 0 else "tails"
    win = (result == side.value)
    await interaction.response.send_message(
        f"Rolled number: {number}.\nThe coin landed on **{result}**.\nYou {'won' if win else 'lost'}!"
    )

@app_commands.command(name="wave", description="Wave at a user.")
async def wave(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"{interaction.user.mention} waved at {member.mention}")

@app_commands.command(name="swisschesse", description="A demonstration command.")
async def swisschesse(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(
        f"{interaction.user.mention} has sent {member.mention} to King Von with that glock 19 and 30 round clip"
    )

@app_commands.command(name="diddle", description="Diddle command.")
async def diddle(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} diddled {member.mention} at diddys freak off"
        )

@app_commands.command(name="publicexecution", description="Executes a public execution.")
async def publicexecution(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} has accused {member.mention} of being a witch and has sentenced them to a public hanging. "
            f"{member.mention} is now hanging from the gallows, their lifeless body swaying in the wind. "
            "The townsfolk cheer as they become a ghost haunting the village forever."
        )

@app_commands.command(name="deport", description="Deport a user.")
async def deport(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"At 6:07 AM EST, {interaction.user.mention} called ICE on {member.mention} "
            "and they were tossed into a white van by ICE and deported to the nearest border."
        )

@app_commands.command(name="snatch", description="Playfully snatches a user.")
async def snatch(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} snuck up on {member.mention}, grabbed their ankles, and tossed them into a white van. [Link](https://tenor.com/8lX5.gif)"
        )

@app_commands.command(name="caughtlacking", description="Catches someone lacking.")
async def caughtlacking(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} and his crew caught {member.mention} lacking and sprayed them with the glock 19, reminiscent of Pop Smoke."
        )

@app_commands.command(name="slap", description="Slap a user.")
async def slap(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} slapped {member.mention} [Reaction](https://tenor.com/bTGGQ.gif)"
        )

@app_commands.command(name="triplebaka", description="Sends a Triple Baka video link.")
async def triplebaka(interaction: discord.Interaction):
        await interaction.response.send_message(
            f"{interaction.user.mention} https://www.youtube.com/watch?v=HYKLZOo3DM4"
        )

@app_commands.command(name="spotify", description="Send a Spotify playlist link.")
async def spotify(interaction: discord.Interaction):
        await interaction.response.send_message("https://open.spotify.com/playlist/6BcRgFzoIAfLX7QZKEl8Gy?si=2c5c81b9c42d492f")

@app_commands.command(name="hug", description="Hug a user.")
async def hug(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} hugged {member.mention} [:3](https://tenor.com/hvKioj0rdk7.gif)"
        )

@app_commands.command(name="kiss", description="Kiss a user.")
async def kiss(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} kissed {member.mention} [:3](https://tenor.com/YkoQ.gif)"
        )

@app_commands.command(name="punch", description="Punch a user.")
async def punch(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} punched {member.mention} [:3](https://tenor.com/cM5NrlugNQL.gif)"
        )

@app_commands.command(name="kick", description="Kick a user.")
async def kick(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} kicked {member.mention} [:3](https://tenor.com/9q2k.gif)"
        )

@app_commands.command(name="banhammer", description="Use the banhammer on a user.")
async def banhammer(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} used the banhammer on {member.mention} [:3](https://tenor.com/bcWNT.gif)"
        )

@app_commands.command(name="rps", description="Play Rock, Paper, Scissors with the bot!")
async def rps(interaction: discord.Interaction, choice: str):
        options = ["rock", "paper", "scissors"]
        if choice.lower() not in options:
            await interaction.response.send_message("Invalid choice! Please choose rock, paper, or scissors.", ephemeral=True)
            return
        bot_choice = random.choice(options)
        if choice.lower() == bot_choice:
            result = "It's a tie!"
        elif (choice.lower() == "rock" and bot_choice == "scissors") or \
             (choice.lower() == "paper" and bot_choice == "rock") or \
             (choice.lower() == "scissors" and bot_choice == "paper"):
            result = "You win!"
        else:
            result = "You lose!"
        await interaction.response.send_message(
            f"You chose **{choice.lower()}**. I chose **{bot_choice}**. {result}"
        )

@app_commands.command(name="marry", description="Propose to a user.")
async def marry(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} proposed to {member.mention} [:3](https://tenor.com/s7SQl7AQGte.gif)"
        )

@app_commands.command(name="divorce", description="Divorce a user.")
async def divorce(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} divorced {member.mention} [:3](https://tenor.com/n5Q7Zeucrnq.gif)"
        )

@app_commands.command(name="slay", description="Slay a user.")
async def slay(interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} slayed {member.mention} mortal combat style")

async def setup(bot):
    await bot.add_cog(CustomCommandsCog(bot))
