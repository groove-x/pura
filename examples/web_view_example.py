import logging
import math

import trio

from pura import WebViewServer, WebViewMixin, TextAlign

PI = math.pi
HALF_PI = PI / 2
QUARTER_PI = PI / 4
TWO_PI = PI * 2

DEFAULT_SIZE = (320, 240)
FRAME_RATE = 20
PORT = 8080
PORT2 = 8081


_logger = logging.getLogger(__name__)


def _setup_logging():
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
    _logger.addHandler(ch)
    _logger.setLevel(logging.INFO)
    _pura_logger = logging.getLogger('pura')
    _pura_logger.addHandler(ch)
    _pura_logger.setLevel(logging.INFO)


class Clock(WebViewMixin):

    def __init__(self):
        super().__init__(webview_size=DEFAULT_SIZE, webview_frame_rate=FRAME_RATE)
        self.mouse_angle = 0

    def draw(self, ctx):
        ctx.background(200)
        angle = (trio.current_time() % 60) / 60 * (2 * math.pi)
        ctx.translate(ctx.width/2, ctx.height/2)
        ctx.scale(2)
        with ctx.pushContext():
            ctx.translate(-5, -10)
            ctx.noFill()
            ctx.stroke(255, 150)
            ctx.rect(-20, 0, 10, 20)
            ctx.noStroke()
            ctx.fill(50, 200, 50, 150)
            ctx.rect(0, 0, 10, 20)
            ctx.stroke(255, 150)
            ctx.rect(20, 0, 10, 20)
        with ctx.pushContext():
            ctx.rotate(angle)
            ctx.strokeWeight(2)
            ctx.stroke(0)
            ctx.line(0, 0, 30, 0)
        with ctx.pushContext():
            ctx.rotate(angle * 10)
            ctx.strokeWeight(2.5)
            ctx.stroke(200, 100, 100)
            for x in range(0, 50, 5):
                ctx.point(x, 0)
        if ctx.mousePressed:
            self.mouse_angle = math.atan2(
                ctx.mouseY-ctx.height/2, ctx.mouseX-ctx.width/2)
        with ctx.pushContext():
            ctx.rotate(self.mouse_angle)
            ctx.stroke(100, 100, 200)
            ctx.line(0, 0, 40, 0)


class Arcs(WebViewMixin):

    def __init__(self):
        super().__init__(webview_size=DEFAULT_SIZE, webview_frame_rate=FRAME_RATE)

    def draw(self, ctx):
        ctx.background(200)
        with ctx.pushContext():
            ctx.translate(ctx.width * .25, ctx.height/2)
            ctx.fill(200, 50, 50)
            ctx.arc(0, 0, 50, 50, 0, HALF_PI)
            ctx.noFill()
            ctx.arc(0, 0, 60, 60, HALF_PI, PI)
            ctx.arc(0, 0, 70, 70, PI, PI + QUARTER_PI)
            ctx.arc(0, 0, 80, 80, PI + QUARTER_PI, TWO_PI)
        with ctx.pushContext():
            ctx.translate(ctx.width * .75, ctx.height/2)
            ctx.stroke(0)
            ctx.fill(200, 50, 50)
            ctx.ellipse(0, -50, 40, 20)
            ctx.noFill()
            ctx.ellipse(0, 0, 40, 40)
            ctx.noStroke()
            ctx.fill(200, 50, 50)
            ctx.ellipse(0, 50, 20, 40)


class Shapes(WebViewMixin):

    def __init__(self):
        super().__init__(webview_size=DEFAULT_SIZE, webview_frame_rate=FRAME_RATE)

    def draw(self, ctx):
        ctx.background(200)
        ctx.strokeWeight(2)

        def shape(close=False):
            ctx.beginShape()
            ctx.vertex(30, 20)
            ctx.vertex(85, 20)
            ctx.vertex(85, 75)
            ctx.endShape(close)
            ctx.point(10, 20)

        with ctx.pushContext():
            ctx.translate(ctx.width * 0.2, ctx.height * 0.2)
            shape()

        with ctx.pushContext():
            ctx.translate(ctx.width * 0.5, ctx.height * 0.2)
            shape(close=True)

        with ctx.pushContext():
            ctx.noFill()
            ctx.translate(ctx.width * 0.2, ctx.height * 0.6)
            shape()

        with ctx.pushContext():
            ctx.noStroke()
            ctx.translate(ctx.width * 0.5, ctx.height * 0.6)
            shape(close=True)


