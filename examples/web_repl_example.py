import trio

from pura import WebViewServer, WebRepl

HOST = "localhost"
HTTP_PORT = 8080


class Counter:
    def __init__(self):
        self.count = 0

    async def _run(self):
        while True:
            self.count += 1
            await trio.sleep(0.5)

    def increment_by(self, value):
        self.count += value


async def main():
    async with trio.open_nursery() as nursery:
        counter = Counter()
        nursery.start_soon(counter._run)
        webview_server = WebViewServer()
        await nursery.start(webview_server.serve, "WebRepl test", HOST, HTTP_PORT)
        await webview_server.add_repl(WebRepl(dict(
            counter=counter,
            some_variable='hello',
        )))
        print(f"REPL is running at http://{HOST}:{HTTP_PORT}/repl")


if __name__ == "__main__":
    try:
        trio.run(main)
    except KeyboardInterrupt:
        print()
