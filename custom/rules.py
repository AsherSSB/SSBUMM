import discord
import asyncio

class Rules():
    def __init__(self, bot):
        self.bot = bot

    async def display_rules(self, interaction:discord.Interaction):
        rules:str = """
1. Report matches honestly
2. Stay present in discord while waiting for a match
3. Be respectful to your opponent in game
4. Do not report without valid reason
5. Do not spam report
6. Only queue if playing on a wired connection or on VERY consistant wifi"""
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(content=rules, ephemeral=True)
        
        await asyncio.sleep(3)  

        view = discord.ui.View()
        accept_button = AcceptButton()
        view.add_item(accept_button)

        await interaction.followup.send(view=view, ephemeral=True)

        try:
            await asyncio.wait_for(accept_button.event.wait(), timeout=60.0)  # Wait for 60 seconds
        except asyncio.TimeoutError:
            await interaction.followup.send("Button timed out.", ephemeral=True)

        return accept_button.accepted


class AcceptButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Accept", style=discord.ButtonStyle.success, custom_id="acceptrules")
        self.accepted:bool = False
        self.event = asyncio.Event()

    async def callback(self, interaction: discord.Interaction):
        self.accepted = True
        self.event.set()
        await interaction.response.send_message("Thanks! And have fun!", ephemeral=True)
        