class Images(WebViewMixin):

    def __init__(self):
        super().__init__(webview_size=DEFAULT_SIZE, webview_frame_rate=FRAME_RATE)
        self.img = self.webview.loadImage(
            'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAhFBMVEUAAAD/nSTzgC'
            'PvhiH1gCP0gCP1gCP0gCT1gCT0gCT0gCTzgCP1gSP3gSL0gCT0gCP0gCT0gCT1gCT0'
            'gCP0gCP1gCT0gCP1gCT0gCLxgSPzgib0gCT0gCT0gCP1gCT0gST1gCL1gST3hCH0gC'
            'T0gCT0gCTzgCX0gCTygib0gCD0gCSeo6kZh+EYAAAAKnRSTlMAAygP27ZJ+PPuf1ZQ'
            'HfDo5MfCvJ2ViGgsIxOjjm5iWjQxCtPPza54PRj8fiS7AAAA1klEQVQ4y82Rx3LDMA'
            'wFSUqiem+RnLilr////0Ll4sQinRkfMt4DDsDO8BEQd8q+frg692J876qRQSBdQ6lM'
            'SWBwCX04GiuA1D7PS9gchecTOYJ+NvCshCrwZ0eIAYp0Cdqug+700stieJSJKbYFPJ'
            'kNTC/Q5G/ReCmoBoh6JY4dlHoSaw5dCARabsMqF1bmpALz0ofll3qnlowyrYF3saaF'
            'qO63Byn2m9J2raDgm/C1GyfHodKhjVnQl7PT6XyOLAmq2XRswhmbwA9uEn5xg2Dhb+'
            'G/+ALnoh6c8vTisQAAAABJRU5ErkJggg=='
        )
        self.img2_str = (
            'AAABAAEAEBAQAAEABAAoAQAAFgAAACgAAAAQAAAAIAAAAAEABAAAAAAAgAAAAAAAAA'
            'AAAAAAEAAAAAAAAADV09IA1dXVANx5OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
            'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAERERERERERERESIiIiIRERERIiIiIh'
            'EREREiIiIiERERESIiIiIRERERIiIiIhEREREiIiIiERERESIiIiIRERERIiIiIhER'
            'ERESEREgERERERIRESEREREREiESIRERERERIiIRERERERERERERERERERERERERER'
            'EREREREREAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
            'AAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        )

    def draw(self, ctx):
        ctx.background(64)
        # pass image binary
        ctx.image(self.img2_str, 0, ctx.height - 16)
        # NOTE: Purposely leaving a transform open until the end of draw.
        #   It should not affect render of image() above assuming that the load
        #   and draw context are correctly synchronized.
        X_OFFSET = 50
        ctx.translate(X_OFFSET, 0)
        # pass image reference - draw enlarged with smoothing disabled, and again animated
        offset = int(math.sin(ctx.frameCount / 5) * 16)
        ctx.image(self.img, ctx.width / 2 + offset, ctx.height / 2)
        with ctx.pushContext():
            ctx.noSmooth()
            ctx.image(self.img, 0, 0, ctx.width / 2, ctx.height / 2)
        # Demonstrate that:
        #   1) image() will wait for pending loadImage()
        #   2) call of unloadImage() immediately after image() is OK
        # (icon will flash for a single frame)
        if ctx.frameCount % 20 == 0:
            img2 = ctx.loadImage(self.img2_str)
            ctx.image(img2, ctx.width - 16 - X_OFFSET, ctx.height - 16)
            ctx.image(img2, ctx.width - 16 - X_OFFSET, ctx.height - 16 * 3)
            ctx.unloadImage(img2)


class Words(WebViewMixin):
    """Based on Processing "Words" example"""

    def __init__(self):
        super().__init__(webview_size=(640, 360), webview_frame_rate=FRAME_RATE)

    def draw(self, ctx):
        ctx.background(102)
        ctx.textFont('Georgia')
        ctx.textSize(24)
        ctx.textAlign(TextAlign.RIGHT)
        self.drawType(ctx, ctx.width * 0.25)
        ctx.textAlign(TextAlign.CENTER)
        self.drawType(ctx, ctx.width * 0.5)
        ctx.textAlign(TextAlign.LEFT)
        self.drawType(ctx, ctx.width * 0.75)

    @staticmethod
    def drawType(ctx, x):
        ctx.line(x, 0, x, 65)
        ctx.line(x, 290, x, ctx.height)
        ctx.fill(0)
        ctx.text("ichi", x, 95)
        ctx.fill(51)
        ctx.text("ni", x, 130)
        ctx.fill(204)
        ctx.text("san", x, 165)
        ctx.fill(255)
        ctx.text("shi", x, 210)
        # test quote escaping
        ctx.text("'\"`", x, 245)
        # test number type
        ctx.text(1.23, x, 280)


class Follow3(WebViewMixin):
    """Based on Processing "Follow3" example"""

    def __init__(self):
        super().__init__(webview_size=DEFAULT_SIZE, webview_frame_rate=FRAME_RATE)
        self.segLength = 15
        num_segments = 15
        self.x = [0.0] * num_segments
        self.y = [0.0] * num_segments

    def dragSegment(self, ctx, i, xin, yin):
        x, y, segLength = self.x, self.y, self.segLength
        dx = xin - x[i]
        dy = yin - y[i]
        angle = math.atan2(dy, dx)
        x[i] = xin - math.cos(angle) * segLength
        y[i] = yin - math.sin(angle) * segLength
        self.segment(ctx, x[i], y[i], angle)

    def segment(self, ctx, x, y, a):
        with ctx.pushContext():
            ctx.translate(x, y)
            ctx.rotate(a)
            ctx.line(0, 0, self.segLength, 0)

    def draw(self, ctx):
        ctx.strokeWeight(9)
        ctx.stroke(255, 100)
        ctx.background(0)
        self.dragSegment(ctx, 0, ctx.mouseX, ctx.mouseY)
        x, y = self.x, self.y
        for i in range(len(x) - 1):
            self.dragSegment(ctx, i + 1, x[i], y[i])


async def async_main():
    async with trio.open_nursery() as nursery:
        server = WebViewServer()
        await nursery.start(server.serve, "Web view test", 'localhost', PORT)
        for cls in (Clock, Arcs, Shapes, Words):
            nursery.start_soon(cls().webview.serve, server)

        # Now we'll subscribe clients to an additional webview server
        # (which will be started as another WebViewServer instance below).
        # This will work for servers in another process or machine as well.
        await server.add_remote('localhost', PORT2)

        # NOTE: normally there is no reason to have multiple webview servers
        # in the same process.  This is only to demonstrate add_remote().
        server2 = WebViewServer()
        await nursery.start(server2.serve, "Web view test2", 'localhost', PORT2)
        for cls in (Images, Follow3):
            nursery.start_soon(cls().webview.serve, server2)
            # demonstrate a view being registered late
            await trio.sleep(7)

if __name__ == '__main__':
    _setup_logging()
    try:
        trio.run(async_main)
    except KeyboardInterrupt:
        print()
