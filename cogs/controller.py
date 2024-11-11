import discord
from discord.ext import commands
from custom.rules import Rules
from custom.elo import Elo
import asyncio

class Controller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="rules")
    async def printrules(self, interaction:discord.Interaction):
        rules = Rules(self.bot)
        confirmation:bool = await rules.display_rules(interaction)
        if (confirmation):
            print(f"{interaction.user.id} confirmed")
        else:
            print(f"{interaction.user.id} rejected")


    @discord.app_commands.command(name="elo")
    async def printelo(self, interaction:discord.Interaction):
        elo = Elo(self.bot)
        p1:int = 1000
        p2:int = 1000
        adjusted:tuple[int, int] = await elo.adjust_elo(p1, p2, 30, 30, 1)
        print(f'{adjusted[0]} greater than {adjusted[1]}')
        await interaction.response.send_message(f"{adjusted[0]} {adjusted[1]}")
        


async def setup(bot):
    await bot.add_cog(Controller(bot))