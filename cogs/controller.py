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
from custom.exceptions import *
from custom.logger import *


# TODO: reorganize commands and functions
# TODO: add matchmaking based on elo

class Controller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.mmopen:bool = False
        self.queue:list[list[int, discord.Interaction]] = []
        self.loop_task = None
        self.prl = PlayerReportLogger().logger
        self.brl = BugReportLogger().logger
        self.fbl = FeedbackLogger().logger
        # TODO: move root logger here and replace logging with new attribute

    
    async def cog_load(self):
        self.db = Database()
        await self.db.initialize()


    async def mm_loop(self):
        try:
            self.queue = []
            while self.mmopen:
                while len(self.queue) > 1:
                    player1:list[int, discord.Interaction] = self.queue.pop(0)
                    player2:list[int, discord.Interaction] = self.queue.pop(0)
                    # Run the match confirmation process asynchronously
                    asyncio.create_task(self.match_players(player1, player2))
                await asyncio.sleep(1)  # TODO: Adjust the sleep duration as needed

        except ConfirmationTimeout as e:
            logging.error(f"Player {e.interaction.user.display_name} failed to confirm match")

        except OSError as e:
            print(f"Error while logging: {e}")

        except Exception as e:
            logging.error(f"Unknown Error: {e}")


    # TODO: refactor this nested dogshit
    async def match_players(self, player1:list[int, discord.Interaction], player2:list[int, discord.Interaction]):
        
        # Query for player info by id
        p1info = await self.db.idqeury(player1[0])
        p2info = await self.db.idqeury(player2[0])

        con = Confirmation(self.bot)
        p1confirm_task = asyncio.create_task(con.send_match_confirmation(player1[1], p2info[1]))
        p2confirm_task = asyncio.create_task(con.send_match_confirmation(player2[1], p1info[1]))
        p1confirm, p2confirm = await asyncio.gather(p1confirm_task, p2confirm_task)

        if p1confirm[0] and p2confirm[0]:
            await player1[1].followup.send(f"Your opponent is playing: {p2confirm[1]}", ephemeral=True)
            await player2[1].followup.send(f"Your opponent is playing: {p1confirm[1]}", ephemeral=True)

        elif (p1confirm[0]):
            await self.send_declined_message(player1[1])
            raise ConfirmationTimeout(player2[1])
        
        elif (p2confirm[0]):
            await self.send_declined_message(player2[1])
            raise ConfirmationTimeout(player1[1])
        
        else:
            raise ConfirmationTimeout
        
        try:
            stages, player1[1], player2[1] = await self.start_stage_select(player1[1], player2[1])
            # stages[1] is host
            if stages[1] == 1:
                await player2[1].followup.send("Your opponent is preparing the arena, please wait...", ephemeral=True)
                room, password = await self.send_host_view(player1[1])
                result = await self.game_loop(player1[1], player2[1], p1confirm[1], p2confirm[1], room, password, stages[0])
            else:
                await player1[1].followup.send("Your opponent is preparing the arena, please wait...", ephemeral=True)
                room, password = await self.send_host_view(player2[1])
                result = await self.game_loop(player2[1], player1[1], p2confirm[1], p1confirm[1], room, password, stages[0])
                if result == 1:
                    result = 0
                else:
                    result = 1

        except InGameTimeout as e:
            logging.error(f"{e.interaction.user.display_name} timed out during Game Loop")
            if e.interaction.user == player1[1].user:
                result = 1
            else:
                result = 0

        except StageSelectTimeout as e:
            logging.error(f"{e.interaction.user.display_name} timed out during stage select")
            if e.interaction.user == player1[1].user:
                result = 1
            else:
                result = 0

        except Exception as e:
            logging.error(f"Unknown Error While Starting/Playing Game: {e}")
            result = -1

        
        try:
            newelotuple:tuple[int, int] = await self.adjust_elo(p1info[0], p2info[0], result)

            p1update:tuple = (newelotuple[0], player1[1].user.id)
            p2update:tuple = (newelotuple[1], player2[1].user.id)
            eloupdatelist:list = [p1update, p2update]

            await self.db.update_elo_double(eloupdatelist)
        except Exception as e:
            logging.error(f"Unknown Error, Failed to Update Elo: {e}")
        
        if result == 0:
            await player1[1].followup.send(f"You Won!\nElo: {p1info[0]} -> {newelotuple[0]}", ephemeral=True)
            await player2[1].followup.send(f"You Lose.\nElo: {p2info[0]} -> {newelotuple[1]}", ephemeral=True)
            
        elif result == 1:
            await player1[1].followup.send(f"You Lose.\nElo: {p1info[0]} -> {newelotuple[0]}", ephemeral=True)
            await player2[1].followup.send(f"You Win!\nElo: {p2info[0]} -> {newelotuple[1]}", ephemeral=True)
        else:
            await player1[1].followup.send("An Error Has Occurred")
            await player2[1].followup.send("An Error Has Occurred")

        logging.info(f"Game successfully finished between {player1[1].user.display_name} and {player2[1].user.display_name}")

    
    # TODO: refactor more dogshit
    async def game_loop(self, player1:discord.Interaction, player2:discord.Interaction, p1char, p2char, room, password, starter):
        # score[0] p1 score score[1] p2 score
        score:list[int] = [0, 0]
        # I fucking hate dsr
        dsr1:str = None
        dsr2:str = None

        while 2 not in score:
            try:
                p1emb = asyncio.create_task(self.send_embed(player1, player2, starter, p1char, p2char, score, room, password))
                p2emb = asyncio.create_task(self.send_embed(player2, player1, starter, p2char, p1char, score, room, password))
                rep1, rep2 = await asyncio.gather(p1emb, p2emb)
                rep1, player1 = rep1
                rep2, player2 = rep2

            except EmbedFail:
                return -1
            
            if rep1 == 0 and rep2 == 1:
                score[0] = score[0] + 1
                dsr1 = starter
            elif rep1 == 1 and rep2 == 0:
                score[1] = score[1] + 1
                dsr2 = starter
            else:
                matching = False
                trys = 1
                while matching != True and trys < 3:
                    try:
                        await player1.followup.send("failed to match report", ephemeral=True)
                        await player2.followup.send("failed to match report", ephemeral=True)
                        view1 = ReportWinnerView(user=player1, opponent=player2, timeout=60)
                        view2 = ReportWinnerView(user=player2, opponent=player1, timeout=60)
                        await player1.followup.send(view = view1, ephemeral=True)
                        await player2.followup.send(view = view2, ephemeral=True)
                        rep1, player1 = await view1.wait_for_selection()
                        rep2, player2 = await view2.wait_for_selection()

                    except InGameTimeout as e:
                        if e.interaction.user == player1.user:
                            score = [0, 2]
                            logging.error(f"user {player1.user.display_name} failed to report retry winner")
                        else:
                            score = [2, 0]
                            logging.error(f"user {player2.user.display_name} failed to report retry winner")
                        break

                    if rep1 == 0 and rep2 == 1:
                        score[0] = score[0] + 1
                        matching = True
                        dsr1 = starter
                    elif rep1 == 1 and rep2 == 0:
                        score[1] = score[1] + 1
                        matching = True
                        dsr2 = starter
                    else:
                        trys = trys + 1
                
                if not matching:
                    return -1
                
            if 2 not in score:
                stagelist = ("Battlefield", 
                             "Small Battlefield", 
                             "Final Destination", 
                             "Hollow Bastion", 
                             "Town and City", 
                             "Smashville", 
                             "Kalos Pokemon League", 
                             "Pokemon Stadium 2",   
                             )
                stages = list(stagelist)
                try:
                    # result player 1 won
                    if rep1 == 0:
                        stages = [stage for stage in stages if stage != dsr2]
                        choice, player1 = await self.send_stage_select(player1, stages, 2, "Select 2 Bans")
                        stages = [stage for stage in stages if stage not in choice]
                        stages, player2 = await self.send_stage_select(player2, stages, 1, "Select Final Stage")
                        starter = stages[0]
                    else:
                        stages = [stage for stage in stages if stage != dsr1]
                        choice, player2 = await self.send_stage_select(player2, stages, 2, "Select 2 Bans")
                        stages = [stage for stage in stages if stage not in choice]
                        stages, player1 = await self.send_stage_select(player1, stages, 1, "Select Final Stage")
                        starter = stages[0]

                except Exception as e:
                    logging.error(f"Unknown Error, Failed to Stage Select {e}")

        if score[0] == 2:
            return 0
        else:
            return 1


    async def send_declined_message(self, player:discord.Interaction):
        await player.followup.send("Your opponent has declined, requeueing", ephemeral=True)
        await self.requeue((player.user.id, player))


    async def requeue(self, player:list[int, discord.Interaction]):
        queuepos = int(random() * 1000) % (len(self.queue) + 1 )
        self.queue.insert(queuepos, player)


    @discord.app_commands.command(name="openmm")
    async def start_mm(self, interaction: discord.Interaction):
        if interaction.user.id == 229036799790546944:
            self.mmopen = True
            if self.loop_task is None or self.loop_task.done():
                self.loop_task = asyncio.create_task(self.mm_loop())
            await interaction.response.send_message("Matchmaking started")
        else:
            await interaction.response.send_message("You do not have permission to do that")

    @discord.app_commands.command(name="closemm")
    async def stop_mm(self, interaction: discord.Interaction):
        if interaction.user.id != 229036799790546944:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

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


    async def adjust_elo(self, p1elo, p2elo, outcome):
        elo = Elo(self.bot)
        adjusted:tuple[int, int] = await elo.adjust_elo(p1elo, p2elo, outcome)
        # [0] p1 [1] p2
        return adjusted

    
    @discord.app_commands.command(name="newtable")
    async def create_table(self, interaction:discord.Interaction):
        if interaction.user.id == 229036799790546944:
            try:
                await self.db.create_user_table()
                await interaction.response.send_message("table created!")
            except Exception as e:
                logging.error(f"Failed to create table: {e}")
                await interaction.response.send_message("Failed to create table")
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)


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

        view = discord.ui.View()
        button = CancelButton(controller=self)
        view.add_item(button)
            
        await interaction.response.send_message("You have entered queue", ephemeral=True, view=view)
        self.queue.append([interaction.user.id, interaction])


    async def coinflip(self):
        return int(random() * 10 % 2 + 1)
    

    # TODO: refactor out if else
    async def start_stage_select(self, p1interact: discord.Interaction, p2interact: discord.Interaction):
        stagelist = ["Battlefield", "Small Battlefield", "Final Destination", "Hollow Bastion", "Town and City"]
        stages = list(stagelist)
        coinflip: int = await self.coinflip()

        if coinflip == 1:
            choice, p1interact = await self.send_stage_select(p1interact, stages, 1, "Select First Ban")
            stages.remove(choice[0])
            choice, p2interact = await self.send_stage_select(p2interact, stages, 2, "Select 2 Bans")
            stages = [stage for stage in stages if stage not in choice]
            stages, p1interact = await self.send_stage_select(p1interact, stages, 1, "Select Final Stage")
        else:
            choice, p2interact = await self.send_stage_select(p2interact, stages, 1, "Select First Ban")
            stages.remove(choice[0])
            choice, p1interact = await self.send_stage_select(p1interact, stages, 2, "Select 2 Bans")
            stages = [stage for stage in stages if stage not in choice]
            stages, p2interact = await self.send_stage_select(p2interact, stages, 1, "Select Final Stage")

        # stages is now a 1 item list
        # append coinflip winner to stages for further interactions
        stages.append(coinflip)
        return stages, p1interact, p2interact

    # TODO: refactor, make this readable
    async def send_stage_select(self, interaction:discord.Interaction, stages, picks, label):
        options = [discord.SelectOption(label=stage) for stage in stages]
        select = Stages(picks, options, label)
        view = discord.ui.View()
        view.add_item(select)
        await interaction.followup.send(view=view, ephemeral=True)

        try:
            await asyncio.wait_for(select.event.wait(), timeout=30)  # Wait for 30 sec
        except asyncio.TimeoutError:
            await interaction.followup.send("Selection timed out", ephemeral=True)
            raise StageSelectTimeout(interaction=interaction)
        
        updated_interaction = select.interaction

        return select.stages, updated_interaction


    async def send_embed(self, player:discord.Interaction, opponent:discord.Interaction, 
                         stage:str, p1char:str, p2char:str, score:list[int], room:str, password:str): # score[0] NEEDS to be player's score and score[1] opponent score
        try:
            embed=discord.Embed(title="Ranked Match Making", description=f"Playing on {stage} vs. {opponent.user.display_name}")
            # process stage string from player readable to embed readable
            stage = stage.replace(" ", "_")
            unix = int(time.time()) + 12 * 60
            item_image_path = f'stages/{stage}.png'
            file = discord.File(item_image_path)
            user_avatar_url = opponent.user.avatar.url
            embed.set_thumbnail(url=user_avatar_url)
            embed.add_field(name=player.user.display_name, value=p1char, inline=True)
            embed.add_field(name="Score", value=f"{score[0]} - {score[1]}", inline=True)
            embed.add_field(name=opponent.user.display_name, value=p2char, inline=True)
            embed.add_field(name="Game will expire", value=f"<t:{unix}:R>", inline=True)
            embed.add_field(name=f"Room Code:", value = room, inline=True)
            embed.add_field(name="Room Password:", value=password, inline=True)
            embed.set_image(url=f"attachment://{stage}.png")
            
            view = ReportWinnerView(user=player, opponent=opponent)

            await player.followup.send(file=file, embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logging.error(f"Unexpected Error Failed to Send Embed {e}")
            raise EmbedFail
        
        winner, interaction = await view.wait_for_selection()

        return winner, interaction
    

    async def send_host_view(self, interaction: discord.Interaction):
        modal = HostModal(interaction=interaction)
        view = HostView(interaction=interaction)
        button = HostButton(modal=modal)
        view.add_item(button)
        await interaction.followup.send(view=view, ephemeral=True)
        
        try:
            await asyncio.wait_for(modal.event.wait(), timeout=300)
        except asyncio.TimeoutError:
            raise InGameTimeout(interaction=interaction)
        
        interaction = button.interaction
        return modal.roomcode.value, modal.password.value
    

    @discord.app_commands.command(name="playerreport")
    async def report_player(self, interaction:discord.Interaction, user:discord.Member, message:str):
        await interaction.response.send_message(f"{user.display_name} reported for following reason: {message} ", ephemeral=True)
        await self.db.increment_rep(user.id)
        self.prl.info(f"{interaction.user.display_name}:{interaction.user.id} reported {user.display_name}:{user.id}  \"{message}\"")


    @discord.app_commands.command(name="bugreport")
    async def report_bug(self, interaction:discord.Interaction, bug:str):
        await interaction.response.send_message(f"bug report \"{bug}\" recieved", ephemeral=True)
        self.brl.info(f"{interaction.user.display_name}:{interaction.user.id} \"{bug}\"")
    

    @discord.app_commands.command(name="leaderboard")
    async def print_leaderboard(self, interaction:discord.Interaction):
        content = "------------Leaderboard\n------------\n"
        players = await self.db.get_top_10_elo()
        for rank, player in enumerate(players):
            line = f"{rank+1}. {interaction.guild.get_member(player[0]).display_name} - {player[1]}\n"
            content += line
        await interaction.response.send_message(content, ephemeral=True)


    @discord.app_commands.command(name="leaderembed")
    async def embed_leaderboard(self, interaction:discord.Interaction):
        embed = discord.Embed(title="Ranked Leaderboard")
        players = await self.db.get_top_10_elo()

        for rank, player in enumerate(players):
            embed.add_field(name=f"{rank+1}. {interaction.guild.get_member(player[0]).display_name}", value=player[1], inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    
    @discord.app_commands.command(name="feedback")
    async def send_feedback(self, interaction:discord.Interaction, message:str):
        self.fbl.log(message)
        interaction.response.send_message("Thank you for your feedback!", ephemeral=True)


    @discord.app_commands.command(name="commands")
    async def list_commands(self, interaction:discord.Interaction):
        content = """List of User Commands
        
/queueme - enters queue for Smash Ultimate matchmaking

/bugreport - sends a bug report. Must include a message describing the bug (what happened and when)

/feedback - sends a feedback message. Must include a message

/playerreport - report a player for bad behavior or excessive lag

/leaderboard - see top 10 highest rated players in message format

/leaderembed - see top 10 highest rated players in embed format"""
        await interaction.response.send_message(content=content)


    @discord.app_commands.command(name="help")
    async def help_list(self, interaction:discord.Interaction):
        content = """
To get started using the matchmaker, invoke /rules to read and accept the rules

Invoke /commands to see additional commands
"""
        await interaction.response.send_message(content=content)


# TODO: move classes to seperate files and fix dependancies
class Stages(discord.ui.Select):
    def __init__(self, picks, options, label):
        super().__init__(min_values=picks, max_values=picks, options=options, placeholder=label)
        self.stages:list = []
        self.event = asyncio.Event()
        self.interaction:discord.Interaction

    async def callback(self, interaction):
        await interaction.response.send_message("selected", ephemeral=True)
        self.stages = self.values
        self.interaction = interaction
        self.event.set()


class HostButton(discord.ui.Button):
    def __init__(self, *, label = "Enter Room Code", modal):
        super().__init__(label=label)
        self.modal:HostModal = modal
        self.interaction:discord.Interaction

    async def callback(self, interaction):
        await interaction.response.send_modal(self.modal)
        self.interaction = interaction


class HostModal(discord.ui.Modal):
    def __init__(self, interaction, title = "Enter Room Code"):
        super().__init__(title=title)
        self.interaction = interaction
        self.roomcode = discord.ui.TextInput(label="Room Code", required=True)
        self.password = discord.ui.TextInput(label="Password", required=True)
        self.add_item(self.roomcode)
        self.add_item(self.password)
        self.event = asyncio.Event()
    
    async def on_submit(self, interaction:discord.Interaction):
        self.event.set()
        self.interaction = interaction
        await interaction.response.defer(ephemeral=True, thinking=False)


class ReportWinnerView(discord.ui.View):
    def __init__(self, user:discord.Interaction, opponent, *, timeout=720):
        super().__init__(timeout=timeout)
        self.winner = None
        self.event = asyncio.Event()
        self.user = user
        self.interaction:discord.Interaction

        options = [
            discord.SelectOption(label=f"{user.user.display_name}", value=0),
            discord.SelectOption(label=f"{opponent.user.display_name}", value=1)
        ]
        
        self.select = discord.ui.Select(placeholder="Report Winner", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.winner = int(self.select.values[0])
        self.event.set()
        await interaction.response.defer()

    async def wait_for_selection(self):
        await self.event.wait()
        return self.winner, self.interaction
    
    async def on_timeout(self):
        self.event.set()
        raise InGameTimeout(interaction=self.user)
        

class HostView(discord.ui.View):
    def __init__(self, *, interaction):
        super().__init__(timeout=60)
        self.event = asyncio.Event()
        self.interaction = interaction

    # TODO:why does this not get handled before game loop or in matching?
    async def on_timeout(self):
        self.event.set()
        raise InGameTimeout(interaction=self.interaction)
        

class CancelButton(discord.ui.Button):
    def __init__(self, controller, *, style=discord.ButtonStyle.danger, label="Cancel Queue"):
        super().__init__(style=style, label=label)
        self.controller = controller

    async def callback(self, interaction: discord.Interaction):
        for player in self.controller.queue:
            if player[0] == interaction.user.id:
                self.controller.queue.remove(player)
        await interaction.response.send_message("You have been removed from queue", ephemeral=True)


async def setup(bot):
    controller = Controller(bot)
    await bot.add_cog(controller)
    await controller.cog_load()

