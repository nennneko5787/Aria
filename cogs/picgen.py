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

    async def cog_load(self):
        await self.loadAccounts()

    async def loadAccounts(self):
        if os.path.exists(self.account_file):
            async with aiofiles.open(self.account_file, "rb") as f:
                try:
                    content = await f.read()
                    if content:  # Only try to load if file isn't empty
                        self.accounts = orjson.loads(content)
                    else:
                        self.accounts = {}
                except orjson.JSONDecodeError:
                    print(
                        f"Error decoding JSON from {self.account_file}, initializing empty accounts."
                    )
                    self.accounts = {}
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

        self.accounts[str(user_id)] = {"email": email, "password": password}
        await self.saveAccounts()

        pixai: PixAI = self.user_pixai_instances.get(
            user_id, PixAI()
        )  # Create PixAI instance for the user
        await pixai.initialize(email, password, login=False)
        await pixai.claim_daily_quota()
        await pixai.claim_questionnaire_quota()

        self.user_pixai_instances[str(user_id)] = pixai  # Store the instance

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
            user_id = interaction.user.id

            # Attempt to get the PixAI instance
            pixai: PixAI = self.user_pixai_instances.get(user_id, None)
            if pixai is None:
                await self.generateAccount(user_id)
                pixai = self.user_pixai_instances.get(user_id)  # Retrieve it again

            # Check if pixai was created successfully
            if pixai is None:
                await interaction.edit_original_response(
                    content="アカウントの生成に失敗しました。再試行してください。"
                )
                return

            # Now you can safely call get_quota()
            quota = await pixai.get_quota()
            if (user_id not in self.accounts) or (quota < 2200):
                await self.generateAccount(user_id)
                pixai = self.user_pixai_instances.get(
                    user_id
                )  # Retrieve again after generation

            # Ensure pixai is still valid after quota check
            if pixai is None:
                await interaction.edit_original_response(
                    content="アカウントの生成に失敗しました。再試行してください。"
                )
                return

            # Continue with the image generation
            email = self.accounts[str(user_id)]["email"]
            password = self.accounts[str(user_id)]["password"]

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
