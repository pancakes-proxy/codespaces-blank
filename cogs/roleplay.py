import discord
from discord.ext import commands
from discord import app_commands
from enum import Enum
import random

class CustomCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class CoinSide(Enum):
        HEADS = "heads"
        TAILS = "tails"

    @app_commands.command(name="coinflip", description="Flip a coin by picking heads or tails.")
    async def coinflip(self, interaction: discord.Interaction, side: CoinSide):
        number = random.randint(1, 100)
        result = "heads" if number % 2 == 0 else "tails"
        win = (result == side.value)
        await interaction.response.send_message(
            f"The coin landed on **{result}**.\nYou {'won' if win else 'lost'}!"
        )

    @app_commands.command(name="wave", description="Wave at a user.")
    async def wave(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{interaction.user.mention} waved at {member.mention}")

    @app_commands.command(name="swisschesse", description="A demonstration command.")
    async def swisschesse(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} has sent {member.mention} to King Von with that glock 19 and 30 round clip"
        )

    @app_commands.command(name="diddle", description="Diddle command.")
    async def diddle(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} diddled {member.mention} at diddys freak off"
        )

    @app_commands.command(name="publicexecution", description="Executes a public execution.")
    async def publicexecution(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} has accused {member.mention} of being a witch and has sentenced them to a public hanging. "
            f"{member.mention} is now hanging from the gallows, their lifeless body swaying in the wind. "
            "The townsfolk cheer as they become a ghost haunting the village forever."
        )

    @app_commands.command(name="deport", description="Deport a user.")
    async def deport(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"At 6:07 AM EST, {interaction.user.mention} called ICE on {member.mention} "
            "and they were tossed into a white van by ICE and deported to the nearest border."
        )

    @app_commands.command(name="snatch", description="Playfully snatches a user.")
    async def snatch(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} snuck up on {member.mention}, grabbed their ankles, and tossed them into a white van. [Link](https://tenor.com/8lX5.gif)"
        )

    @app_commands.command(name="caughtlacking", description="Catches someone lacking.")
    async def caughtlacking(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} and his crew caught {member.mention} lacking and sprayed them with the glock 19, reminiscent of Pop Smoke."
        )

    @app_commands.command(name="slap", description="Slap a user.")
    async def slap(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} slapped {member.mention} [Reaction](https://tenor.com/bTGGQ.gif)"
        )

    @app_commands.command(name="triplebaka", description="Sends a Triple Baka video link.")
    async def triplebaka(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"{interaction.user.mention} https://www.youtube.com/watch?v=HYKLZOo3DM4"
        )

    @app_commands.command(name="spotify", description="Send a Spotify playlist link.")
    async def spotify(self, interaction: discord.Interaction):
        await interaction.response.send_message("https://open.spotify.com/playlist/6BcRgFzoIAfLX7QZKEl8Gy?si=2c5c81b9c42d492f")

    @app_commands.command(name="hug", description="Hug a user.")
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} hugged {member.mention} [:3](https://tenor.com/hvKioj0rdk7.gif)"
        )

    @app_commands.command(name="kiss", description="Kiss a user.")
    async def kiss(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} kissed {member.mention} [:3](https://tenor.com/YkoQ.gif)"
        )

    @app_commands.command(name="punch", description="Punch a user.")
    async def punch(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} punched {member.mention} [:3](https://tenor.com/cM5NrlugNQL.gif)"
        )

    @app_commands.command(name="roleplaykick", description="Kick a user.")
    async def kick(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} kicked {member.mention} [:3](https://tenor.com/9q2k.gif)"
        )

    @app_commands.command(name="banhammer", description="Use the banhammer on a user.")
    async def banhammer(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} used the banhammer on {member.mention} [:3](https://tenor.com/bcWNT.gif)"
        )

    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors with the bot!")
    async def rps(self, interaction: discord.Interaction, choice: str):
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
    async def marry(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} proposed to {member.mention} [:3](https://tenor.com/s7SQl7AQGte.gif)"
        )

    @app_commands.command(name="divorce", description="Divorce a user.")
    async def divorce(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} divorced {member.mention} [:3](https://tenor.com/n5Q7Zeucrnq.gif)"
        )

    @app_commands.command(name="slay", description="Slay a user.")
    async def slay(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} slayed {member.mention} mortal combat style"
            )

    @app_commands.command(name="backshots", description="Give backshots to a user.")
    async def arrest(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} has given {member.mention}. them heavenly backshots"
            )
        
    @app_commands.command(name="arrest", description="Arrest a user.")
    async def arrest(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        await interaction.response.send_message(
            f"{interaction.user.mention} has arrested {member.mention} for {reason if reason else 'no reason given'}."
            )

    @app_commands.command(name="drug", description="Drug a user.")
    async def drug(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} has drugged {member.mention} with a mysterious substance. "
            "They are now in a state of blissful confusion, unable to comprehend their surroundings. "
        )

    @app_commands.command(name="scream", description="Scream at a user.")
    async def scream(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} screamed at {member.mention} in a fit of rage. "
            "The sound echoed through the halls, leaving everyone in shock."
        )

    @app_commands.command(name="toss", description="Toss a user.")
    async def toss(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} tossed {member.mention} into the air like a ragdoll. "
            "They landed with a thud."
        )            
    
    @app_commands.command(name="rob", description="Rob a user.")
    async def rob(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} robbed {member.mention} of their wallet. "
            "They are now on the run from the law."
        )

    @app_commands.command(name="buydrugs", description="Buy drugs from a user.")
    async def buy_drugs(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            f"{interaction.user.mention} bought drugs from {member.mention}. "
        )    

async def setup(bot):
    await bot.add_cog(CustomCommandsCog(bot))
