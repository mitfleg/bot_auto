from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from handlers.common import getConfig


bot = Bot(token=getConfig('TOKEN'))
dp = Dispatcher(bot, storage=MemoryStorage())

if __name__ == "__main__":
    from handlers import dp
    from handlers.auto.check import IsNumber
    dp.bind_filter(IsNumber)
    executor.start_polling(dp, skip_updates=True)
