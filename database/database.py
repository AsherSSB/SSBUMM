import discord
from discord.ext import commands
import aiosqlite

class Database():
    async def __init__(self, bot):
        self.bot = bot
        self.con = await aiosqlite.connect("SSBUMM")
        self.cur = await self.con.cursor()

    