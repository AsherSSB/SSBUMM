import discord
from discord.ext import commands
import asyncio
import logging

class Confirmation():
    def __init__(self, bot):
        self.bot = bot

    async def send_match_confirmation(self, interaction: discord.Interaction, reputation: int):
        try:
            view = ConfirmationView()
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
                return False

            return view.isaccepted
        except Exception as e:
            logging.error(f"Failed to send match confirmation: {e}")
            return False

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
    def __init__(self):
        super().__init__(label="Accept", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        self.view.isaccepted = True
        self.view.event.set()
        await interaction.response.send_message("Thanks! And have fun!", ephemeral=True)


class DeclineButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Decline", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        self.view.isaccepted = False
        self.view.event.set()
        await interaction.response.send_message("Match declined.", ephemeral=True)


class ConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.isaccepted = None
        self.event = asyncio.Event()
        self.add_item(AcceptButton())
        self.add_item(DeclineButton())
