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
        self.webviews = []  # (name, ctx)
        self.remote_webview_servers = []  # url
        self.handlers_by_path = {'main': self}

    def get_blueprint(self, title):
        blueprint = quart.Blueprint('webviews', __name__,
                                    static_folder='static/')

        @blueprint.route('/')
        async def _index():
            return await quart.render_template('index.html', title=title)

        @blueprint.route('/js/<path:path>')
        async def _js(path):
            return await blueprint.send_static_file(f'js/{path}')

        @blueprint.websocket('/<path:path>')
        async def _ws(path):
            websocket: quart.Websocket = quart.websocket._get_current_object()

            # print(path, 'connected')
            handler = self.handlers_by_path.get(path)
            if handler is None:
                full_path = websocket.full_path
                _logger.warning('webview server: no handler for path "%s"', full_path)
                # TODO: close websocket with error (https://gitlab.com/pgjones/quart/-/issues/383)
                #await websocket.accept()
                #await websocket.close(1008, reason=f'path "{full_path}" not found')
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

        return blueprint

    async def serve(self, title, host, port, *,
                    task_status=trio.TASK_STATUS_IGNORED):
        """Web view server task."""

        web_app = QuartTrio('pura')
        web_app.register_blueprint(self.get_blueprint(title))
        async with trio.open_nursery() as nursery:
            urls = await nursery.start(hypercorn.trio.serve, web_app,
                                       hypercorn.Config.from_mapping(
                                           bind=[f'{host}:{port}'],
                                           loglevel='WARNING',
                                       ))
            _logger.info(f'listening on {urls[0]}')
            task_status.started()

    @staticmethod
    def _add_webview_message(name, ctx):
        return f'pura.add_webview(ws_url,"{name}",{ctx.width},{ctx.height});'

    # TODO: support unregistering views
    async def add_webview(self, name, ctx):
        path = f'{name}'
        assert path not in self.handlers_by_path
        self.handlers_by_path[path] = ctx
        self.webviews.append((name, ctx))
        await self._sendAllPeers(
            self._add_webview_message(name, ctx))

    @staticmethod
    def _add_remote_message(url):
        return f'pura.webview_server_subscribe({repr(url)});'

    async def add_remote(self, url):
        """
        Make a remote webview server's views available to clients of this server

        :param url: remote webviews URL
        """
        self.remote_webview_servers.append(url)
        await self._sendAllPeers(self._add_remote_message(url))

    # TODO: shared with WebView-- move these methods to a base class
    async def _sendAllPeers(self, msg):
        for peer in self._peers:
            await peer.send(msg)

    async def _handleConnected(self, peer: quart.Websocket):
        self._peers.append(peer)
        for name, ctx in self.webviews:
            await peer.send(
                self._add_webview_message(name, ctx))
        for url in self.remote_webview_servers:
            await peer.send(self._add_remote_message(url))

    def _handleClose(self, peer: quart.Websocket):
        self._peers.remove(peer)

    def _handleMessage(self, msg):
        """Process incoming JSON message from client."""
        #msg_type = msg['type']
        #logger.warning(f"unhandled message type: {msg['type']}")
