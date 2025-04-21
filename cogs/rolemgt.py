import discord
from discord.ext import commands

class RoleManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="createrole",
        help=(
            "Creates a new role. Usage: /createrole <role name> <permissions> <color>\n"
            "• permissions: Comma-separated list of permission names (e.g. send_messages, manage_channels)\n"
            "• color: A hex color value (e.g. #FF5733)"
        )
    )
    @commands.has_permissions(manage_roles=True)
    async def createrole(self, ctx, role_name: str, perms: str, color: str):
        # Parse the permissions string into a discord.Permissions object.
        valid_perms = discord.Permissions.VALID_FLAGS
        kwargs = {}
        # Split by comma then go through each provided permission name.
        for perm in perms.split(','):
            perm_clean = perm.strip().lower()
            if perm_clean in valid_perms:
                kwargs[perm_clean] = True
            else:
                await ctx.send(f"Invalid permission name: `{perm_clean}`")
                return

        try:
            role_perms = discord.Permissions(**kwargs)
        except Exception as e:
            await ctx.send(f"Error setting permissions: {e}")
            return

        # Parse the hex color.
        try:
            # Remove a leading '#' if present and convert.
            color_int = int(color.lstrip('#'), 16)
            role_color = discord.Color(color_int)
        except ValueError:
            await ctx.send("Invalid color format. Please provide a valid hex value (e.g. #FF5733).")
            return

        try:
            role = await ctx.guild.create_role(
                name=role_name,
                permissions=role_perms,
                colour=role_color,
                reason=f"Role created by {ctx.author}"
            )
            await ctx.send(f"Role `{role.name}` created successfully.")
        except Exception as e:
            await ctx.send(f"Failed to create role: {e}")

    @commands.hybrid_command(
        name="viewroleperms",
        help="Displays the enabled permissions of a role. Usage: /viewroleperms <role>"
    )
    async def viewroleperms(self, ctx, role: discord.Role):
        # Convert the permissions to a dictionary and build a list of enabled permissions.
        perms_dict = role.permissions.to_dict()
        enabled_perms = [perm.replace("_", " ").title() for perm, value in perms_dict.items() if value]
        description = "\n".join(enabled_perms) if enabled_perms else "No permissions enabled."
        embed = discord.Embed(
            title=f"Permissions for Role: {role.name}",
            description=description,
            color=role.colour
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="addrole",
        help="Adds a role to a member. Usage: /addrole <member> <role>"
    )
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role, reason=f"Role added by {ctx.author}")
            await ctx.send(f"Role `{role.name}` added to {member.mention}.")
        except Exception as e:
            await ctx.send(f"Failed to add role: {e}")

    @commands.hybrid_command(
        name="removerole",
        help="Removes a role from a member. Usage: /removerole <member> <role>"
    )
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, role: discord.Role):
        try:
            await member.remove_roles(role, reason=f"Role removed by {ctx.author}")
            await ctx.send(f"Role `{role.name}` removed from {member.mention}.")
        except Exception as e:
            await ctx.send(f"Failed to remove role: {e}")

async def setup(bot):
    await bot.add_cog(RoleManagerCog(bot))
