import aiohttp
import asyncio

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.deep_linking import decode_payload
from main.mongo import MongoManager
from main.settings import MasterSettings

mongo = MongoManager()

bot = Bot(token=MasterSettings.BOT_TOKEN)
dp = Dispatcher(bot)

start_chat_button = types.KeyboardButton(text='Начать чат')
start_chat_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(start_chat_button)

stop_chat_button = types.KeyboardButton(text='Закончить чат')
stop_chat_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(stop_chat_button)

@dp.message_handler(commands=["start"])
async def send_welcome(message: types.message.Message):
    await message.answer(text="Привет, для того, чтобы начать общение, заполни анкету")
    await message.answer(text="Введи своё имя (никнейм, псевдоним, позывной)")
    await mongo.register_user(message.from_user.id)


@dp.message_handler(content_types=types.ContentType.TEXT)
async def form_fulfill(message: types.message.Message):
    tgid = message.from_user.id
    text: str = message.text
    user = await mongo.get_user(tgid)
    status = user['status']
    reply_text = "Анкета уже заполнена!"

    if await mongo.chat_exists(tgid=tgid):
        chat = await mongo.get_chat(tgid)
        if text == "Закончить чат":
            await mongo.delete_chat(tgid)
            await mongo.delete_chat(chat['elsetgid'])
            await bot.send_message(chat_id=tgid, text="Чат закончен", reply_markup=start_chat_keyboard)
            await bot.send_message(chat_id=chat['elsetgid'], text="Чат закончен", reply_markup=start_chat_keyboard)
        else:
            await bot.send_message(chat_id=chat['elsetgid'], text=text)

    else:
        if status == 0:
            field = 'name'
            if len(text) < 3 or len(text) > 10:
                await message.answer("Имя должно быть от 3 до 10 символов. Попробуй ещё раз")
                return
            reply_text = "Хорошо, теперь введи твой возраст"

        elif status == 1:
            field = 'age'
            if not text.isdecimal():
                await message.answer("Возраст должен быть числом. Попробуй ещё раз")
                return
            age = int(text)
            if age < 18:
                await message.answer("Извини, малышам сюда нельзя.")
                return
            if age > 100:
                await message.answer("А тебе точно столько лет?)")
                return
            reply_text = "Отлично, теперь напишите пару строк о себе."

        elif status == 2:
            field = 'bio'
            if len(text) < 0 or len(text) > 100:
                await message.answer("А можно покороче?")
                return
            reply_text = "Замечательно, анкета заполнена!"

        if status < 3:
            await mongo.update_user(tgid, text)

        if text == "Начать чат":
            res = await mongo.create_chat_request(tgid)
            if res:
                request = await mongo.get_random_chat_request(tgid)
                if request is None:
                    await message.answer("сейчас начнём чат :)")
                else:
                    await mongo.start_chat(tgid, request["tgid"])
                    await mongo.start_chat(request["tgid"], tgid)
                    await bot.send_message(chat_id=request['tgid'], text=await mongo.user_as_info(tgid))
                    await bot.send_message(chat_id=request['tgid'], text="Приятного общения!", reply_markup=stop_chat_keyboard)

                    await bot.send_message(chat_id=tgid, text=await mongo.user_as_info(request['tgid']))
                    await bot.send_message(chat_id=tgid, text="Приятного общения!", reply_markup=stop_chat_keyboard)

                    await mongo.delete_chat_request(tgid)
                    await mongo.delete_chat_request(request['tgid'])
            else:
                await message.answer("уже ищем собеседника, нужно немного подождать")

        else:
            if status == 2 or status:
                await message.answer(reply_text, reply_markup=start_chat_keyboard)
            else:
                await message.answer(reply_text)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(mongo.connect())
    executor.start_polling(dp, skip_updates=True)
