# cogs/fun.py
import discord
import random
from discord.ext import commands
from discord import app_commands
from enum import Enum

# Define an enum for coinflip
class CoinSide(str, Enum):
    heads = "heads"
    tails = "tails"

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Pings a server and returns the result.")
    async def ping(self, interaction: discord.Interaction):
        import asyncio
        import platform
        if platform.system().lower() == 'windows':
            cmd = ['ping', 'staffteam.learnhelp.cc', '-n', '5']
        else:
            cmd = ['ping', 'staffteam.learnhelp.cc', '-c', '5']
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                output = f"Ping command failed with error: {stderr.decode().strip()}"
            else:
                output = stdout.decode().strip()
        except FileNotFoundError:
            output = "Ping command not found. Please ensure it is installed on the system."
        except Exception as e:
            output = f"An unexpected error occurred: {e}"
        await interaction.response.send_message(f"```{output}```")

    @app_commands.command(name="coinflip", description="Flip a coin by picking heads or tails.")
    async def coinflip(self, interaction: discord.Interaction, side: CoinSide):
        number = random.randint(1, 100)
        result = "heads" if number % 2 == 0 else "tails"
        win = (result == side.value)
        await interaction.response.send_message(
            f"Rolled number: {number}.\nThe coin landed on **{result}**.\nYou {'won' if win else 'lost'}!"
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

    @app_commands.command(name="kick", description="Kick a user.")
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
            f"{interaction.user.mention} slayed {member.mention} mortal combat style")

