import discord
from discord.ext import commands
from custom.rules import Rules
from custom.elo import Elo
from database.database import Database
import logging


class Controller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None

    
    async def cog_load(self):
        self.db = Database()
        await self.db.initialize()


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

        
    @commands.is_owner()
    @discord.app_commands.command(name="newtable")
    async def create_table(self, interaction:discord.Interaction):
        try:
            await self.db.create_user_table()
            await interaction.response.send_message("table created!")
        except Exception as e:
            logging.error(f"Failed to create table: {e}")
            await interaction.response.send_message("Failed to create table")


    @commands.is_owner()
    @discord.app_commands.command(name="newuser")
    async def add_user(self, interaction:discord.Interaction):
        try:
            logging.info(f"Attempting to add user {interaction.user.id}")
            await self.db.add_user(interaction.user.id)
            await interaction.response.send_message("user added!")
        except Exception as e:
            logging.error(f"Failed to add user: {e}")
            await interaction.response.send_message("Failed to add user.")


async def setup(bot):
    controller = Controller(bot)
    await bot.add_cog(controller)
    await controller.cog_load()

