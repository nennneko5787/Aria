import copy

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

from .config import Config

DEFAULT_MODEL = "gemini-1.5-pro-exp-0827"


class AIChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot, chatLogs: dict, models: dict):
        self.bot = bot
        self.openai = AsyncOpenAI(api_key="banana", base_url="https://api.voids.top/v1")
        self.chatLogs: dict[int, list] = chatLogs
        self.userModels: dict[int, str] = models
        self.cooldown: dict[int, bool] = {}

    @app_commands.command(name="model", description="AIのモデルを変更します。")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def modelCommand(self, interaction: discord.Interaction, model: str):
        await interaction.response.defer(ephemeral=True)
        self.userModels[interaction.user.id] = model
        await Config.saveUserModel(interaction.user.id, model)
        await interaction.followup.send(
            f"モデルを**{model}**に変更しました。", ephemeral=True
        )

    @app_commands.command(name="clear", description="AIとの会話履歴をリセットします。")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def clearCommand(self, interaction: discord.Interaction):
        if self.cooldown.get(interaction.user.id):
            await interaction.response.send_message("クールダウン中", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        self.chatLogs[interaction.user.id] = []
        await Config.saveChatLogs(interaction.user.id, [])
        await interaction.followup.send("会話履歴をリセットしました。", ephemeral=True)

    @app_commands.command(name="chat", description="AIと会話します。")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def chatCommand(self, interaction: discord.Interaction, text: str):
        await self.process_chat(interaction.user, text, interaction=interaction)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if (message.author.id != self.bot.user.id) & (
            (self.bot.user in message.mentions)
            | (message.type == discord.ChannelType.private)
        ):
            await self.process_chat(
                message.author, message.clean_content, message=message
            )

    async def process_chat(
        self,
        user: discord.User,
        text: str,
        interaction: discord.Interaction = None,
        message: discord.Message = None,
    ):
        if self.cooldown.get(user.id):
            if interaction:
                await interaction.response.send_message(
                    "クールダウン中", ephemeral=True
                )
            if message:
                await message.reply("クールダウン中")
            return

        self.cooldown[user.id] = True

        if interaction:
            await interaction.response.defer()
        elif message:
            replyedMessage = await message.reply(
                "<a:loading:1295326859587747860> 生成中..."
            )

        if user.id not in self.chatLogs:
            self.chatLogs[user.id] = []
            await Config.saveChatLogs(user.id, [])

        if user.id not in self.userModels:
            self.userModels[user.id] = DEFAULT_MODEL
            await Config.saveUserModel(user.id, DEFAULT_MODEL)

        messages = copy.deepcopy(self.chatLogs[user.id])
        messages.append({"role": "user", "content": text})

        try:
            stream = await self.openai.chat.completions.create(
                model=self.userModels[user.id],
                messages=messages,
                stream=True,
            )
            response = ""
            async for chunk in stream:
                response += chunk.choices[0].delta.content or ""
                if interaction:
                    await interaction.edit_original_response(
                        content=response or "<a:loading:1295326859587747860> 準備中..."
                    )
                elif message:
                    await replyedMessage.edit(
                        content=response or "<a:loading:1295326859587747860> 準備中..."
                    )

            embed = discord.Embed(
                description="-# `/clear` コマンドで会話履歴をリセットできます。\n-# `/model` コマンドで使用するモデルを変更できます。\n-# もしこのボットが役に立ったら、KyashかPayPayで`nennneko5787`に何円かカンパしていただけるとありがたいです！",
                colour=discord.Colour.og_blurple(),
            )
            if interaction:
                await interaction.edit_original_response(content=response, embed=embed)
            elif message:
                await replyedMessage.edit(content=response, embed=embed)

            messages.append({"role": "system", "content": response})
            self.chatLogs[user.id] = copy.deepcopy(messages)
            await Config.saveChatLogs(user.id, self.chatLogs[user.id])

        except Exception as e:
            if interaction:
                await interaction.edit_original_response(content=f"Error: {str(e)}")
            elif message:
                await replyedMessage.edit(content=f"Error: {str(e)}")

        finally:
            self.cooldown[user.id] = False


async def setup(bot: commands.Bot):
    chatLogs = await Config.loadChatLogsList()
    models = await Config.loadUserModels()
    print(chatLogs, models)
    await bot.add_cog(AIChatCog(bot, chatLogs, models))
