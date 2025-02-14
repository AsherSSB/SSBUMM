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



    async def add_user(self, userid):
        if await self.userExists(userid):
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
    

    async def increment_rep(self, userid:int):
        try:
            await self.cur.execute("UPDATE users SET reputation = reputation + 1 WHERE id = ?",(userid,))
            await self.con.commit()
        except Exception as e:
            logging.error(f"Faled to update user reputation {userid}: {e}")


    async def reset_rep(self, userid:int):
        try:
            await self.cur.execute("UPDATE users SET reputation = 0 WHERE id = ?",(userid))
            await self.con.commit()
        except Exception as e:
            logging.error(f"Faled to reset user reputation {userid}: {e}")

    
    async def update_elo_single(self, newelo:int, userid:int):
        try:
            await self.cur.execute("UPDATE users SET elo = ? WHERE id = ?",(newelo, userid))
            await self.con.commit()
        except Exception as e:
            logging.error(f"Faled to update user elo {userid}: {e}")

    # each touple is new elo followed by user id
    async def update_elo_double(self, users:list[tuple[int, int]]):
        try:
            await self.cur.executemany("UPDATE users SET elo = ? WHERE id = ?", users)
            await self.con.commit()
        except Exception as e:
            logging.error(f"Failed to update elo for {users[0][1]} and {users[1][1]}: {e}")


    async def get_top_10_elo(self):
        try:
            res = await self.cur.execute("SELECT id, elo FROM users ORDER BY elo DESC LIMIT 10")
            return await res.fetchall()
        except Exception as e:
            logging.error(f"Failed to query top 10 ELO: {e}")
            return []
