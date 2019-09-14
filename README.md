[![Build status](https://img.shields.io/circleci/build/github/groove-x/pura)](https://circleci.com/gh/groove-x/pura)

# pura - the little async embedded visualization framework that could

Pura is a simple embedded visualization framework inspired by the
Processing API and based on the python-trio async/await event loop.

Points:
 * a program can register one or more animated graphical views
 * views are written in a subset of the [Processing API](https://py.processing.org/reference/)
 * views can be observed over HTTP by one or more browser clients
 * views have no overhead unless there is a remote client specifically observing it
 * keyboard and mouse input is supported

The example in action:

![Demo video](docs/pura_demo.gif)

## Installation

```shell
git clone https://github.com/groove-x/pura.git
cd pura
pip install -e .
```

## Run the example

```
python examples/web_view_example.py
```
Then connect at http://localhost:8080/

## Using pura in your own project

Pura requires that your program be running under the
[python-trio](https://github.com/python-trio/trio) async/await eval loop.

Add visualizations to your program by inheriting from `WebView`
and implementing a `draw()` method.

From your main program, launch the web view server and register your
class instances.

```python
from pura import WebView, WebViewServer
import trio

Foo(WebView):
    def draw(self):
        self.background(0)
        ...

...

HTTP_PORT = 8080
WEBSOCKET_PORT = 8081
foo = Foo()
server = WebViewServer()
async with trio.open_nursery() as nursery:
    await nursery.start(server.serve, "Web view server", 'localhost',
                        HTTP_PORT, WEBSOCKET_PORT)
    nursery.start_soon(foo._serve_webview, server, 320, 240)
```

See the project [`examples/`](examples/) directory, as well as documentation on the
WebView class.

## Disclaimer

Pura is shared as a proof of concept.  It is intended to be used over a
trusted network to visualize and alter the internal state of a program
during development.  The web client is implemented via eval of
JavaScript received over HTTP from the server.

This software is not supported by GROOVE X, Inc., and GROOVE X
specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
