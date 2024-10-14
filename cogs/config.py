import glob
import os

import aiofiles
import orjson


class Config:
    @classmethod
    async def saveChatLogs(cls, userId: int, log: list):
        async with aiofiles.open(f"./chatLogs/{userId}.json", "wb+") as f:
            await f.write(orjson.dumps(log))

    @classmethod
    async def saveUserModel(cls, userId: int, model: str):
        async with aiofiles.open(f"./models.json", "wb+") as f:
            binary = await f.read()
            json = orjson.loads(binary if binary != b"" else "{}".encode())
            json[f"{userId}"] = model
            await f.write(orjson.dumps(json))

    @classmethod
    async def loadChatLogs(cls, userId: int) -> list:
        async with aiofiles.open(f"./chatLogs/{userId}.json", "wb+") as f:
            binary = await f.read()
            return orjson.loads(binary if binary != b"" else "{}".encode())

    @classmethod
    async def loadChatLogsList(cls) -> dict[int, list]:
        users = {}
        pathList = glob.glob("./chatlogs/*.json")
        for path in pathList:
            userId = os.path.basename(path)
            users[int(userId)] = await cls.loadChatLogs(userId)
        return users

    @classmethod
    async def loadUserModels(cls) -> dict:
        async with aiofiles.open(f"./models.json", "wb+") as f:
            binary = await f.read()
            return orjson.loads(binary if binary != b"" else "{}".encode())
