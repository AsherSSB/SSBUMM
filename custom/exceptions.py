import discord

class InteractionTimout(Exception):
    def __init__(self, interaction:discord.Interaction = None):
        self.interaction = interaction

class ConfirmationTimeout(InteractionTimout):
    pass

class InGameTimeout(InteractionTimout):
    pass

class StageSelectTimeout(InteractionTimout):
    pass

class EmbedFail(Exception):
    pass