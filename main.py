# main.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from cogs.application import PlayerMenuView

# Загрузка токена из скрытого файла .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Регистрация персистентной кнопки (чтобы работала после перезапуска бота)
        self.add_view(PlayerMenuView())
        # Автоматическая загрузка кога анкет
        await self.load_extension("cogs.application")

bot = Bot()

@bot.event
async def on_ready():
    print(f"Бот успешно запущен под именем: {bot.user}")

if __name__ == "__main__":
    bot.run(TOKEN)
