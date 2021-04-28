import logging
from typing import List

import hypercorn
import quart
import trio
from quart_trio import QuartTrio

_logger = logging.getLogger(__name__)


class WebViewServer:
    """Server for web views"""

    def __init__(self):
        self._peers: List[quart.Websocket] = []
        self.webviews = []
        self.remote_webview_servers = []  # (host, port)
        self.handlers_by_path = {}

    async def serve(self, title, host, port, *,
                    task_status=trio.TASK_STATUS_IGNORED):
        """Web view server task."""

        web_app = QuartTrio('pura')

        @web_app.route('/')
        async def _index():
            return await quart.render_template('index.html', title=title)

        @web_app.route('/js/<path:path>')
        async def _js(path):
            return await web_app.send_static_file(f'js/{path}')

        @web_app.websocket('/ws/<path:path>', endpoint='root-ws')
        async def _ws_connect(path):
            websocket: quart.Websocket = quart.websocket._get_current_object()

            path = websocket.full_path
            # print(path, 'connected')
            handler = self.handlers_by_path.get(path)
            if handler is None:
                _logger.warning('webview server: no handler for path "%s"', path)
                # TODO: close websocket with error (https://gitlab.com/pgjones/quart/-/issues/383)
                #await websocket.accept()
                #await websocket.close(1008, reason=f'path "{path}" not found')
                return
            # TODO: handle closed connection silently?  But quart-trio gives us no way to
            #   discern, see https://gitlab.com/pgjones/quart-trio/-/issues/19#note_496172565.
            await handler._handleConnected(websocket)

            try:
                while True:
                    message = await websocket.receive()
                    # print(path, 'received', message)
                    handler._handleMessage(message)
            finally:
                # print(path, 'closed')
                handler._handleClose(websocket)

        async with trio.open_nursery() as nursery:
            self.handlers_by_path['/ws/main'] = self
            urls = await nursery.start(hypercorn.trio.serve, web_app,
                                       hypercorn.Config.from_mapping(
                                           bind=[f'{host}:{port}'],
                                           loglevel='WARNING',
                                       ))
            _logger.info(f'listening on {urls[0]}')
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
    def _add_remote_message(host, port):
        if host:
            param = f'"ws://{host}:{port}/ws/"'
        else:
            # replace port in the client-side URL
            param = f'ws_url.replace(/:[0-9]+[/]/,":{port}/")'
        return f'pura.webview_server_subscribe({param});'

    async def add_remote(self, host, port):
        """
        Make a remote webview server's views available to clients of this server

        :param host: remote webview server host (None for same host)
        :param port: remote webview server port
        """
        self.remote_webview_servers.append((host, port))
        await self._sendAllPeers(self._add_remote_message(host, port))

    # TODO: shared with WebView-- move these methods to a base class
    async def _sendAllPeers(self, msg):
        for peer in self._peers:
            await peer.send(msg)

    async def _handleConnected(self, peer: quart.Websocket):
        self._peers.append(peer)
        for webview, width, height in self.webviews:
            await peer.send(
                self._add_webview_message(webview, width, height))
        for host, port in self.remote_webview_servers:
            await peer.send(self._add_remote_message(host, port))

    def _handleClose(self, peer: quart.Websocket):
        self._peers.remove(peer)

    def _handleMessage(self, msg):
        """Process incoming JSON message from client."""
        #msg_type = msg['type']
        #logger.warning(f"unhandled message type: {msg['type']}")
