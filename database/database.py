import discord
from discord.ext import commands
import aiosqlite
import logging

class Database():
    def __init__(self):
        self.con = None
        self.cur = None


    async def initialize(self):
        self.con = await aiosqlite.connect("SSBUMM.db")
        self.cur = await self.con.cursor()
        logging.info("Database initialized")



    async def create_user_table(self):
        await self.cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, elo INTEGER, reputation INTEGER)")
        await self.con.commit()
        logging.info("User table created")


    # TODO: check for user already in database
    async def add_user(self, userid):
        if not await self.userExists(userid):
            logging.info(f"User {userid} already exists in database")
            raise Exception("User already exists in database")
        try:
            await self.cur.execute("INSERT INTO users (id, elo, reputation) VALUES (?, 1000, 0)", (userid,))
            await self.con.commit()
            logging.info(f"User {id} added to database")
        except Exception as e:
            logging.error(f"Failed to add user {id}: {e}")


    async def idqeury(self, userid:int):
        res = await self.cur.execute("SELECT elo, reputation FROM users WHERE id = ?", (userid,))
        return await res.fetchone()
    

    async def userExists(self, userid:int):
        res = await self.cur.execute("SELECT 1 FROM users WHERE id = ? LIMIT 1", (userid,))
        result = await res.fetchone()
        if result is None:
            return False
        return True
    
