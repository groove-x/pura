import code
import json
import re
import rlcompleter
import sys
from itertools import count
from typing import Union

import quart

_NON_IDENTIFIER_PATTERN = r"[^a-zA-Z0-9._]+"


class _Completer(rlcompleter.Completer):
    """Completer that gives suggestions for the right-most
    identifier in a string. Since the REPL does not yet support
    statements, it won't suggest some statement keywords.
    """
    @staticmethod
    def _get_last_fragment(text):
        """Get the last identifier-like fragment
        For example:
        if text is '[1, 2, foo' it will return 'foo'
        if text is 'x and ' it will return suggestions based on ''
        """
        last_fragment = re.split(_NON_IDENTIFIER_PATTERN, text)[-1]
        return last_fragment

    def get_matches(self, text):
        last_fragment = self._get_last_fragment(text)
        if not last_fragment:
            return sorted(key for key in self.namespace.keys()  # type: ignore
                          if not key.startswith('_'))
        matches = []
        for state in count():
            match = self.complete(last_fragment, state)
            if match is None:
                break
            matches.append(match)
        return sorted(matches)


class _ListStream:
    """Context manager to temporarily redirect the writes for the
    given standard stream to a list.
    From: https://stackoverflow.com/a/21341209

    stream_name must be either 'stdout' or 'stderr'.
    """
    def __init__(self, stream_name):
        self.stream_name = stream_name
        self.data = []

    def write(self, s):
        self.data.append(s)

    def __enter__(self):
        setattr(sys, self.stream_name, self)
        return self

    def __exit__(self, ext_type, exc_value, traceback_):
        setattr(sys, self.stream_name, getattr(sys, f"__{self.stream_name}__"))


class _Message:
    def __init__(self, type_, text):
        self.type = type_
        self.text = text

    def to_json(self):
        return json.dumps({"type": self.type, "text": self.text})

    @classmethod
    def from_json(cls, json_str):
        json_data = json.loads(json_str)
        return cls(json_data["type"], json_data["text"])


class WebRepl:
    """Proxy for remote REPL via websocket.
    It receives python expressions from the peer and responds with
    the result of evaluating the expression.

    TODO: Support await. This is requires having an await-capable console like
      that of aioconsole (https://aioconsole.readthedocs.io).
    TODO: syntax highlighting
      https://github.com/jcubic/jquery.terminal/wiki/Formatting-and-Syntax-Highlighting#syntax-highlighting
    """
    def __init__(self, namespace):
        self.namespace = namespace
        self._interpreter = code.InteractiveInterpreter(namespace)

    async def _handleConnected(self, peer: quart.Websocket):
        pass

    async def _handleMessage(self, peer: quart.Websocket, msg: Union[str, bytes]):
        message = _Message.from_json(msg)
        if message.type == "command":
            with _ListStream("stdout") as list_stdout, _ListStream("stderr") as list_stderr:
                # TODO: Handle incomplete inputs and multi-line statements
                # server-side instead of the current client-side implementation.
                # The return value of runsource can be used to decide whether
                # to prompt the next line. Currently this value is ignored
                # and it will return silently if the input is incomplete.
                self._interpreter.runsource(message.text + "\n")
            stdout = "".join(list_stdout.data)
            stderr = "".join(list_stderr.data)
            response_text = (stdout + stderr).rstrip()

        elif message.type == "autocomplete":
            completer = _Completer(self.namespace)
            response_text = ",".join(completer.get_matches(message.text))

        else:
            raise ValueError(f"Invalid message type: {message.type}")

        response = _Message(message.type, response_text).to_json()
        await peer.send(response)

    def _handleClose(self, peer: quart.Websocket):
        pass
