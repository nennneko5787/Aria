import glob
import os

import aiofiles
import aiofiles.os
import orjson


class Config:
    @classmethod
    async def saveChatLogs(cls, userId: int, log: list):
        try:
            async with aiofiles.open(f"./chatLogs/{userId}.json", "wb") as f:
                await f.write(orjson.dumps(log))
        except Exception as e:
            print(f"Error saving chat logs for user {userId}: {e}")

    @classmethod
    async def saveUserModel(cls, userId: int, model: str):
        try:
            async with aiofiles.open(f"./models.json", "rb") as f:
                binary = await f.read()
                data = orjson.loads(binary if binary else "{}".encode())

            data[str(userId)] = model

            async with aiofiles.open(f"./models.json", "wb") as f:
                await f.write(orjson.dumps(data))
        except Exception as e:
            print(f"Error saving user model for user {userId}: {e}")

    @classmethod
    async def loadChatLogs(cls, userId: int) -> list:
        try:
            file_path = f"./chatLogs/{userId}.json"
            if not await aiofiles.os.path.exists(file_path):
                return []

            async with aiofiles.open(file_path, "rb") as f:
                binary = await f.read()
                return orjson.loads(binary) if binary else []
        except Exception as e:
            print(f"Error loading chat logs for user {userId}: {e}")
            return []

    @classmethod
    async def loadChatLogsList(cls) -> dict[int, list]:
        users = {}
        try:
            pathList = glob.glob("./chatLogs/*.json")
            for path in pathList:
                userId = int(os.path.basename(path).split(".")[0])
                users[userId] = await cls.loadChatLogs(userId)
        except Exception as e:
            print(f"Error loading chat logs list: {e}")
        return users

    @classmethod
    async def loadUserModels(cls) -> dict:
        try:
            if not await aiofiles.os.path.exists("./models.json"):
                return {}

            async with aiofiles.open("./models.json", "rb") as f:
                binary = await f.read()
                return orjson.loads(binary) if binary else {}
        except Exception as e:
            print(f"Error loading user models: {e}")
            return {}
