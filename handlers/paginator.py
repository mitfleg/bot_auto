from itertools import islice
from typing import Iterable, Any, Iterator, Callable, Coroutine

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State
from aiogram.types import CallbackQuery


class Paginator:
    def __init__(
            self,
            data: types.InlineKeyboardMarkup | Iterable[types.InlineKeyboardButton] | Iterable[Iterable[types.InlineKeyboardButton]],
            state: State = None,
            callback_startswith: str = 'page_',
            cancel_text: str = 'cancel',
            cancel_callback: str = 'back',
            size: int = 8,
            page_separator: str = '/',
            dp: Dispatcher | None = None,
    ):
        """
        Example: paginator = Paginator(data=kb, size=5)

        :param data: An iterable object that stores an InlineKeyboardButton.
        :param callback_startswith: What should callback_data begin with in handler pagination. Default = 'page_'.
        :param size: Number of lines per page. Default = 8.
        :param state: Current state.
        :param page_separator: Separator for page numbers. Default = '/'.
        """
        self.dp = dp
        self.page_separator = page_separator
        self._state = state
        self._cancel_text = cancel_text
        self._cancel_callback = cancel_callback
        self._size = size
        self._startswith = callback_startswith
        if isinstance(data, types.InlineKeyboardMarkup):
            self._list_kb = list(
                self._chunk(
                    it=data.inline_keyboard,
                    size=self._size
                )
            )
        elif isinstance(data, Iterable):
            self._list_kb = list(
                self._chunk(
                    it=data,
                    size=self._size
                )
            )

    def __call__(
            self,
            current_page=0,
            *args,
            **kwargs
    ) -> types.InlineKeyboardMarkup:
        _list_current_page = self._list_kb[current_page]

        paginations = self._get_paginator(
            counts=len(self._list_kb),
            page=current_page,
            page_separator=self.page_separator,
            startswith=self._startswith
        )
        keyboard = types.InlineKeyboardMarkup(
            row_width=5,
            inline_keyboard=_list_current_page
        )
        cancel_button = types.InlineKeyboardButton(
            text=self._cancel_text,
            callback_data=self._cancel_callback
        )
        keyboard.add(*paginations)
        keyboard.add(cancel_button)

        if self.dp:
            self.paginator_handler()

        return keyboard

    @staticmethod
    def _get_page(call: types.CallbackQuery) -> int:
        return int(call.data[-1])

    @staticmethod
    def _chunk(it, size) -> Iterator[tuple[Any, ...]]:
        it = iter(it)
        return iter(lambda: tuple(islice(it, size)), ())

    @staticmethod
    def _get_paginator(
            counts: int,
            page: int,
            page_separator: str = '/',
            startswith: str = 'page_'
    ) -> list[types.InlineKeyboardButton]:
        counts -= 1
        paginations = []
        if page > 0:
            paginations.append(
                types.InlineKeyboardButton(
                    text='⏮️️',
                    callback_data=f'{startswith}0'
                )
            )
            paginations.append(
                types.InlineKeyboardButton(
                    text='⬅️',
                    callback_data=f'{startswith}{page - 1}'
                ),
            )
        paginations.append(
            types.InlineKeyboardButton(
                text=f'{page + 1}{page_separator}{counts + 1}',
                callback_data='pass'
            ),
        )
        if counts > page:
            paginations.append(
                types.InlineKeyboardButton(
                    text='➡️',
                    callback_data=f'{startswith}{page + 1}'
                )
            )
            paginations.append(
                types.InlineKeyboardButton(
                    text='⏭️',
                    callback_data=f'{startswith}{counts}'
                )
            )
        return paginations

    def paginator_handler(self) -> tuple[
        tuple[Callable[[CallbackQuery], Coroutine[Any, Any, None]], Text],
        dict[str, State | str]
    ]:
        async def _page(call: types.CallbackQuery, state: FSMContext):
            page = self._get_page(call)

            await call.message.edit_reply_markup(
                reply_markup=self.__call__(
                    current_page=page
                )
            )
            await state.update_data({f'last_page_{self._startswith}': page})

        if not self.dp:
            return \
                (_page, Text(startswith=self._startswith)), \
                {'state': self._state if self._state else '*'}
        else:
            self.dp.register_callback_query_handler(
                _page,
                Text(startswith=self._startswith),
                **{'state': self._state if self._state else '*'}
            )