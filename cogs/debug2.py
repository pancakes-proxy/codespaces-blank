# cogs/admin.py

import discord
import asyncio
import subprocess
from discord.ext import commands
from discord import app_commands

def is_command_safe(user_id: str, command: str, sudo_allowed: set) -> (bool, str):
    """
    Validates a shell command to ensure it is safe to execute.
    Returns a tuple (allowed: bool, reason: str).
    """
    lower_command = command.lower()
    # Block CTRL+C control characters.
    if "\x03" in command or "ctrl+c" in lower_command:
        return (False, "Commands containing CTRL+C control characters are not allowed under any circumstances.")

    # Keywords that are always blocked.
    always_block_keywords = [
        "ssh", "systemctl", "service", "chown", "chmod", "iptables", "ufw",
        "make", "cmake", "curl", "wget", "useradd", "usermod", "userdel",
        "passwd", "groupadd", "groupmod", "groupdel",
        "rm -rf", "dd", "mv", "cp", "netstat", "ifconfig", "ip ",
        "scp", "ftp", "rsync", "modprobe", "insmod", "rmmod", "fdisk",
        "mkfs", "parted", "lsblk"
    ]
    for keyword in always_block_keywords:
        if keyword in lower_command:
            return (False, f"Commands containing '{keyword}' are not allowed under any circumstances.")

    allowed_package_commands = ["pip", "snap", "apt", "yum", "dnf", "zypper", "apk"]

    # If the user is not in sudo mode, restrict commands.
    if user_id not in sudo_allowed:
        if lower_command.strip().startswith("git"):
            return (False, "Git commands require debug mode to be executed.")
        if any(lower_command.strip().startswith(pkg) for pkg in allowed_package_commands):
            return (False, "Package management commands require debug mode to be executed.")
        return (True, "")
    else:
        # When in debug mode, only allow certain commands.
        allowed_debug_commands = allowed_package_commands + ["git", "pkill", "pip"]
        if any(lower_command.strip().startswith(cmd) for cmd in allowed_debug_commands):
            return (True, "")
        else:
            return (False, "In debug mode, only package management and git commands are allowed.")

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="wl", description="Whitelist a user to allow them to execute shell commands. (Admin-only)")
    async def wl(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        self.bot.whitelisted_users.add(member.id)
        log_msg = f"[LOG] Admin {interaction.user} (ID: {interaction.user.id}) whitelisted user {member} (ID: {member.id})."
        print(log_msg)
        await interaction.response.send_message(f"User {member.mention} has been whitelisted.\n{log_msg}")

    @app_commands.command(name="cmd", description="Execute a shell command. (Whitelisted users only; dangerous commands are restricted)")
    async def cmd(self, interaction: discord.Interaction, command: str):
        if interaction.user.id not in self.bot.whitelisted_users:
            await interaction.response.send_message("You are not whitelisted to run shell commands.", ephemeral=True)
            return

        allowed, reason = is_command_safe(str(interaction.user.id), command, self.bot.sudo_allowed_users)
        if not allowed:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        log_exe = (
            f"[LOG] User {interaction.user} (ID: {interaction.user.id}) is executing:\n"
            f"`{command}` in channel {interaction.channel}."
        )
        print(log_exe)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode().strip() or stderr.decode().strip() or "No output."
        except Exception as e:
            output = f"Error executing command: {e}"
        log_output = f"[LOG] Output: {output}"
        print(log_output)
        final_response = f"```\n{output}\n```\n{log_exe}\n{log_output}"
        await interaction.response.send_message(final_response)

    @app_commands.command(name="debugcmd", description="Activates debug mode and enables package management & git commands. (Hidden command)")
    async def debugcmd(self, interaction: discord.Interaction, service_code_input: str):
        if service_code_input == self.bot.service_code:
            self.bot.sudo_allowed_users.add(interaction.user.id)
            log_msg = f"[LOG] Debug mode activated for user {interaction.user} (ID: {interaction.user.id})."
            print(log_msg)
            await interaction.response.send_message(f"Debug mode activated. {log_msg}")
        else:
            log_msg = (
                f"[LOG] Invalid debug attempt by user {interaction.user} (ID: {interaction.user.id}) "
                f"with service code '{service_code_input}'."
            )
            print(log_msg)
            await interaction.response.send_message("Invalid service code.", ephemeral=True)

    @app_commands.command(name="cmdout", description="Shows the last 20 lines of terminal output dynamically.")
    async def cmdout(self, interaction: discord.Interaction):
        try:
            process = await asyncio.create_subprocess_exec(
                "dmesg", "--user", "-T",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            output, error = await process.communicate()
            if process.returncode != 0:
                await interaction.response.send_message(f"An error occurred: {error.decode().strip()}", ephemeral=True)
            else:
                # Get the last 20 lines of output.
                lines = output.decode().strip().split("\n")[-20:]
                result = "\n".join(lines) or "No recent terminal output available."
                await interaction.response.send_message(f"```\n{result}\n```")
        except Exception as e:
            await interaction.response.send_message(f"An unexpected error occurred: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
