import discord
from discord.ext import commands
from custom.rules import Rules
from custom.elo import Elo
from database.database import Database
import logging
import asyncio


class Controller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.mmopen:bool = False
        self.queue:list = []
        self.loop_task = None

    
    async def cog_load(self):
        self.db = Database()
        await self.db.initialize()


    async def mm_loop(self):
        self.queue = []
        while self.mmopen:
            print("Matchmaking opened")
            while len(self.queue) > 1:
                player1:tuple[int, discord.Interaction] = self.queue.pop(0)
                player2:tuple[int, discord.Interaction] = self.queue.pop(0)
                # TODO: matchmake player1 and player2
                await player1[1].followup.send("Hello", ephemeral=True)
                await player2[1].followup.send("Hi", ephemeral=True)

            await asyncio.sleep(1)  # Adjust the sleep duration as needed


    # TODO: UNSAFE, DELETE AFTER TESTING HAS CONCLUDED
    @commands.is_owner()
    @discord.app_commands.command(name="openmm")
    async def start_mm(self, interaction: discord.Interaction):
        self.mmopen = True
        if self.loop_task is None or self.loop_task.done():
            self.loop_task = asyncio.create_task(self.mm_loop())
        await interaction.response.send_message("Matchmaking started")


    @commands.is_owner()
    @discord.app_commands.command(name="closemm")
    async def stop_mm(self, interaction: discord.Interaction):
        self.mmopen = False
        await interaction.response.send_message("Matchmaking stopped")


    @discord.app_commands.command(name="rules")
    async def printrules(self, interaction:discord.Interaction):
        rules = Rules(self.bot)
        confirmation:bool = await rules.display_rules(interaction)
        if (confirmation):
            await self.add_user(interaction.user.id)
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

    
    # TODO: UNSAFE, DELETE AFTER TESTING HAS CONCLUDED
    @commands.is_owner()
    @discord.app_commands.command(name="newtable")
    async def create_table(self, interaction:discord.Interaction):
        try:
            await self.db.create_user_table()
            await interaction.response.send_message("table created!")
        except Exception as e:
            logging.error(f"Failed to create table: {e}")
            await interaction.response.send_message("Failed to create table")


    async def add_user(self, userid):
        try:
            logging.info(f"Attempting to add user {userid}")
            await self.db.add_user(userid)
            print("user added!")
        except Exception as e:
            logging.error(f"Failed to add user: {e}")
            print("Failed to add user.")

    @discord.app_commands.command(name="queueme")
    async def enter_queue(self, interaction:discord.Interaction):
        # TODO: verify user in database before adding them to queue
        # TODO: verify mm is open before adding to queue
        await interaction.response.send_message("You have entered queue", ephemeral=True)
        self.queue.append((interaction.user.id, interaction))


async def setup(bot):
    controller = Controller(bot)
    await bot.add_cog(controller)
    await controller.cog_load()

