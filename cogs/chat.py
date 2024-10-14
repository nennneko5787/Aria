import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

from .config import Config


class AIChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.openai = AsyncOpenAI(api_key="banana", base_url="https://api.voids.top/v1")
        self.chatLogs: dict[int, list] = {}
        self.userModels: dict[int, str] = {}
        self.cooldown: dict[discord.User, bool] = {}

    @commands.Cog.listener()
    async def setup_hook(self):
        self.chatLogs = await Config.loadChatLogsList()
        self.userModels: dict[int, str] = await Config.loadUserModels()
        print("ok")

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
        if (interaction.user in self.cooldown) and (self.cooldown[interaction.user]):
            await interaction.response.send_message("クールダウン中", ephemeral=True)
            return
        self.cooldown[interaction.user] = True
        await interaction.response.send_message("<:loading:1295326859587747860> 生成中...")
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
        stream = await self.openai.chat.completions.create(
            model=self.userModels[interaction.user.id],
            messages=messages,
            stream=True,
        )
        response = ""
        async for chunk in stream:
            response += chunk.choices[0].delta.content or ""
            if response == "":
                await interaction.edit_original_response(content="生成中...")
            else:
                await interaction.edit_original_response(content=response)
        messages.append({"role": "system", "content": response})
        self.chatLogs[interaction.user.id] = messages
        await Config.saveChatLogs(
            interaction.user.id, self.chatLogs[interaction.user.id]
        )
        self.cooldown[interaction.user] = False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (message.author.id != self.bot.user.id) & (self.bot.user in message.mentions):
            if (message.author in self.cooldown) and (self.cooldown[message.author]):
                await message.reply("クールダウン中")
                return
            self.cooldown[interaction.user] = True
            replyedMessage = await message.reply("<:loading:1295326859587747860> 生成中...")
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
            stream = await self.openai.chat.completions.create(
                model=self.userModels[message.author.id],
                messages=messages,
                stream=True,
            )
            response = ""
            async for chunk in stream:
                response += chunk.choices[0].delta.content or ""
                if response == "":
                    await replyedMessage.edit(content="生成中...")
                else:
                    await replyedMessage.edit(content=response)
            messages.append({"role": "system", "content": response})
            self.chatLogs[message.author.id] = messages
            await Config.saveChatLogs(
                message.author.id, self.chatLogs[message.author.id]
            )
            self.cooldown[interaction.user] = False


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChatCog(bot))
