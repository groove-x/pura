/* jshint esversion: 6 */
/* jshint browser: true */
/* global jQuery, root_ws_url */

/* Remote REPL client.
It sends commands input by the user and displays the received result.
See repl.html for the implementation of the user interface.
*/
const NON_IDENTIFIER_PATTERN = /[^a-zA-Z0-9._]+/g;
const PROMPT = "[[;green;]>>> ]";
const PROMPT_CONTINUE = "[[;green;]... ]";

function getLastFragment(text) {
    return text.split(NON_IDENTIFIER_PATTERN).pop();
}

// TODO: Consider having the server generate a JS string that calls a top-level
// action, instead of marshalling with an intermediate message type
class Message {
    constructor(type, text) {
        this.type = type;
        this.text = text;
    }
    toJson() {
        return JSON.stringify({"type": this.type, "text": this.text});
    }
}

// TODO: does javascript have classmethods?
function json2Message(json_str) {
    let json_data = JSON.parse(json_str);
    return new Message(json_data.type, json_data.text);
}

document.title += " • REPL • " + window.location.hostname;

let repl = {};

repl.websocket = null;
repl.connectionStatus = document.getElementById("connection-status");
repl.terminal = null;
repl.completion_callback = null;
repl.completion_prefix = null;
repl.code = "";

function updateOutput(message) {
    let msg = json2Message(message.data);

    if (msg.type === "command") {
        if (msg.text.length > 0) {
            repl.terminal.echo(msg.text);
        }
    } else if (msg.type === "autocomplete") {
        let matches = msg.text.split(",");
        repl.completion_callback(matches.map(cmd => repl.completion_prefix + cmd));
    }
    else {
        window.console.log("Invalid message type:", msg.type);
    }
}

// Triggered when the user presses ENTER
function sendCommand(cmd) {
    let message = new Message("command", cmd);
    repl.websocket.send(message.toJson());
}

// Triggered when the user presses TAB
function sendAutocomplete(text) {
    let message = new Message("autocomplete", text);
    repl.websocket.send(message.toJson());
}

repl.serverSubscribe = function() {
    window.console.log("repl.serverSubscribe");
    if (repl.websocket) {
        repl.websocket.close();
    }
    let url = root_ws_url;

    window.console.info("repl server subscribe", url);

    let ws = new WebSocket(url);
    repl.connectionStatus.className = "status in-progress";

    ws.onopen = function() {
        repl.connectionStatus.className = "status open";
    };

    ws.onmessage = updateOutput;

    ws.onclose = function() {
        window.console.log('webview server connection closed', url);
        ws = null;
        repl.connectionStatus.className = "status dead";
        setTimeout(repl.serverSubscribe, (4 + Math.random()) * 1000);
    };

    repl.websocket = ws;
};

repl.serverSubscribe();

// TODO: make history to be multi-line aware, like the Pycharm console.
jQuery(function($, undefined) {
    repl.terminal = $('#terminal').terminal(function(cmd) {
        // Logic to handle multi-line statements
        // Adapted from: https://github.com/jcubic/try-python/blob/master/main.py#L30
        let last_char = cmd.trim().slice(-1);
        if (last_char === ':' || last_char === "\\") {
            this.set_prompt(PROMPT_CONTINUE);
            repl.code += cmd + "\n";
        } else if (repl.code !== '' && cmd === "") {
            sendCommand(repl.code);
            this.set_prompt(PROMPT);
            repl.code = "";
        } else if (repl.code !== '' && cmd !== "") {
            repl.code += cmd + "\n";
        } else if (repl.code === '' && cmd !== "") {
            sendCommand(cmd);
        }
    }, {
        // options reference:  https://terminal.jcubic.pl/api_reference.php#options
        greetings: '',
        height: 400,
        prompt: PROMPT,
        clear: false,
        // The built-in implementation of tab-completion only supports space
        // as word delimiter, so custom tab completion handling is necessary.
        // See https://github.com/jcubic/jquery.terminal/issues/489
        completionEscape: false,
        wordAutocomplete: false,
        completion: function(cmd, callback) {
            if (cmd.trim() === "" && repl.code !== "") {
                this.insert("    ");
                return;
            }
            let before_cursor = this.before_cursor();
            let fragment = getLastFragment(before_cursor);
            repl.completion_callback = callback;
            repl.completion_prefix = before_cursor.substring(0, before_cursor.length - fragment.length);
            sendAutocomplete(fragment);
        },
        doubleTab: function(cmd, matches, echo_cmd) {
            echo_cmd();
            // TODO: columnar alignment (see python repl)
            this.echo(matches.map(cmd_ => cmd_.substring(repl.completion_prefix.length)).join(' '),
                      {keepWords: true});
        },
        keymap: {
            "CTRL+C": function(e, original_callback){
                repl.code = "";
                original_callback();
                this.set_prompt(PROMPT);
            }
        }
    });
});
