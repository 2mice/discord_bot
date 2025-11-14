import discord
from discord.ext import commands
import config

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.load_extension("cogs.welcome")
    await bot.load_extension("cogs.moderation")
    await bot.load_extension("cogs.music")
    await bot.load_extension("cogs.logging_system")
    await bot.load_extension("cogs.autorole")

    print("Cogs loaded.")

bot.run(config.TOKEN)
