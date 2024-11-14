import discord
from discord.ext import commands
from custom.rules import Rules
from custom.elo import Elo
from database.database import Database
import logging
import asyncio
from custom.confirm_match import Confirmation
from random import random
import time
import os

class Controller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.mmopen:bool = False
        self.queue:list[tuple[int, discord.Interaction]] = []
        self.loop_task = None

    
    async def cog_load(self):
        self.db = Database()
        await self.db.initialize()


    async def mm_loop(self):
        self.queue = []
        while self.mmopen:
            while len(self.queue) > 1:
                player1:tuple[int, discord.Interaction] = self.queue.pop(0)
                player2:tuple[int, discord.Interaction] = self.queue.pop(0)
                # Run the match confirmation process asynchronously
                asyncio.create_task(self.match_players(player1, player2))
            await asyncio.sleep(1)  # Adjust the sleep duration as needed

    async def match_players(self, player1:tuple, player2:tuple):
        try:
            # Query for player info by id
            p1info = await self.db.idqeury(player1[0])
            p2info = await self.db.idqeury(player2[0])
            con = Confirmation(self.bot)
            p1confirm_task = asyncio.create_task(con.send_match_confirmation(player1[1], p2info[1]))
            p2confirm_task = asyncio.create_task(con.send_match_confirmation(player2[1], p1info[1]))
            p1confirm, p2confirm = await asyncio.gather(p1confirm_task, p2confirm_task)
            if p1confirm and p2confirm:
                # TODO: Game functionality
                await self.start_stage_select(player1[1], player2[1])
            else:
                await self.send_declined_messages((player1[1], p1confirm,), (player2[1], p2confirm))

        except Exception as e:
            logging.error(f"Failed to match players: {e}")
    

    async def send_declined_messages(self, player1:tuple[discord.Interaction, bool], player2:tuple[discord.Interaction, bool]):
        if player1[1]:
            await player1[0].followup.send("Your opponent has declined, requeueing", ephemeral=True)
            await self.requeue((player1[0].user.id, player1[0]))
        if player2[1]:
            await player2[0].followup.send("Your opponent has declined, requeueing", ephemeral=True)
            await self.requeue((player2[0].user.id, player2[0]))


    async def requeue(self, player:tuple[int, discord.Interaction]):
        queuepos = int(random() * 1000) % (len(self.queue) + 1 )
        self.queue.insert(queuepos, player)


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


    @discord.app_commands.command(name="testconfirm")
    async def test_confirm(self, interaction: discord.Interaction):
        con = Confirmation(self.bot)
        confirm:bool = await con.send_match_confirmation(interaction, 3)
        print(confirm)


    @discord.app_commands.command(name="printq")
    async def test_printq(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{self.queue}")


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
        if not await self.db.userExists(interaction.user.id):
            interaction.response.send_message("You must read and accept the rules before entering queue")
            raise Exception("User not in DB")

        if self.mmopen == False:
            await interaction.response.send_message("Matchmaking is currently closed", ephemeral=True)
            raise Exception("MM is closed")

        for players in self.queue:
            if interaction.user.id == players[0]:
                await interaction.response.send_message("You are already in queue", ephemeral=True)
                raise Exception("You are already in queue")

        await interaction.response.send_message("You have entered queue", ephemeral=True)
        self.queue.append((interaction.user.id, interaction))


    @discord.app_commands.command(name="modalme")
    async def test_modal(self, interaction:discord.Interaction):
        modal = CharacterSelect()
        await interaction.response.send_modal(modal)
        await modal.wait()
        

    @discord.app_commands.command(name="coinflip")
    async def coinflipcommand(self, interaction:discord.Interaction):
        await interaction.response.send_message(f"{await self.coinflip()}")


    async def coinflip(self):
        return int(random() * 10 % 2 + 1)
    

    async def start_stage_select(self, p1interact:discord.Interaction, p2interact:discord.Interaction):
        stagelist = ("Battlefield", "Small Battlefield", "Final Destination", "Hollow Bastion", "Town and City")
        stages = list(stagelist)
        coinflip:int = await self.coinflip()
        print(f"coinflip result: {coinflip}")
        if coinflip == 1:
            print("player 1 won the coinflip")
            choice = await self.send_stage_select(p1interact, stages, 1)
            stages.remove(choice[0])
            print(stages)
            choice = await self.send_stage_select(p2interact, stages, 2)
            stages = [stage for stage in stages if stage not in choice]
            print(stages)
            stages = await self.send_stage_select(p1interact, stages, 1)
        else:
            print("player 2 won the coinflip")
            choice = await self.send_stage_select(p2interact, stages, 1)
            stages.remove(choice[0])
            print(stages)
            choice = await self.send_stage_select(p1interact, stages, 2)
            stages = [stage for stage in stages if stage not in choice]
            print(stages)
            stages = await self.send_stage_select(p2interact, stages, 1)
        # stages is now a 1 item list
        p1interact.followup.send(f"Begin Match on {stages[0]}", ephemeral=True)
        p2interact.followup.send(f"Begin Match on {stages[0]}", ephemeral=True)




    async def send_stage_select(self, interaction:discord.Interaction, stages, picks):
        options = [discord.SelectOption(label=stage) for stage in stages]
        select = Stages(picks, picks, options)
        view = discord.ui.View()
        view.add_item(select)
        await interaction.followup.send(view=view, ephemeral=True)
        try:
            await asyncio.wait_for(select.event.wait(), timeout=60.0)  # Wait for 60 seconds
        except asyncio.TimeoutError:
            await interaction.followup.send("Selection timed out", ephemeral=True)
        
        return select.stages


    async def start_game(self, p1:discord.Interaction, p2:discord.Interaction, stage, coin):
        if coin == 1:
            host = p1
        else:
            host = p2


        content = """
        
        """

    @discord.app_commands.command(name="embed")
    async def test_send_embed(self, interaction:discord.Interaction):
        file = discord.File("Battlefield.png")
        stage = "Pokemon Stadium 2"
        embed=discord.Embed(title="Ranked Match Making", description=f"Playing on {stage}")
        unix = int(time.time()) + 15 * 60
        embed.set_image(url=f"attachment://{file}")
        embed.add_field(name="Player 1", value="Sonic", inline=True)
        embed.add_field(name="Score", value="0 - 0", inline=True)
        embed.add_field(name="Player 2", value="Terry", inline=True)
        embed.set_footer(text=f"<t:{unix}:R>")
        
        await interaction.response.send_message(file=file,embed=embed)


    @discord.app_commands.command(name='abrir')
    async def abrir_case(self, interaction:discord.Interaction):
        embed = discord.Embed(title="Test", color=0x00ff00)

        item_image_path = 'stages/Battlefield.png'
        if os.path.exists(item_image_path) and os.path.isfile(item_image_path):
            file = discord.File(item_image_path)
            embed.set_image(url=f"attachment://Battlefield.png")  # then use that file as the embed url
            await interaction.response.send_message(file=file, embed=embed)
        else:
            await interaction.response.send_message(embed=embed)



class CharacterSelect(discord.ui.Modal, title='Character Select'):
    name = discord.ui.TextInput(label='Character')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Thanks for your response!', ephemeral=True)
        

class Stages(discord.ui.Select):
    def __init__(self, min_values , max_values, options):
        super().__init__(min_values=min_values, max_values=max_values, options=options)
        self.stages:list = []
        self.event = asyncio.Event()

    async def callback(self, interaction):
        await interaction.response.send_message("selected", ephemeral=True)
        self.stages = self.values
        self.event.set()


class Game(discord.Embed):
    def __init__(self, stage, ):
        super().__init__(title="Ranked MM", description=f"playing on{stage}")
        stage_image = discord.File(f"stages/{stage}.png", filename=f"{stage}.png")
        self.set_image(url=f"attachment://{stage}.png")
    















async def setup(bot):
    controller = Controller(bot)
    await bot.add_cog(controller)
    await controller.cog_load()
