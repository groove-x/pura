import logging
from functools import partial

import trio
from trio_websocket import (ConnectionClosed, serve_websocket,
                            WebSocketRequest)

logger = logging.getLogger(__name__)


# TODO: abstract base class for sub-handlers
async def websocket_handler(request: WebSocketRequest,
                            handlers_by_path=None):
    """Dispatches websocket events by path."""

    websocket = await request.accept()
    path = websocket.path
    # print(path, 'connected')
    handler = handlers_by_path.get(path)
    if handler is None:
        logger.warning('webview server: no handler for path "%s"', path)
        await websocket.aclose(1008, f'path "{path}" not found')
        return
    await handler._handleConnected(websocket)

    while True:
        try:
            message = await websocket.get_message()
            # print(path, 'received', message)
            handler._handleMessage(message)
        except (ConnectionClosed, trio.BrokenResourceError):
            # print(path, 'closed')
            handler._handleClose(websocket)
            break


async def run_websocket_server(host, port, handlers_by_path, *,
                               task_status=trio.TASK_STATUS_IGNORED):
    handler = partial(websocket_handler, handlers_by_path=handlers_by_path)
    await serve_websocket(handler, host, port, ssl_context=None,
                          task_status=task_status)


def websocket_normal_closure_filter(exc):
    """
    Trio MultiError filter for trio_websocket.ConnectionClosed with
    NORMAL_CLOSURE code.
    """
    if isinstance(exc, ConnectionClosed) and \
            exc.reason.code == 1000: # NORMAL_CLOSURE
        return None
    return exc
