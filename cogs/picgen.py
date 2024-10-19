import asyncio
import io
import os
import traceback

import aiofiles
import discord
import httpx
import orjson
from discord import app_commands
from discord.ext import commands
from Pix_Chan import PixAI


class PicGenCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pix = PixAI()
        self.email: str = None
        self.client = None
        self.account_file = "pix_account.json"
        self.client = httpx.AsyncClient(timeout=300)
        self.cooldown: dict[int, bool] = {}

    async def cog_load(self):
        await self.loadAccount()

    async def loadAccount(self):
        if os.path.exists(self.account_file):
            async with aiofiles.open(self.account_file, "rb") as f:
                account_data = orjson.loads(await f.read())
                self.email = account_data.get("email")
                self.password = account_data.get("password")

    async def saveAccount(self, email: str, password: str):
        account_data = {"email": email, "password": password}
        async with aiofiles.open(self.account_file, "wb") as f:
            await f.write(orjson.dumps(account_data))

    async def generateAccount(self):
        while True:
            response = await self.client.get(
                "https://api.voids.top/m-kuku-lu/create?domain=nyasan.com"
            )
            jsonData = response.json()
            if jsonData["success"]:
                break
        email = jsonData["email"]
        password = "pixpixsexsex"

        await self.saveAccount(email, password)

        await self.pix.initialize(email, password, login=False)
        await self.pix.claim_daily_quota()
        await self.pix.claim_questionnaire_quota()

    @app_commands.command(name="picgen", description="プロンプトから画像を生成します。")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def picGenCommand(
        self,
        interaction: discord.Interaction,
        prompt: str,
        negative_prompts: str = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, quality bad, hands bad, eyes bad, face bad, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name\n",
        model_id: str = "1709400693561386681",
    ):
        await interaction.response.send_message(
            "<a:loading:1295326859587747860> 生成中..."
        )
        self.cooldown[interaction.user.id] = True
        try:
            if not self.email:
                await self.generateAccount()

            quota = await self.pix.get_quota()
            if quota < 2200:
                await self.generateAccount()

            queryId = await self.pix.generate_image(
                prompt, negative_prompts=negative_prompts, model_id=model_id
            )
            while True:
                mediaIds = await self.pix.get_task_by_id(queryId)
                if mediaIds:
                    break
                await asyncio.sleep(3)

            files = []
            count = 0
            for mediaId in mediaIds:
                response = await self.client.get(await self.pix.get_media(mediaId))
                files.append(
                    discord.File(io.BytesIO(response.content), filename=f"{count}.png")
                )
                count += 1

            await interaction.edit_original_response(
                content="生成完了", attachments=files
            )
        except:
            traceback.print_exc()
            await self.generateAccount()
        finally:
            self.cooldown[interaction.user.id] = False


async def setup(bot: commands.Bot):
    await bot.add_cog(PicGenCog(bot))
