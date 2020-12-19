import json
import logging
import math
import numbers
from contextlib import contextmanager
from enum import Enum, auto
from functools import wraps, total_ordering
from itertools import takewhile
from typing import NamedTuple

import trio
from attr import attrs

TWO_PI = math.pi * 2

logger = logging.getLogger(__name__)


DEFAULT_TEXT_FONT = 'Arial'
DEFAULT_TEXT_SIZE = 12
DEFAULT_BACKGROUND_COLOR = 200
DEFAULT_FILL_COLOR = 255


@total_ordering
class KeyboardKey(NamedTuple):  # pylint: disable=inherit-non-class
                                # https://github.com/PyCQA/pylint/issues/3876
    """Represents a keyboard input with modifiers

    Comparison to string is allowed, and simply compares the `key` attribute.

    str() simply returns the `key` attribute
    """
    key: str
    alt_modifier: bool = False
    ctrl_modifier: bool = False
    meta_modifier: bool = False
    shift_modifier: bool = False

    def __eq__(self, other):
        if isinstance(other, str):
            return self.key == other
        # super() cannot be used
        # https://stackoverflow.com/questions/61543768/super-in-a-typing-namedtuple-subclass-fails-in-python-3-8
        return tuple.__eq__(self, other)

    def __lt__(self, other):
        if isinstance(other, str):
            return self.key < other
        return tuple.__lt__(self, other)

    def __str__(self):
        return self.key


@attrs(auto_attribs=True, eq=True, frozen=True, slots=True, init=False)
class Color:
    """
    Color type based on the Processing API.

    input variants:
        gray
        gray, alpha
        non_alpha_color_obj, alpha
        r, g, b
        r, g, b, a

    All channel values are 8-bit unsigned int.
    Like Processing color(), values are immutable.
    As an extension, the raw r/g/b/a channel values are available as attributes.

    TODO: support raw input similar to Processing (e.g. 0xFFCC00)
    TODO: implement colorMode(), red(), green(), etc. functions of Processing
    """

    r: int
    g: int
    b: int
    a: int

    def __init__(self, *args):
        """
        :param arg0: gray or red channel or other color object
        :param arg1: green channel or alpha channel
        :param arg2: blue channel
        :param arg3: alpha channel
        """
        n_args = len(args)
        if not 1 <= n_args <= 4:
            raise ValueError('Unexpected number of arguments to Color()')
        arg0 = args[0]
        a = 255
        if n_args == 1:
            r = g = b = arg0
        elif n_args == 2:
            a = args[1]
            if isinstance(arg0, self.__class__):
                other = arg0
                r, g, b = other.r, other.g, other.b
                a = a * other.a // 255
            else:
                r = g = b = arg0
        elif n_args == 3:
            r, g, b = args
        else:
            r, g, b, a = args
        # __setattr__() must be used to bypass frozen restriction
        for name, val in zip('rgba', (r, g, b, a)):
            object.__setattr__(self, name, val)

    def js_string(self):
        """Returns JavaScript color string"""
        if self.a == 255:
            return '#%02X%02X%02X' % (self.r, self.g, self.b)
        return '#%02X%02X%02X%02X' % (self.r, self.g, self.b, self.a)


class TextAlign(Enum):
    LEFT = 'left'
    RIGHT = 'right'
    CENTER = 'center'


class StrokeCap(Enum):
    ROUND = 'round'
    SQUARE = 'butt'
    PROJECT = 'square'


class _ShapeState(Enum):
    NONE = auto()
    FIRST = auto()
    OPEN = auto()


@attrs(auto_attribs=True)
class Image:
    _base64_str: str


def _canvas_color(*args):
    """Return JS color string given color object or color object init args."""
    if len(args) == 1 and isinstance(args[0], Color):
        return args[0].js_string()
    return Color(*args).js_string()


