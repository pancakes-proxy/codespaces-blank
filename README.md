# WDiscordBot

*Last Updated: April 2025*

---

## Table of Contents
1. [Introduction](#introduction)
2. [Understanding the Cog System](#understanding-the-cog-system)
3. [Directory Structure and Core Components](#directory-structure-and-core-components)
4. [Guidelines for Modding Cogs](#guidelines-for-modding-cogs)
5. [Files to Avoid Editing](#files-to-avoid-editing)
6. [Creating and Integrating New Cogs](#creating-and-integrating-new-cogs)
7. [Testing and Debugging Your Mods](#testing-and-debugging-your-mods)
8. [Contributing](#contributing)
9. [Conclusion](#conclusion)

---

## Introduction

WDiscordBot is an open-source bot designed for customization. This guide explains how to safely modify its features while preserving critical functionality.

---

## Understanding the Cog System

The cog system enables modular bot functionality by separating commands, event listeners, and utilities into isolated components. Each cog has:
- **Commands**: Responds to user inputs.
- **Listeners**: Handles events like message triggers.
- **Helpers/Utilities**: Supports cog operations.

This separation makes the bot easy to maintain, scalable, and highly customizable.

---

## Directory Structure and Core Components

The following is an overview of the files within the `cogs` directory:

```
cogs
├── ai.py
├── application.py
├── automod.py
├── cog2.py
├── cogupdate.py
├── contribute.py
├── core.py
├── debug2.py
├── fun.py
├── howtohelp.py
├── issues.py
├── mod.py
├── rolemgt.py
├── roleplay.py
└── rule34.py
```

### Key Notes:
- **Core Files**:
  - `core.py`
  - `cog2.py`
  - `debug2.py`
  - `cogupdate.py`

  *These files should not be modified to ensure stability and functionality.*

- **Customizable Files**:
  - Files like `mod.py`, `automod.py`, and `rolemgt.py` are safe to edit for extending functionality.

---

## Guidelines for Modding Cogs

When modding WDiscordBot, follow these best practices:

1. **Use Version Control**:
   - Always back up your changes using Git.
   - Create separate branches for testing modifications.

2. **Extend Rather Than Edit**:
   - Avoid modifying core files; extend functionality by creating new cogs or using inheritance.

3. **Follow Coding Conventions**:
   - Use consistent naming, formatting, and documentation styles.

4. **Error Handling**:
   - Implement robust error handling and log exceptions for easier debugging.

5. **Keep Modifications Modular**:
   - Structure new features so they can be enabled or disabled independently.

---

## Files to Avoid Editing

Do not modify the following files:
- `core.py`
- `debug2.py`
- `cog2.py`
- `cogupdate.py`

### Why?
- **Preserves Core Stability**: These files are essential for WDiscordBot's base functionality.
- **Ensures Easy Updates**: Keeping these files untouched avoids compatibility issues during updates.
- **Facilitates Collaboration**: Contributors can focus on safe customization areas without worrying about breaking core features.

---

## Creating and Integrating New Cogs

To safely add new features, create a new cog file. Below is a template for your custom cog:

```python
# File: cogs/custommod.py

from discord.ext import commands

class CustomMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hello")
    async def hello_command(self, ctx):
        """
        Responds with a greeting message.
        """
        await ctx.send("Hello, world!")

def setup(bot):
    bot.add_cog(CustomMod(bot))
```

### Steps:
1. **Create the File**:
   Place your new `.py` file in the `cogs` directory.

2. **Register Your Cog**:
   Ensure the bot loader (`main.py`) is set to register the new cog via the `setup` function.

3. **Test**:
   Verify functionality locally before deploying changes.

---

## Testing and Debugging Your Mods

Thorough testing ensures stable modifications. Follow these steps:

1. **Use a Local Test Environment**:
   - Run WDiscordBot on a private server or test instance.
   - Test all commands and listeners.

2. **Write Unit and Integration Tests**:
   - Use mocks for simulating bot interactions.

3. **Monitor Logs**:
   - Leverage the bot's logging system to debug exceptions or errors.

---

## Contributing

We welcome contributions to WDiscordBot! Follow these steps to get started:

1. **Fork the Repository**:
   - Click "Fork" on the GitHub page to create your own copy.

2. **Clone Your Fork**:
   - Use `git clone <https://github.com/youruser/your-fork-name>` to download your fork locally.

3. **Create a Branch**:
   - Always create a new branch for your changes using a descriptive name.

4. **Implement Your Changes**:
   - Follow the coding guidelines and include necessary documentation and tests.

5. **Submit a Pull Request**:
   - After testing locally, submit a pull request with a detailed description of your changes.

6. **Participate in Code Review**:
   - Address feedback and update your branch as necessary.

7. **Stay Synchronized**:
   - Regularly update your fork with changes from the upstream repository to avoid merge conflicts.

### Need Help?
Join our Discord community or refer to the GitHub issue tracker for guidance.

---

## Conclusion

Follow these best practices to keep WDiscordBot stable, mod-friendly, and collaborative. By avoiding modifications to core files, using modular design, and adhering to contribution guidelines, you'll foster a vibrant development community.
