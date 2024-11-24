import discord
from discord.ext import commands
import math


class Elo():
    def __init__(self, bot):
        self.bot = bot

    # outcome is 0 for PA win, 1 for PB win
    async def adjust_elo(self, playerArating, playerBrating, outcome) -> tuple[int, int]:
        k = 40
        # Calculate the Winning Probability of Player B
        Pb = self.probability(playerArating, playerBrating)

        # Calculate the Winning Probability of Player A
        Pa = self.probability(playerBrating, playerArating)

        # Update the Elo Ratings
        playerArating = playerArating + k * ((1 - outcome) - Pa)
        playerBrating = playerBrating + k * (outcome - Pb)

        # return updated ratings
        return (round(playerArating), round(playerBrating))
            


    def probability(self, rating1, rating2):
    # Calculate and return the expected score
        return 1.0 / (1 + math.pow(10, (rating1 - rating2) / 400.0))