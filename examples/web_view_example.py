import math

import trio

from pura import WebView, WebViewServer

PI = math.pi
HALF_PI = PI / 2
QUARTER_PI = PI / 4
TWO_PI = PI * 2

FRAME_RATE = 20
HTTP_PORT = 8080
WEBSOCKET_PORT = 8081
WEBSOCKET2_PORT = 8082


class Clock(WebView):

    def __init__(self):
        super().__init__(frame_rate=FRAME_RATE)
        self.mouse_angle = 0

    def draw(self):
        self.background(200)
        angle = (trio.current_time() % 60) / 60 * (2 * math.pi)
        self.translate(self.width/2, self.height/2)
        with self.pushContext():
            self.translate(-5, -10)
            self.noFill()
            self.stroke(255, 150)
            self.rect(-20, 0, 10, 20)
            self.noStroke()
            self.fill(50, 200, 50, 150)
            self.rect(0, 0, 10, 20)
            self.stroke(255, 150)
            self.rect(20, 0, 10, 20)
        with self.pushContext():
            self.rotate(angle)
            self.strokeWeight(2)
            self.stroke(0)
            self.line(0, 0, 30, 0)
        with self.pushContext():
            self.rotate(angle * 10)
            self.strokeWeight(2.5)
            self.stroke(200, 100, 100)
            for x in range(0, 50, 5):
                self.point(x, 0)
        if self.mousePressed:
            self.mouse_angle = math.atan2(
                self.mouseY-self.height/2, self.mouseX-self.width/2)
        with self.pushContext():
            self.rotate(self.mouse_angle)
            self.stroke(100, 100, 200)
            self.line(0, 0, 40, 0)


class Arcs(WebView):

    def __init__(self):
        super().__init__(frame_rate=FRAME_RATE)

    def draw(self):
        self.background(200)
        with self.pushContext():
            self.translate(self.width * .25, self.height/2)
            self.fill(200, 50, 50)
            self.arc(0, 0, 50, 50, 0, HALF_PI)
            self.noFill()
            self.arc(0, 0, 60, 60, HALF_PI, PI)
            self.arc(0, 0, 70, 70, PI, PI + QUARTER_PI)
            self.arc(0, 0, 80, 80, PI + QUARTER_PI, TWO_PI)
        with self.pushContext():
            self.translate(self.width * .75, self.height/2)
            self.stroke(0)
            self.fill(200, 50, 50)
            self.ellipse(0, -50, 40, 20)
            self.noFill()
            self.ellipse(0, 0, 40, 40)
            self.noStroke()
            self.fill(200, 50, 50)
            self.ellipse(0, 50, 20, 40)


class Shapes(WebView):

    def __init__(self):
        super().__init__(frame_rate=FRAME_RATE)

    def draw(self):
        self.background(200)
        self.strokeWeight(2)

        def shape(close=False):
            self.beginShape()
            self.vertex(30, 20)
            self.vertex(85, 20)
            self.vertex(85, 75)
            self.endShape(close)
            self.point(10, 20)

        with self.pushContext():
            self.translate(self.width * 0.2, self.height * 0.2)
            shape()

        with self.pushContext():
            self.translate(self.width * 0.5, self.height * 0.2)
            shape(close=True)

        with self.pushContext():
            self.noFill()
            self.translate(self.width * 0.2, self.height * 0.6)
            shape()

        with self.pushContext():
            self.noStroke()
            self.translate(self.width * 0.5, self.height * 0.6)
            shape(close=True)


class Images(WebView):

    def __init__(self):
        super().__init__(frame_rate=FRAME_RATE)
        self.img = self.loadImage(
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

    def draw(self):
        self.background(64)
        # pass image binary
        self.image(self.img2_str, 0, self.height - 16)
        # NOTE: Purposely leaving a transform open until the end of draw.
        #   It should not affect render of image() above assuming that the load
        #   and draw context are correctly synchronized.
        X_OFFSET = 50
        self.translate(X_OFFSET, 0)
        # pass image reference - draw enlarged with smoothing disabled, and again animated
        offset = int(math.sin(self.frameCount / 5) * 16)
        self.image(self.img, self.width / 2 + offset, self.height / 2)
        with self.pushContext():
            self.noSmooth()
            self.image(self.img, 0, 0, self.width / 2, self.height / 2)
        # Demonstrate that:
        #   1) image() will wait for pending loadImage()
        #   2) call of unloadImage() immediately after image() is OK
        # (icon will flash for a single frame)
        if self.frameCount % 20 == 0:
            img2 = self.loadImage(self.img2_str)
            self.image(img2, self.width - 16 - X_OFFSET, self.height - 16)
            self.image(img2, self.width - 16 - X_OFFSET, self.height - 16 * 3)
            self.unloadImage(img2)


class Follow3(WebView):

    def __init__(self):
        super().__init__(webview_name='follow3', frame_rate=FRAME_RATE)
        self.segLength = 15
        num_segments = 15
        self.x = [0.0] * num_segments
        self.y = [0.0] * num_segments

    def dragSegment(self, i, xin, yin):
        x, y, segLength = self.x, self.y, self.segLength
        dx = xin - x[i]
        dy = yin - y[i]
        angle = math.atan2(dy, dx)
        x[i] = xin - math.cos(angle) * segLength
        y[i] = yin - math.sin(angle) * segLength
        self.segment(x[i], y[i], angle)

    def segment(self, x, y, a):
        with self.pushContext():
            self.translate(x, y)
            self.rotate(a)
            self.line(0, 0, self.segLength, 0)

    def draw(self):
        self.strokeWeight(9)
        self.stroke(255, 100)
        self.background(0)
        self.dragSegment(0, self.mouseX, self.mouseY)
        x, y = self.x, self.y
        for i in range(len(x) - 1):
            self.dragSegment(i + 1, x[i], y[i])


async def async_main():
    async with trio.open_nursery() as nursery:
        server = WebViewServer()
        await nursery.start(server.serve, "Web view test", 'localhost',
                            HTTP_PORT, WEBSOCKET_PORT)
        nursery.start_soon(Clock()._serve_webview, server, 200, 100)
        nursery.start_soon(Arcs()._serve_webview, server, 320, 240)
        nursery.start_soon(Shapes()._serve_webview, server, 320, 240)

        # Now we'll subscribe clients to an additional webview server
        # (which will be started as another WebViewServer instance below).
        # This will work for servers in another process or machine as well.
        await server.add_remote('localhost', WEBSOCKET2_PORT)

        # NOTE: normally there is no reason to have multiple webview servers
        # in the same process.  This is only to demonstrate add_remote().
        server2 = WebViewServer()
        await nursery.start(server2.serve, "Web view test2", 'localhost',
                            None, WEBSOCKET2_PORT)
        nursery.start_soon(Images()._serve_webview, server2, 320, 240)
        # demonstrate a view being registered late
        await trio.sleep(7)
        nursery.start_soon(Follow3()._serve_webview, server2, 320, 240)


if __name__ == '__main__':
    import logging

    logging.info('')  # why is this needed?
    logging.getLogger().setLevel(logging.INFO)

    try:
        trio.run(async_main)
    except KeyboardInterrupt:
        print()
