import discord
from discord.ext import commands
import math


class Elo():
    def __init__(self, bot):
        self.bot = bot

    # outcome is 1 for PA win, 0 for PB win
    async def adjust_elo(self, playerArating, playerBrating,
                            Ka, Kb, outcome) -> tuple[int, int]:
        # Calculate the Winning Probability of Player B
        Pb = self.probability(playerArating, playerBrating)

        # Calculate the Winning Probability of Player A
        Pa = self.probability(playerBrating, playerArating)

        # Update the Elo Ratings
        playerArating = playerArating + Ka * (outcome - Pa)
        playerBrating = playerBrating + Kb * ((1 - outcome) - Pb)

        # return updated ratings
        return (round(playerArating), round(playerBrating))
            


    def probability(self, rating1, rating2):
    # Calculate and return the expected score
        return 1.0 / (1 + math.pow(10, (rating1 - rating2) / 400.0))