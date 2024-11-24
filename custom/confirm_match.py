import discord
from discord.ext import commands
import asyncio
import logging
from custom.exceptions import *

class Confirmation():
    def __init__(self, bot):
        self.bot = bot

    async def send_character_select(self, interaction:discord.Interaction) -> str:
        modal = CharacterSelect()
        await interaction.response.send_modal(modal)
        await modal.wait()
        return modal.name

    async def send_match_confirmation(self, interaction: discord.Interaction, reputation: int):
        try:
            view = ConfirmationView(interaction)
            strrep = self.evaluate_reputation(reputation)
            confirm_message = f"""
Match Found!

Opponent Reputation: {strrep}

Accept Match?"""
            await interaction.followup.send(content=confirm_message, view=view, ephemeral=True)

            try:
                await asyncio.wait_for(view.event.wait(), timeout=30.0)  # Wait for 30 seconds
            except asyncio.TimeoutError:
                await interaction.followup.send("Button timed out.", ephemeral=True)
                raise ConfirmationTimeout()

            return (view.isaccepted, view.character)
        
        except Exception as e:
            logging.error(f"Failed to send match confirmation: {e}")
            return (False, None)

    def evaluate_reputation(self, rep: int) -> str:
        if rep == 0:
            return "Spotless"
        elif rep < 3:
            return "Good"
        elif rep < 6:
            return "Acceptable"
        else:
            return "Poor"


class AcceptButton(discord.ui.Button):
    def __init__(self, interaction):
        super().__init__(label="Accept", style=discord.ButtonStyle.success)
        self.interaction = interaction

    async def callback(self, interaction: discord.Interaction):
        self.view.isaccepted = True
        modal = CharacterSelect()
        await interaction.response.send_modal(modal)

        await asyncio.wait_for(modal.event.wait(), timeout=120)  # 2 minutes timeout

        self.view.character = modal.name
        self.view.event.set()



class DeclineButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Decline", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        self.view.isaccepted = False
        self.view.event.set()
        await interaction.response.send_message("Match declined.", ephemeral=True)


class ConfirmationView(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=30)
        self.isaccepted = None
        self.event = asyncio.Event()
        self.character:str | None = None
        self.add_item(AcceptButton(interaction))
        self.add_item(DeclineButton())

class CharacterSelect(discord.ui.Modal):
    def __init__(self):
        super().__init__(title='Character Select')
        self.event = asyncio.Event()
        self.name = discord.ui.TextInput(label='Character')
        self.add_item(self.name)


    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=False)
        self.event.set()
        