def queue_eval(func):
    """Decorator taking returned eval and adding to send queue."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        s = func(self, *args, **kwargs)
        assert s.endswith((';', '}'))
        assert self._is_draw_context, 'WebView API used outside of draw() context'
        self._sendQueue.append(s)
        # A terrible hack... since the client must queue commands while an image
        # load is pending, and since commands are batched from our side, it's
        # necessary to force a batch boundary after an image load.  The existence
        # of "isImageLoadPending" indicates such an image load, but this will add
        # unnecessary boundaries due to conditional expressions in the commands.
        # TODO: Use a different approach like command grouping so that the client
        #  understands boundaries regardless of batching.
        if 'isImageLoadPending' in s:
            self._sendQueue.append('')
    return wrapper


def queue_eval_optional(func):
    """Decorator taking returned eval and adding to send queue if in draw context."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self._is_draw_context:
            s = func(self, *args, **kwargs)
            assert s.endswith((';', '}'))
            self._sendQueue.append(s)
    return wrapper


# About client commands
#
# All command strings are JavaScript which are simply eval'd by the client.
# Eval environment:
#
#     available global state:
#         ctx: HTML5 canvas context object for drawing
#         ws_url: base URL of this webview server
#     pura namespace methods:
#         swap() - move hidden canvas (for drawing) to the front
#         add_webview(name, port, width, height) - register the given webview.
#             (For use by main websocket only.)
#
#     See html/js/pura.js for the implementation.

class WebView:
    """Remote visualization agent"""

    def __init__(self, name, *, size, draw_fn, frame_rate=5):
        self.name = name
        self._ctx = DrawContext(size=size, draw_fn=draw_fn, frame_rate=frame_rate)

    @property
    def width(self):
        return self._ctx.width

    @property
    def height(self):
        return self._ctx.height

    async def serve(self, webview_server):
        """Make webview available on the given webview server."""
        await webview_server.add_webview(self.name, self._ctx)
        await self._ctx._run_draw_loop()

    def loadImage(self, base64_str):
        """Returns image reference"""
        return self._ctx.loadImage(base64_str)

    def unloadImage(self, image):
        """Unloads image"""
        return self._ctx.unloadImage(image)


