import orjson
import discord
from discord import app_commands
from discord.ext import commands
from Pix_Chan import PixAI

class PicGenCog(commands.Cog):
    def __init__(self, bot: commands.Cog):
        self.bot = bot
        self.pix = PixAI()
        self.email: str = None
        
    @app_commands.command(name="picgen", description="プロンプトから画像を生成します。")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def picGenCommand(interaction: discord.Interaction, prompt: str, negative_prompt: str = None):
        await interaction.response.send_message("生成中…")