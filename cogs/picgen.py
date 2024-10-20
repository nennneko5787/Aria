import random, string
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
        self.client = httpx.AsyncClient(timeout=300)
        self.cooldown: dict[int, bool] = {}
        self.accounts = {}  # Store user accounts in memory
        self.account_file = "user_pix_accounts.json"
        self.user_pixai_instances: dict[int, PixAI] = {}
        self.proxies: list[str] = []

    async def cog_load(self):
        await self.loadAccounts()
        response = await self.client.get(
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=socks4,socks5&proxy_format=protocolipport&format=json&timeout=1000"
        )
        self.proxies = response.json()["proxies"]

    async def loadAccounts(self):
        if os.path.exists(self.account_file):
            async with aiofiles.open(self.account_file, "rb") as f:
                self.accounts = orjson.loads(await f.read())
        else:
            self.accounts = {}

    async def saveAccounts(self):
        async with aiofiles.open(self.account_file, "wb") as f:
            await f.write(orjson.dumps(self.accounts))

    def randomID(self, n: int):
        return "".join(random.choices(string.ascii_letters + string.digits, k=n))

    async def generateAccount(self, user_id: int):
        email = f"{self.randomID(10)}@14chan.jp"
        password = self.randomID(20)

        self.accounts[user_id] = {"email": email, "password": password}
        await self.saveAccounts()

        pixai = self.user_pixai_instances.get(
            user_id, PixAI(proxy=random.choice(self.proxies))
        )  # Create PixAI instance for the user
        await pixai.initialize(email, password, login=False)
        await pixai.claim_daily_quota()
        await pixai.claim_questionnaire_quota()

        self.user_pixai_instances[user_id] = pixai  # Store the instance

    @app_commands.command(name="picgen", description="プロンプトから画像を生成します。")
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
            user_id = interaction.user.id

            pixai = self.user_pixai_instances.get(
                user_id, PixAI()
            )  # Use user-specific PixAI instance

            quota = await pixai.get_quota()
            if (user_id not in self.accounts) or (quota < 2200):
                await self.generateAccount(user_id)
            else:
                email = self.accounts[user_id]["email"]
                password = self.accounts[user_id]["password"]

                await pixai.initialize(email, password, login=True)

            queryId = await pixai.generate_image(
                prompt, negative_prompts=negative_prompts, model_id=model_id
            )
            while True:
                mediaIds = await pixai.get_task_by_id(queryId)
                if mediaIds:
                    break
                await asyncio.sleep(3)

            files = []
            count = 0
            for mediaId in mediaIds:
                response = await self.client.get(await pixai.get_media(mediaId))
                files.append(
                    discord.File(io.BytesIO(response.content), filename=f"{count}.png")
                )
                count += 1

            await interaction.edit_original_response(
                content="生成完了", attachments=files
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.edit_original_response(content=str(e))
        finally:
            self.cooldown[interaction.user.id] = False


async def setup(bot: commands.Bot):
    await bot.add_cog(PicGenCog(bot))