@app_commands.command(name="school", description="Displays a school menu.")
async def school(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Kasane's School Menu",
        description="Welcome to the school menu! Here's what we have on offer:",
        color=discord.Color.blue()
    )
    embed.add_field(name="📚 Math", value="Numbers, equations, and questionable life choices.", inline=False)
    embed.add_field(name="🔬 Science", value="Explosions, questionable experiments, and caffeine.", inline=False)
    embed.add_field(name="📖 Literature", value="Books, drama, and overdue essays.", inline=False)
    embed.add_field(name="🎨 Art", value="Paint, mess, and existential crises.", inline=False)
    embed.add_field(name="🏫 History", value="Dead people, wars, and dates you won't remember.", inline=False)
    embed.set_footer(text="Enjoy your learning! 📚")

    class SchoolMenuView(discord.ui.View):
        @discord.ui.button(label="Math", style=discord.ButtonStyle.primary, emoji="📚")
        async def math_button(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Math Menu",
                    description="- Calculator Smashing Contest\n- Pi Eating Challenge\n- Guess the Teacher's Age (Impossible)",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Science", style=discord.ButtonStyle.primary, emoji="🔬")
        async def science_button(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Science Menu",
                    description="- Failed Lab Experiments\n- Mystery Substances Table\n- Who Set Off the Fire Alarm?",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Literature", style=discord.ButtonStyle.primary, emoji="📖")
        async def literature_button(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Literature Menu",
                    description="- Last-Minute Essay Generator\n- Overanalyze That Poem\n- Shakespearean Roasts",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Art", style=discord.ButtonStyle.primary, emoji="🎨")
        async def art_button(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Art Menu",
                    description="- Paint Water or Coffee?\n- Abstract Doodles Only\n- Glue Stick Speedrun",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="History", style=discord.ButtonStyle.primary, emoji="🏫")
        async def history_button(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="History Menu",
                    description="- Guess That Century\n- Ancient Meme Review\n- Who Actually Did Their Homework?",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

    await interaction.response.send_message(embed=embed, view=SchoolMenuView())

@app_commands.command(name="party", description="Displays a party menu.")
async def party(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Kasane's Party Menu",
        description="Welcome to the party menu! Here's what we have on offer:",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎉 Party Games", value="Fun games to play with friends.", inline=False)
    embed.add_field(name="🎶 Music", value="Dance to the latest hits!", inline=False)
    embed.add_field(name="🍕 Food", value="Delicious snacks and drinks.", inline=False)
    embed.add_field(name="🎈 Decorations", value="Party decorations to set the mood.", inline=False)
    embed.set_footer(text="Let's get this party started! 🎊")

    class PartyMenuView(discord.ui.View):
        @discord.ui.button(label="Party Games", style=discord.ButtonStyle.primary, emoji="🎉")
        async def party_games(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Party Games",
                    description="- Charades\n- Musical Chairs\n- Dance Off",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Music", style=discord.ButtonStyle.primary, emoji="🎶")
        async def music(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Music",
                    description="- Top 40 Playlist\n- Karaoke Time\n- DJ Requests",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Food", style=discord.ButtonStyle.primary, emoji="🍕")
        async def food(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Food",
                    description="- Pizza\n- Chips & Dip\n- Cupcakes",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Decorations", style=discord.ButtonStyle.primary, emoji="🎈")
        async def decorations(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Decorations",
                    description="- Balloons\n- Streamers\n- Confetti",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

    await interaction.response.send_message(embed=embed, view=PartyMenuView())

@app_commands.command(name="snack", description="Displays a snack menu.")
async def snack(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Kasane's Snack Menu",
        description="Welcome to the snack menu! Here's what we have on offer:",
        color=discord.Color.blue()
    )
    embed.add_field(name="🍔 Burger", value="A delicious burger with all the fixings.", inline=False)
    embed.add_field(name="🌭 Hot Dog", value="A classic hot dog, perfect for any occasion.", inline=False)
    embed.add_field(name="🥤 Soda", value="A refreshing soda to quench your thirst.", inline=False)
    embed.add_field(name="🍟 Fries", value="Crispy golden fries, straight from the fryer.", inline=False)
    embed.add_field(name="🍕 Pizza Slice", value="A cheesy slice of pizza, just for you.", inline=False)
    embed.add_field(name="🍩 Donut", value="A sweet donut to satisfy your cravings.", inline=False)
    embed.set_footer(text="Enjoy your snacks! 🍴")

    class SnackMenuView(discord.ui.View):
        @discord.ui.button(label="Burger", style=discord.ButtonStyle.primary, emoji="🍔")
        async def burger(interaction: discord.Interaction, _button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Burger",
                    description="A delicious burger with all the fixings.",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Hot Dog", style=discord.ButtonStyle.primary, emoji="🌭")
        async def hotdog(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Hot Dog",
                    description="A classic hot dog, perfect for any occasion.",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Soda", style=discord.ButtonStyle.primary, emoji="🥤")
        async def soda(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Soda",
                    description="A refreshing soda to quench your thirst.",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Fries", style=discord.ButtonStyle.primary, emoji="🍟")
        async def fries(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Fries",
                    description="Crispy golden fries, straight from the fryer.",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Pizza Slice", style=discord.ButtonStyle.primary, emoji="🍕")
        async def pizza(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Pizza Slice",
                    description="A cheesy slice of pizza, just for you.",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

        @discord.ui.button(label="Donut", style=discord.ButtonStyle.primary, emoji="🍩")
        async def donut(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Donut",
                    description="A sweet donut to satisfy your cravings.",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

    await interaction.response.send_message(embed=embed, view=SnackMenuView())



@app_commands.command(name="discordsupportinvite", description="Send a link to the Discord support server.")
async def discordsupportinvite(self, interaction: discord.Interaction):
        await interaction.response.send_message("https://discord.gg/9CFwFRPNH4")

@app_commands.command(name="developersite", description="Sends a link to the developer's website.")
async def developersite(self, interaction: discord.Interaction):
        await interaction.response.send_message("https://learnhelp.cc/")

@app_commands.command(name="supportserver", description="Sends a link to the support server.")
async def supportserver(self, interaction: discord.Interaction):
        await interaction.response.send_message("https://discord.gg/9CFwFRPNH4")
        

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))