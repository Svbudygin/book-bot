import sys
import asyncio
from handlers import bot, dispatcher


async def main() -> None:
    await dispatcher.start_polling(bot)
    # pass


asyncio.run(main())
