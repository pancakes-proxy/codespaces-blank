import discord
from discord.ext import commands

class HowToCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="howto",
    description="How to contribute to the repository."
    )
    async def howto(self, ctx):
        embed = discord.Embed(
            title="Contributing Guide",
            description="Follow these steps to contribute to the repository.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="1. Fork the Repository",
            value=(
                "Visit the repository and click **Fork** to create your own copy:\n"
                "[GitHub Repository](https://github.com/pancakes-proxy/wdiscordbot.git)"
            ),
            inline=False
        )
        embed.add_field(
            name="2. Clone Your Fork",
            value=(
                "Clone your fork locally by running:\n"
                "```\ngit clone <your_fork_url>\n```"
            ),
            inline=False
        )
        embed.add_field(
            name="3. Create a Branch",
            value=(
                "Create a new branch for your changes to keep things organized:\n"
                "```\ngit checkout -b feature/your-feature-name\n```"
            ),
            inline=False
        )
        embed.add_field(
            name="4. Edit or Create Cogs",
            value=(
                "All cogs are stored in the `/cogs` directory. Create or edit a cog following the structure:\n"
                "- Each cog is a Python file defining a class that inherits from `commands.Cog`.\n"
                "- Follow existing naming conventions and code structure for consistency."
            ),
            inline=False
        )
        embed.add_field(
            name="5. Test Your Changes",
            value="Run your bot locally to ensure your modifications work correctly.",
            inline=False
        )
        embed.add_field(
            name="6. Commit and Push",
            value=(
                "After testing, commit your changes with a clear message and push your branch:\n"
                "```\ngit commit -m \"Your descriptive commit message\"\ngit push origin feature/your-feature-name\n```"
            ),
            inline=False
        )
        embed.add_field(
            name="7. Create a Pull Request",
            value=(
                "Finally, open a pull request on GitHub so that the maintainers may review your changes."
            ),
            inline=False
        )
        embed.set_footer(text="Thank you for your contributions!")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HowToCog(bot))
