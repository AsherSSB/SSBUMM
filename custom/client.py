import os
import discord
from discord.ext import commands


class Client(commands.Bot):
    
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self) -> None:
        cogsdir:str = "./cogs"
        
        for filename in os.listdir(cogsdir):
            if filename.endswith('.py'):
                await self.load_extension(f"cogs.{filename[:-3]}")

        await self.tree.sync() # This is global