class DrawContext:
    """webview draw context

    Mimics a subset of the Processing Python graphics API.
    Notable differences:

        * there is no setup() hook

        * push/popMatrix() and push/popStyle() are replaced by a single
          pushContext().  Usage "with pushContext(): ...".

        * "special" keyboard keys (arrows, modifiers, etc.) are included
          in the "key" attribute.  There is not a separate keyCode.

        * keyboard input objects are an instance of KeyboardKey, which
          includes modifier information.

        * instead of keyPressed(), mousePressed(), etc. overload methods,
          there is an inputEvents list which contains (event_name, value)
          tuples.  The list is cleared after each frame.

        * Color type is capitalized

        * loadImage() takes inline image (base64 string) rather than file path,
          and the returned image handle is opaque (no fields for width,
          height, etc.).

        * unloadImage() is provided to free sever and client memory if needed.

        * image() accepts inline image (base64 string) in addition to handle
          from loadImage().  Since it the client draw is blocked until the
          image is ready, streaming of image sequences is possible.

        * smooth() takes no argument, and applies only to image() and not to
          other drawing primitives.  Unlike Processing 3, it's bound to the
          draw context.

    inputEvents "event_name: value":
        keydown/keyup: KeyboardKey
        mousedown/mouseup: (x, y)
    """

    # pylint: disable=no-self-use

    def __init__(self, *, size, frame_rate, draw_fn):
        """
        :param size: sequence of width, height
        :param frame_rate: rate of draw calls when the view is active
        :param draw_fn: draw function called each frame when the view is active
        """
        self.width, self.height = size
        self._draw_fn = draw_fn
        self._frame_rate = frame_rate
        self._peers = set()
        self._hasPeers = trio.Event()
        # NOTE: empty string is used to force a batching boundary
        self._sendQueue = []
        self._receiveQueue = []  # oldest to newest
        self._shapeState = _ShapeState.NONE
        self._images = []
        self._is_draw_context = False
        self.frameCount = 0
        self.mousePressed = False
        self.mouseX = 0
        self.mouseY = 0
        self.keyPressed = False
        self.key = ''
        self.inputEvents = []

    @staticmethod
    async def _broadcast(peers, msg):
        """Broadcast message to given clients, ignoring connection errors."""
        for peer in peers:
            await peer.send(msg)

    async def _handleConnected(self, peer):
        # set up canvas defaults, etc.
        await peer.send(
            f"ctx.lineCap = '{StrokeCap.ROUND.value}';"
            f"ctx.font = '{DEFAULT_TEXT_SIZE}px {DEFAULT_TEXT_FONT}';"
            f"ctx.fillStyle = '{_canvas_color(DEFAULT_BACKGROUND_COLOR)}';"
            f"ctx.fillRect(0, 0, {self.width}, {self.height});"
            f"ctx.fillStyle = '{_canvas_color(DEFAULT_FILL_COLOR)}';"
        )
        for image in self._images:
            await peer.send(self._loadImage(id(image), image._base64_str))
        # peer will be included at start of next draw loop
        self._peers.add(peer)
        self._hasPeers.set()

    def _handleClose(self, peer):
        self._peers.remove(peer)
        if not self._peers:
            self._hasPeers = trio.Event()

    async def _handleMessage(self, peer, msg):
        """Process incoming JSON message from webview client."""
        # TODO: only accept input from one webview client
        # queue the message until our next draw iteration
        self._receiveQueue.append(msg)

    def _handleDeferredMessage(self, msg):
        msg = json.loads(msg)
        msg_type = msg['type']
        if msg_type == 'mousemove':
            self.mouseX, self.mouseY = int(msg['x']), int(msg['y'])
        elif msg_type == 'mousedown':
            self.mousePressed = True
            x, y = int(msg['x']), int(msg['y'])
            # TODO: include button ID with mousedown/mouseup
            self.inputEvents.append(('mousedown', (x, y)))
        elif msg_type == 'mouseup':
            self.mousePressed = False
            x, y = int(msg['x']), int(msg['y'])
            self.inputEvents.append(('mouseup', (x, y)))
        elif msg_type == 'mouseout':
            self.mousePressed = False
        elif msg_type == 'dblclick':
            x, y = int(msg['x']), int(msg['y'])
            self.inputEvents.append(('dblclick', (x, y)))
        elif msg_type == 'keydown':
            self.keyPressed = True
            self.key = KeyboardKey(
                key=msg['key_code'],
                alt_modifier=msg['alt_key'],
                ctrl_modifier=msg['ctrl_key'],
                meta_modifier=msg['meta_key'],
                shift_modifier=msg['shift_key']
            )
            self.inputEvents.append(('keydown', self.key))
        elif msg_type == 'keyup':
            self.keyPressed = False
            key = KeyboardKey(
                key=msg['key_code'],
                alt_modifier=msg['alt_key'],
                ctrl_modifier=msg['ctrl_key'],
                meta_modifier=msg['meta_key'],
                shift_modifier=msg['shift_key']
            )
            self.inputEvents.append(('keyup', key))
        else:
            logger.warning(f"unhandled message type: {msg['type']}")

    async def _run_draw_loop(self):
        period = 1 / self._frame_rate
        while True:
            t_start = trio.current_time()
            await self._hasPeers.wait()
            peers = self._peers.copy()
            self.inputEvents.clear()
            for msg in self._receiveQueue:
                self._handleDeferredMessage(msg)
            self._receiveQueue.clear()
            self._is_draw_context = True
            with self.pushContext():
                self._draw_fn(self)
                self._swapBuffer()
            self._is_draw_context = False
            # batch messages to minimize send count
            # honor explicit batch boundaries (empty string)
            # force a break mid-queue to provide some pipelining with client
            if len(self._sendQueue) > 1:
                mid_index = len(self._sendQueue) // 2
                if '' not in self._sendQueue[mid_index-1:mid_index+1]:
                    self._sendQueue.insert(mid_index, '')
            strings_iter = iter(self._sendQueue)
            while True:
                msg = ''.join(takewhile(lambda s: s, strings_iter))
                if msg:
                    await self._broadcast(peers, msg)
                else:
                    break
            self._sendQueue.clear()
            self.frameCount += 1
            user_elapsed = trio.current_time() - t_start
            await trio.sleep(max(0, period - user_elapsed))

    @queue_eval
    def background(self, *args):
        return (
            f"ctx.save();"
            f"ctx.fillStyle = '{_canvas_color(*args)}';"
            f"ctx.fillRect(0, 0, {self.width}, {self.height});"
            f"ctx.restore();"
        )

    @queue_eval
    def _swapBuffer(self):
        return 'pura.swap();'

    @queue_eval
    def strokeWeight(self, x):
        return f"ctx.lineWidth = {x};"

    @queue_eval
    def strokeCap(self, cap: StrokeCap):
        return f"ctx.lineCap = '{cap.value}';"

    @queue_eval
    def stroke(self, *args):
        return f"ctx.strokeStyle = '{_canvas_color(*args)}';"

    def noStroke(self):
        self.stroke(0, 0)

    @queue_eval
    def fill(self, *args):
        return f"ctx.fillStyle = '{_canvas_color(*args)}';"

    def noFill(self):
        self.fill(0, 0)

    @queue_eval
    def translate(self, x, y):
        return f'ctx.translate({x}, {y});'

    @queue_eval
    def rotate(self, a):
        return f'ctx.rotate({a});'

    @queue_eval
    def scale(self, x, y=None):
        if y is None:
            y = x
        return f'ctx.scale({x}, {y});'

    # TODO: support kind option
    # TODO: context manager (Processing.py has beginShape and beginClosedShape)
    @queue_eval
    def beginShape(self):
        assert self._shapeState is _ShapeState.NONE, 'unexpected beginShape()'
        self._shapeState = _ShapeState.FIRST
        return 'ctx.beginPath();'

    @queue_eval
    def endShape(self, close=False):
        assert self._shapeState is _ShapeState.OPEN, 'unexpected endShape()'
        self._shapeState = _ShapeState.NONE
        return ('ctx.closePath();' if close else '') + (
            'ctx.fill();'
            'ctx.stroke();'
        )

    @queue_eval
    def vertex(self, x, y):
        if self._shapeState is _ShapeState.OPEN:
            return f'ctx.lineTo({x}, {y});'
        if self._shapeState is _ShapeState.FIRST:
            self._shapeState = _ShapeState.OPEN
            return f'ctx.moveTo({x}, {y});'
        raise AssertionError('path not open')

    @queue_eval
    def line(self, x1, y1, x2, y2):
        return (
            f'ctx.beginPath();'
            f'ctx.moveTo({x1}, {y1});'
            f'ctx.lineTo({x2}, {y2});'
            f'ctx.stroke();'
        )

    def point(self, x, y):
        return self.line(x, y, x, y)

    # TODO: support corner radius
    # TODO: support rectMode()
    @queue_eval
    def rect(self, a, b, c, d):
        return (
            f'ctx.beginPath();'
            f'ctx.rect({a},{b},{c},{d});'
            f'ctx.fill();'
            f'ctx.stroke();'
        )

    # TODO: support ellipseMode
    def ellipse(self, x, y, w, h):
        return self.arc(x, y, w, h, 0, TWO_PI)

    # TODO: support ellipseMode
    # TODO: support draw mode
    @queue_eval
    def arc(self, x, y, w, h, start, stop):
        if w == h and abs(stop - start) == TWO_PI:
            return (
                f'ctx.beginPath();'
                f'ctx.arc({x},{y},{w/2},{start},{stop});'
                f'ctx.fill();'
                f'ctx.stroke();'
            )
        return (
            f'ctx.beginPath();'
            f'ctx.save();'
            f'ctx.translate({x}, {y});'
            f'ctx.scale({w}, {h});'
            f'ctx.moveTo(0, 0);'
            f'ctx.arc(0, 0, 0.5, {start}, {stop});'
            f'ctx.fill();'
            f'ctx.beginPath();'
            f'ctx.arc(0, 0, 0.5, {start}, {stop});'
            f'ctx.restore();'
            f'ctx.stroke();'
        )

    def _loadImage(self, id_, base64_str):
        return (
            '{'
            'let image = new Image();'
            f'pura.imagesById[{id_}]=image;'
            f'image.src = "data:image/png;base64,{base64_str}";'
            '}'
        )

    @queue_eval_optional
    def _loadImageAllPeers(self, id_, base64_str):
        return self._loadImage(id_, base64_str)

    # TODO: take bytes
    def loadImage(self, base64_str):
        """Returns image reference

        May be called outside of the draw() context.
        """
        image = Image(base64_str)
        self._images.append(image)
        self._loadImageAllPeers(id(image), base64_str)
        return image

    @queue_eval_optional
    def unloadImage(self, image):
        """Unloads image

        May be called outside of the draw() context.
        """
        self._images.remove(image)
        return f'delete pura.imagesById[{id(image)}];'

    @queue_eval
    def image(self, image_or_base64_str, x, y, w=None, h=None):
        """
        image_or_base64_str is either image reference returned from
        loadImage(), or base64 of binary to be used immediately.
        """
        # pylint: disable=line-too-long
        assert w is None and h is None or (w is not None and h is not None)
        size_args = '' if w is None else f', {w}, {h}'
        if isinstance(image_or_base64_str, Image):
            image = image_or_base64_str
            return (
                '{'
                f'let image = pura.imagesById[{id(image)}];'
                f'if (image.complete) ctx.drawImage(image,{x},{y}{size_args});'
                'else {pura.isImageLoadPending = true; image.addEventListener("load", function(){'
                f' ctx.drawImage(image,{x},{y}{size_args});'
                '  pura.isImageLoadPending = false;'
                '  pura.resumeCommands();'
                '});}'                '}'
            )
        base64_str = image_or_base64_str
        return (
            '{'
            'let image = new Image();'
            'pura.isImageLoadPending = true;'
            'image.onload = function(){'
            f' ctx.drawImage(image,{x},{y}{size_args});'
            '  pura.isImageLoadPending = false;'
            '  pura.resumeCommands();'
            '};'
            f'image.src = "data:image/png;base64,{base64_str}";'
            '}'
        )

    @queue_eval
    def text(self, t, x, y):
        if isinstance(t, str):
            pass
        elif isinstance(t, numbers.Number):  # NOTE: this check is relatively slow
            t = str(t)
        else:
            raise TypeError('expected string or number')
        # string repr() should be fine as JavaScript, and is 2x faster than json.dumps()
        return f"ctx.fillText({repr(t)}, {x}, {y});"

    @queue_eval
    def textSize(self, v):
        # e.g. "12px Arial"
        return f"ctx.font = '{v}px ' + ctx.font.split(' ')[1];"

    # TODO: size parameter
    @queue_eval
    def textFont(self, v):
        return f"ctx.font = ctx.font.split(' ')[0] + ' {v}';"

    @queue_eval
    def textAlign(self, align_x: TextAlign):
        return f"ctx.textAlign = '{align_x.value}';"

    @queue_eval
    def smooth(self):
        return 'ctx.imageSmoothingEnabled = true;'

    @queue_eval
    def noSmooth(self):
        # unfortunately there is no way to turn off primitive antialiasing...
        return 'ctx.imageSmoothingEnabled = false;'

    @queue_eval
    def _pushContext(self):
        return 'ctx.save();'

    @queue_eval
    def _popContext(self):
        return 'ctx.restore();'

    @contextmanager
    def pushContext(self):
        self._pushContext()
        yield None
        self._popContext()


class WebViewMixin:
    """Remote visualization mixin

      * the host class inherits a single attribute, `webview`, and
        must implement draw().
      * by default, the webview name is derived from the host class name
      * constructor kwargs that begin with 'webview_' are passed to the
        WebView constructor after removing the prefix

    draw() is only called when there is an active client connection.

    To make the webview available, call obj.webview.serve().
    """

    def __init__(self, **kwargs):
        """
        :param webview_name: display name of the view
        :param webview_size: sequence of width, height
        :param webview_frame_rate: optional rate of draw calls when the
          view is active (default 5)
        """
        webview_kwargs = {k[len('webview_'):]: v for k, v in kwargs.items()
                          if k.startswith('webview_')}
        if webview_kwargs.get('name') is None:
            webview_kwargs['name'] = self.__class__.__name__.split('.')[-1]
        self.webview = WebView(webview_kwargs.pop('name'),
                               draw_fn=self.draw, **webview_kwargs)

    def draw(self, ctx: DrawContext):
        raise NotImplementedError
