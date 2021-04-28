"""remote visualization framework

Summary of important webview classes:

  * WebViewMixin - inheriting from this class provides a WebView instance
    (the `webview` attribute) and requires implementing a draw() method.

  * WebView - the webview instance, including metadata such as the view name.
    It provides the serve() function and a few graphical functions that can be
    called outside of the draw context.

  * DrawContext - this context is passed to the draw() function and mimics the
    Processing graphics API.

  * WebViewServer - provides a networking endpoint for webview clients and
    routes connections to the corresponding views.

Be sure to check the documentation of each class.
"""

from ._version import __version__
from ._web_view import WebView, WebViewMixin, DrawContext, Color, KeyboardKey, TextAlign, StrokeCap
from ._web_view_server import WebViewServer
