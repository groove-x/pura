import argparse

import anyio

from pura import WebViewServer, WebRepl

HOST = "localhost"
HTTP_PORT = 8080


class Counter:
    def __init__(self):
        self.count = 0

    async def _run(self):
        while True:
            self.count += 1
            await anyio.sleep(0.5)

    def increment_by(self, value):
        self.count += value


async def main():
    async with anyio.create_task_group() as tg:
        counter = Counter()
        tg.start_soon(counter._run)
        webview_server = WebViewServer()
        await tg.start(webview_server.serve, "WebRepl test", HOST, HTTP_PORT)
        await webview_server.add_repl(WebRepl(dict(
            counter=counter,
            some_variable='hello',
        )))
        print(f"REPL is running at http://{HOST}:{HTTP_PORT}/repl")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='web repl example')
    parser.add_argument('--async-backend', default='asyncio', choices=['ayncio', 'trio'])
    args = parser.parse_args()
    try:
        anyio.run(main, backend=args.async_backend)
    except KeyboardInterrupt:
        print()
