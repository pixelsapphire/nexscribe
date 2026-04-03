from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import auto, Enum
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import reactivex
from reactivex import Observable
from reactivex.disposable import Disposable
from reactivex.subject import BehaviorSubject


class ChatRole(Enum):
    USER = auto()
    SYSTEM = auto()
    ASSISTANT = auto()
    BOT = auto()
    DEVELOPER = auto()


@dataclass
class ChatMessage:
    content: str
    role: ChatRole
    extra: dict[str, Any]

    def __init__(self, content: str, role: ChatRole = ChatRole.USER, extra: dict[str, Any] | None = None) -> None:
        self.content: str = content
        self.role: ChatRole = role
        self.extra: dict[str, Any] = dict(extra) if extra is not None else {}

    def copy(self) -> ChatMessage: return ChatMessage(str(self.content), self.role, dict(self.extra))

    def substitute(self, *values: Any) -> ChatMessage: return ChatMessage(self.content % values, self.role, dict(self.extra))

    def __mod__(self, values: Any) -> ChatMessage: return self.substitute(values)


@dataclass
class ChatRequestSettings:
    model: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    extra: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass
class ChatRequestContext:
    conversation: list[ChatMessage] = field(default_factory=list[ChatMessage])
    settings: ChatRequestSettings = field(default_factory=ChatRequestSettings)


class ChatAPI(ABC):
    def __init__(self, bot_role: ChatRole = ChatRole.BOT) -> None:
        self._bot_role: ChatRole = bot_role

    def initialize(self) -> None: pass

    def process_message(self, message: ChatMessage) -> ChatMessage: return message

    @property
    def bot_role(self) -> ChatRole:
        return self._bot_role

    def stream_response_extra(self) -> dict[str, Any]:
        return {}

    def stream_response(self, context: ChatRequestContext) -> Observable[str]:
        def _subscribe(observer: Any, _: Any = None) -> Disposable:
            try:
                response: ChatMessage = self.get_response(context)
                observer.on_next(response.content)
                observer.on_completed()
            except Exception as error:
                observer.on_error(error)
            return Disposable()

        return cast(Observable[str], reactivex.create(_subscribe))

    @abstractmethod
    def get_response(self, context: ChatRequestContext) -> ChatMessage: ...


class ChatBot:

    def __init__(self) -> None:
        self._api: ChatAPI | None = None
        self._conversation_stream: BehaviorSubject[list[ChatMessage]] = BehaviorSubject([])
        self._latest_response: ChatMessage | None = None

    @property
    def conversation_stream(self) -> Observable[list[ChatMessage]]:
        return self._conversation_stream

    def _conversation_snapshot(self) -> list[ChatMessage]:
        return [m.copy() for m in self._conversation_stream.value]

    def connect(self, api: ChatAPI) -> None:
        self._api = api
        self._api.initialize()

    def tell(self, message: ChatMessage) -> None:
        if self._api is None: raise RuntimeError('Chatbot is not connected to an API')
        self._conversation_stream.on_next([*self._conversation_snapshot(), self._api.process_message(message.copy())])

    def attach_images(self, message: ChatMessage, image_paths: list[str | Path]) -> ChatMessage:
        enriched_message: ChatMessage = message.copy()
        existing_images: list[str] = []
        existing_images_raw: Any = enriched_message.extra.get('images')
        if isinstance(existing_images_raw, list):
            for image_path in cast(list[object], existing_images_raw):
                if isinstance(image_path, (str, Path)): existing_images.append(str(image_path))
        enriched_message.extra['images'] = [*existing_images, *(str(image_path) for image_path in image_paths)]
        return enriched_message

    def proceed(self, settings: ChatRequestSettings | None = None) -> None:
        if self._api is None: raise RuntimeError('Chatbot is not connected to an API')
        conversation: list[ChatMessage] = self._conversation_snapshot()
        response: ChatMessage = self._api.get_response(ChatRequestContext(conversation, settings or ChatRequestSettings())).copy()
        self._latest_response = response
        self._conversation_stream.on_next([*conversation, response])

    def proceed_stream(self, settings: ChatRequestSettings | None = None) -> Observable[str]:
        if self._api is None: raise RuntimeError('Chatbot is not connected to an API')

        conversation: list[ChatMessage] = self._conversation_snapshot()
        api: ChatAPI = self._api
        request_context: ChatRequestContext = ChatRequestContext(conversation, settings or ChatRequestSettings())

        def _subscribe(observer: Any, _: Any = None) -> Disposable:
            response_chunks: list[str] = []

            def _on_next(chunk: str) -> None:
                response_chunks.append(chunk)
                observer.on_next(chunk)

            def _on_error(error: Exception) -> None:
                observer.on_error(error)

            def _on_completed() -> None:
                extra: dict[str, Any] = dict(api.stream_response_extra())
                raw_id: object = extra.get('id')
                if not isinstance(raw_id, str) or not raw_id.startswith('msg'):
                    extra['id'] = f'msg{uuid4().hex}'
                response: ChatMessage = ChatMessage(content=''.join(response_chunks), role=api.bot_role, extra=extra)
                self._latest_response = response
                self._conversation_stream.on_next([*conversation, response])
                observer.on_completed()

            try: return cast(Disposable, api.stream_response(request_context).subscribe(_on_next, _on_error, _on_completed))
            except Exception as error:
                observer.on_error(error)
                return Disposable()

        return cast(Observable[str], reactivex.create(_subscribe))

    def ask(self, message: ChatMessage, settings: ChatRequestSettings | None = None) -> None:
        self.tell(message)
        self.proceed(settings)

    def ask_stream(self, message: ChatMessage, settings: ChatRequestSettings | None = None) -> Observable[str]:
        self.tell(message)
        return self.proceed_stream(settings)

    def ask_with_images(self, message: ChatMessage, image_paths: list[str | Path], settings: ChatRequestSettings | None = None) -> None:
        self.ask(self.attach_images(message, image_paths), settings)

    def ask_with_images_stream(self, message: ChatMessage, image_paths: list[str | Path], settings: ChatRequestSettings | None = None) -> Observable[str]:
        return self.ask_stream(self.attach_images(message, image_paths), settings)

    def get_answer(self) -> ChatMessage:
        if self._latest_response is None: raise RuntimeError('No answer available')
        return self._latest_response.copy()

    def clear_memory(self) -> None:
        self._conversation_stream.on_next([])

    def copy(self) -> ChatBot:
        chat_bot = ChatBot()
        chat_bot._api = self._api
        chat_bot._conversation_stream.on_next(self._conversation_snapshot())
        chat_bot._latest_response = self._latest_response.copy() if self._latest_response is not None else None
        return chat_bot
