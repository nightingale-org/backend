from __future__ import annotations

import socketio

from rodi import Services


class AsyncSocketIOServer(socketio.AsyncServer):
    services: Services

    def __init__(
        self,
        client_manager=None,
        logger=False,
        json=None,
        async_handlers=True,
        namespaces=None,
        **kwargs,
    ):
        super().__init__(
            client_manager=client_manager,
            logger=logger,
            json=json,
            async_handlers=async_handlers,
            namespaces=namespaces,
            **kwargs,
        )
