import asyncio
import logging
import socket
import sys
from ssl import SSLContext
from typing import Union, Awaitable, Optional, Callable, Type

from aiohttp.abc import Application, AbstractAccessLogger
from aiohttp.log import access_logger
from aiohttp.web import _run_app
from aiohttp.web_log import AccessLogger
from aiohttp.web_runner import GracefulExit


def run_app(app: Union[Application, Awaitable[Application]], *,
            host: Optional[str] = None,
            port: Optional[int] = None,
            path: Optional[str] = None,
            sock: Optional[socket.socket] = None,
            shutdown_timeout: float = 60.0,
            ssl_context: Optional[SSLContext] = None,
            print: Callable[..., None] = print,
            backlog: int = 128,
            access_log_class: Type[AbstractAccessLogger] = AccessLogger,
            access_log_format: str = AccessLogger.LOG_FORMAT,
            access_log: Optional[logging.Logger] = access_logger,
            handle_signals: bool = True,
            reuse_address: Optional[bool] = None,
            reuse_port: Optional[bool] = None) -> None:
    """Run an app locally"""
    loop = asyncio.get_event_loop()

    # Configure if and only if in debugging mode and using the default logger
    if loop.get_debug() and access_log and access_log.name == 'aiohttp.access':
        if access_log.level == logging.NOTSET:
            access_log.setLevel(logging.DEBUG)
        if not access_log.hasHandlers():
            access_log.addHandler(logging.StreamHandler())

    main = loop.create_task(_run_app(app,
                                     host=host,
                                     port=port,
                                     path=path,
                                     sock=sock,
                                     shutdown_timeout=shutdown_timeout,
                                     ssl_context=ssl_context,
                                     print=print,
                                     backlog=backlog,
                                     access_log_class=access_log_class,
                                     access_log_format=access_log_format,
                                     access_log=access_log,
                                     handle_signals=handle_signals,
                                     reuse_address=reuse_address,
                                     reuse_port=reuse_port))
    try:
        loop.run_until_complete(main)
    except (GracefulExit, KeyboardInterrupt):  # pragma: no cover
        pass
    finally:
        main.cancel()
        loop.run_until_complete(main)
        if sys.version_info >= (3, 6):
            loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
