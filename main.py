import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from custom import Client
import logging

logging.basicConfig(level=logging.INFO)

bot = Client()

# TESTING PURPOSES
@bot.command()
async def sync(ctx: commands.Context):
    # sync to the guild where the command was used
    bot.tree.copy_global_to(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send(content="Success")


@bot.command()
@commands.is_owner()
async def reload(ctx, extension):
    await bot.reload_extension(f"cogs.{extension}")
    embed = discord.Embed(title='Reload', description=f'{extension} successfully reloaded', color=0xff00c8)
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print(f'{bot.user} is online!')


async def main():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

    async with bot:
        await bot.start(str(TOKEN))



asyncio.run(main())