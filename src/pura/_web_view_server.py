import logging
import pathlib
from functools import partial
from string import Template
from http import HTTPStatus

import h11
import trio
from trio_websocket import ConnectionClosed

from . import _http_server
from ._websocket_server import run_websocket_server

logger = logging.getLogger(__name__)


def local_to_abs_path(path):
    """Returns absolute path given script-local path."""
    parent = pathlib.Path(__file__).parent
    return parent / path


HTML_PATH = local_to_abs_path('html/')


# TODO: run HTTP and websocket on the same port
async def http_request_handler(server, request, *, title=None,
                               http_port=None, ws_port=None):
    target = request.target.decode('ascii')
    request_body = ''
    async for part in _http_server.receive_body(server):
        request_body += part  # pylint: disable=consider-using-join
    if target == '/':
        path = trio.Path(HTML_PATH / 'index.html')
        template = Template(await path.read_text())
        body = template.substitute(
            title=title, ws_url_path='/ws/',
            http_port=http_port, ws_port=ws_port)
        await _http_server.send_simple_response(
            server, int(HTTPStatus.OK), 'text/html; charset=utf-8',
            body.encode('utf-8'))
    elif target == '/js/pura.js':
        path = trio.Path(HTML_PATH / target.lstrip('/'))
        body = await path.read_text()
        await _http_server.send_simple_response(
            server, int(HTTPStatus.OK), 'application/javascript; charset=utf-8',
            body.encode('utf-8'))
    else:
        raise h11.RemoteProtocolError(
            f'{target} not found', int(HTTPStatus.NOT_FOUND))


class WebViewServer:
    """Server for web views"""

    def __init__(self):
        self._peers = []
        self.webviews = []
        self.remote_webview_servers = []  # (host, ws_port)
        self.handlers_by_path = {}

    async def serve(self, title, host, http_port, ws_port, *,
                    task_status=trio.TASK_STATUS_IGNORED):
        """Web view server task."""
        async with trio.open_nursery() as nursery:
            if http_port:
                # HTTP server
                http_handler = partial(
                    http_request_handler, title=title, http_port=http_port,
                    ws_port=ws_port)
                http_serve = partial(
                    _http_server.http_serve, request_handler=http_handler,
                    debug=False)
                logger.info(f'listening on http://{host}:{http_port}')
                await nursery.start(
                    partial(trio.serve_tcp, http_serve, http_port, host=host))

            # websocket server
            self.handlers_by_path['/ws/main'] = self
            await nursery.start(run_websocket_server, host, ws_port,
                                self.handlers_by_path)
            task_status.started()

    @staticmethod
    def _add_webview_message(webview, width, height):
        return f'pura.add_webview(ws_url,"{webview._webview_name}",{width},{height});'

    async def add_webview(self, webview, width, height):
        path = f'/ws/{webview._webview_name}'
        assert path not in self.handlers_by_path
        self.handlers_by_path[path] = webview
        self.webviews.append((webview, width, height))
        await self._sendAllPeers(
            self._add_webview_message(webview, width, height))

    @staticmethod
    def _add_remote_message(host, ws_port):
        if host:
            param = f'"ws://{host}:{ws_port}/ws/"'
        else:
            # replace port in the client-side URL
            param = f'ws_url.replace(/:[0-9]+[/]/,":{ws_port}/")'
        return f'pura.webview_server_subscribe({param});'

    async def add_remote(self, host, ws_port):
        """
        Make a remote webview server's views available to clients of this server

        :param host: remote webview server host (None for same host)
        :param ws_port: remote webview server websocket port
        """
        self.remote_webview_servers.append((host, ws_port))
        await self._sendAllPeers(self._add_remote_message(host, ws_port))

    # TODO: shared with WebView-- move these methods to a base class
    async def _sendAllPeers(self, msg):
        for peer in self._peers:
            try:
                await peer.send_message(msg)
            except (ConnectionClosed, trio.BrokenResourceError):
                pass

    async def _handleConnected(self, peer):
        self._peers.append(peer)
        for webview, width, height in self.webviews:
            await peer.send_message(
                self._add_webview_message(webview, width, height))
        for host, ws_port in self.remote_webview_servers:
            await peer.send_message(self._add_remote_message(host, ws_port))

    def _handleClose(self, peer):
        self._peers.remove(peer)

    def _handleMessage(self, msg):
        """Process incoming JSON message from client."""
        #msg_type = msg['type']
        #logger.warning(f"unhandled message type: {msg['type']}")
