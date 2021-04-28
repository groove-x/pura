[![Build status](https://img.shields.io/circleci/build/github/groove-x/pura)](https://circleci.com/gh/groove-x/pura)

# pura - the little async embedded visualization framework that could

Pura is a simple embedded visualization framework inspired by the
Processing API and based on the python-trio async/await event loop.

During development it's productive to have visualizations that let
you see and alter the internal state of your program.  Pura lets
you create these easily along side your regular code, and view them
remotely from a web browser.  This is especially useful when the device
running your Python program doesn't otherwise have a display.

Points:
 * a program can register one or more animated graphical views
 * views are coded using a subset of the [Processing API](https://py.processing.org/reference/)
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
[python-trio](https://github.com/python-trio/trio) async/await event loop.

Add visualizations to your program by inheriting from `WebViewMixin`
and implementing the `draw()` method.

At the top level of your program, launch the web view server and
register your class instances.

```python
from pura import WebViewMixin, WebViewServer
import trio

class Foo(WebViewMixin):
    def __init__(self):
        super().__init__(webview_size=(320, 240))

    def draw(self, ctx):
        ctx.background(0)
        ctx.line(0, 0, ctx.width, ctx.height)
        ...

...

foo = Foo()
server = WebViewServer()
async with trio.open_nursery() as nursery:
    await nursery.start(server.serve, "Web view server", 'localhost', 8080)
    nursery.start_soon(foo.webview.serve, server)
```

See the project [`examples/`](examples/) directory, as well as the
`WebView` and `WebViewMixin` class documentation.

Note that, since it's unlikely that Pura can be used as-is in another
project, the package has not been released to pypi.  Please file an
issue if you believe otherwise.

## Disclaimer

Pura is shared as a proof of concept.  It is intended to be used over a
trusted network to visualize and alter the internal state of a program
during development.  The web client is implemented via eval of
JavaScript received over HTTP from the server.

This software is not supported by GROOVE X, Inc., and GROOVE X
specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
