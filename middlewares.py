from typing import Callable, Awaitable, Any
from aiogram.types import TelegramObject
from aiogram import BaseMiddleware


class AccessMiddleware(BaseMiddleware):
    def __init__(self, access_ids: list):
        self.access_ids = access_ids
        super().__init__()

    async def __call__(                                           
        self,                            
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any] 
    ):  
        if int(event.from_user.id) in self.access_ids:    
            await handler(event, data)
        # else:
        #     await message.answer("Access Denied") 