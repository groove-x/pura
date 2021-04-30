import logging
from asyncio import CancelledError
from typing import List

import anyio
import hypercorn
import quart
import sniffio

from pura import WebRepl

_logger = logging.getLogger(__name__)


class WebViewServer:
    """Server for web views"""

    def __init__(self):
        self._peers: List[quart.Websocket] = []
        self.webviews = []  # (name, ctx)
        self.remote_webview_servers = []  # url
        # TODO: make a WebsocketHandler mixin, fix naming convention of _handleConnected(), etc.
        self.handlers_by_path = {'_main': self}

    def get_blueprint(self, title):
        blueprint = quart.Blueprint('webviews', __name__,
                                    static_folder='static/')

        @blueprint.route('/')
        async def _index():
            return await quart.render_template('index.html', title=title)

        @blueprint.route('/repl')
        async def _repl():
            return await quart.render_template('repl.html', title=title)

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
                    await handler._handleMessage(websocket, message)
            finally:
                # print(path, 'closed')
                handler._handleClose(websocket)

        return blueprint

    async def serve(self, title, host, port, *,
                    task_status=anyio.TASK_STATUS_IGNORED):
        """Web view server task."""

        # (quart and hypercorn should have a common API for asyncio and trio...)
        async_lib = sniffio.current_async_library()
        if async_lib == 'trio':
            from quart_trio import QuartTrio  # pylint: disable=import-outside-toplevel
            web_app = QuartTrio('pura')
            web_app.register_blueprint(self.get_blueprint(title))
            async with anyio.create_task_group() as tg:
                urls = await tg.start(hypercorn.trio.serve, web_app,
                                      hypercorn.Config.from_mapping(
                                          bind=[f'{host}:{port}'],
                                          loglevel='WARNING',
                                      ))
                _logger.info(f'listening on {urls[0]}')
                task_status.started()
        elif async_lib == 'asyncio':
            web_app = quart.Quart('pura')
            web_app.register_blueprint(self.get_blueprint(title))
            task_status.started()
            await hypercorn.asyncio.serve(web_app,
                                          hypercorn.Config.from_mapping(
                                              bind=[f'{host}:{port}'],
                                              loglevel='INFO',
                                              graceful_timeout=.2,
                                          ))
            raise CancelledError
        else:
            raise RuntimeError('unsupported async library:', async_lib)

    @staticmethod
    def _add_webview_message(name, ctx):
        display_name = getattr(ctx, 'display_name', '')
        link_url = getattr(ctx, 'link_url', '')
        return f'pura.add_webview(ws_url,"{name}",{ctx.width},{ctx.height},' \
               f'"{display_name}","{link_url}");'

    # TODO: support unregistering views
    async def add_webview(self, name, ctx):
        assert name not in self.handlers_by_path
        self.handlers_by_path[name] = ctx
        self.webviews.append((name, ctx))
        await self._sendAllPeers(self._add_webview_message(name, ctx))

    async def add_repl(self, repl: WebRepl):
        # on the main webview page, selecting the REPL will open a link
        # TODO: get websocket and http paths from server config
        repl.display_name = 'REPL (new window)'
        repl.link_url = '/repl'
        await self.add_webview('repl', repl)

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
        # TODO: reload client on version mismatch of HTML/JS resources
        self._peers.append(peer)
        for name, ctx in self.webviews:
            await peer.send(
                self._add_webview_message(name, ctx))
        for url in self.remote_webview_servers:
            await peer.send(self._add_remote_message(url))

    def _handleClose(self, peer: quart.Websocket):
        self._peers.remove(peer)

    async def _handleMessage(self, peer: quart.Websocket, msg):
        """Process incoming JSON message from client."""
        #msg_type = msg['type']
        #logger.warning(f"unhandled message type: {msg['type']}")
