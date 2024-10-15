import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

from .config import Config


class AIChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot, chatLogs: dict, models: dict):
        self.bot = bot
        self.openai = AsyncOpenAI(api_key="banana", base_url="https://api.voids.top/v1")
        print(chatLogs)
        self.chatLogs: dict[int, list] = chatLogs
        print(models)
        self.userModels: dict[int, str] = models
        self.cooldown: dict[discord.User, bool] = {}

    @app_commands.command(name="model", description="AIのモデルを変更します。")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def modelCommand(self, interaction: discord.Interaction, model: str):
        await interaction.response.defer(ephemeral=True)
        self.userModels[interaction.user.id] = "gemini-1.5-pro-exp-0827"
        await Config.saveUserModel(
            interaction.user.id, self.userModels[interaction.user.id]
        )
        await interaction.followup.send(
            f"モデルを**{model}**に変更しました。", ephemeral=True
        )

    @app_commands.command(name="clear", description="AIとの会話履歴をリセットします。")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def clearCommand(self, interaction: discord.Interaction):
        if (interaction.user in self.cooldown) and (self.cooldown[interaction.user]):
            await interaction.response.send_message("クールダウン中", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        self.chatLogs[interaction.user.id] = []
        await Config.saveChatLogs(
            interaction.user.id, self.chatLogs[interaction.user.id]
        )
        await interaction.followup.send(
            f"会話履歴をリセットしました。", ephemeral=True
        )

    @app_commands.command(name="chat", description="AIと会話します。")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def chatCommand(self, interaction: discord.Interaction, text: str):
        print(f"{message.author.global_name} @{message.author.name} (ID: {message.author.id})")
        if (interaction.user in self.cooldown) and (self.cooldown[interaction.user]):
            await interaction.response.send_message("クールダウン中", ephemeral=True)
            return
        self.cooldown[interaction.user] = True
        await interaction.response.send_message("<a:loading:1295326859587747860> 生成中...")
        if not interaction.user.id in self.chatLogs:
            self.chatLogs[interaction.user.id] = []
            await Config.saveChatLogs(
                interaction.user.id, self.chatLogs[interaction.user.id]
            )
        if not interaction.user.id in self.userModels:
            self.userModels[interaction.user.id] = "gemini-1.5-pro-exp-0827"
            await Config.saveUserModel(
                interaction.user.id, self.userModels[interaction.user.id]
            )
        messages = self.chatLogs[interaction.user.id]
        messages.append({"role": "user", "content": text})
        try:
            stream = await self.openai.chat.completions.create(
                model=self.userModels[interaction.user.id],
                messages=messages,
                stream=True,
            )
            response = ""
            async for chunk in stream:
                response += chunk.choices[0].delta.content or ""
                if response == "":
                    await interaction.edit_original_response(content="<a:loading:1295326859587747860> 準備中...")
                else:
                    await interaction.edit_original_response(content=response)
            embed = discord.Embed(description="-# `/clear` コマンドで会話履歴をリセットできます。\n-# `/model` コマンドで使用するモデルを変更できます。\n-# もしこのボットが役に立ったら、KyashかPayPayで`nennneko5787`に何円かカンパしていただけるとありがたいです！", colour=discord.Colour.og_blurple())
            await interaction.edit_original_response(content=response, embed=embed)
            messages.append({"role": "system", "content": response})
            self.chatLogs[interaction.user.id] = messages
            await Config.saveChatLogs(
                interaction.user.id, self.chatLogs[interaction.user.id]
            )
        finally:
            self.cooldown[interaction.user] = False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        print(f"{message.author.global_name} @{message.author.name} (ID: {message.author.id})")
        dmchannel = await message.author.create_dm()
        if (message.author.id != self.bot.user.id) & ((self.bot.user in message.mentions) | (message.channel.id == dmchannel.id)):
            if (message.author in self.cooldown) and (self.cooldown[message.author]):
                await message.reply("クールダウン中")
                return
            self.cooldown[message.author] = True
            replyedMessage = await message.reply("<a:loading:1295326859587747860> 生成中...")
            if not message.author.id in self.chatLogs:
                self.chatLogs[message.author.id] = []
                await Config.saveChatLogs(
                    message.author.id, self.chatLogs[message.author.id]
                )
            if not message.author.id in self.userModels:
                self.userModels[message.author.id] = "gemini-1.5-pro-exp-0827"
                await Config.saveUserModel(
                    message.author.id, self.userModels[message.author.id]
                )
            messages = self.chatLogs[message.author.id]
            messages.append({"role": "user", "content": message.clean_content})
            try:
                stream = await self.openai.chat.completions.create(
                    model=self.userModels[message.author.id],
                    messages=messages,
                    stream=True,
                )
                response = ""
                async for chunk in stream:
                    response += chunk.choices[0].delta.content or ""
                    if response == "":
                        await replyedMessage.edit(content="<a:loading:1295326859587747860> 準備中...")
                    else:
                        await replyedMessage.edit(content=response)
                embed = discord.Embed(description="-# `/clear` コマンドで会話履歴をリセットできます。\n-# `/model` コマンドで使用するモデルを変更できます。\n-# もしこのボットが役に立ったら、KyashかPayPayで`nennneko5787`に何円かカンパしていただけるとありがたいです！", colour=discord.Colour.og_blurple())
                await replyedMessage.edit(content=response, embed=embed)
                messages.append({"role": "system", "content": response})
                self.chatLogs[message.author.id] = messages
                await Config.saveChatLogs(
                    message.author.id, self.chatLogs[message.author.id]
                )
            finally:
                self.cooldown[message.author] = False


async def setup(bot: commands.Bot):
    chatLogs = await Config.loadChatLogsList()
    models = await Config.loadUserModels()
    await bot.add_cog(AIChatCog(bot, chatLogs, models))
