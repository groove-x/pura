/* jshint esversion: 6 */
/* jshint browser: true */
/* jshint -W061 */
/* global canvas, root_ws_url */

/*
let reqAnimFrame = window.requestAnimationFrame ||
                   window.mozRequestAnimationFrame ||
                   window.webkitRequestAnimationFrame;
*/

let pura = {};

pura.baseTitle = document.title;
pura.webviewSocket = null;
pura.webviewServers = [];
pura.context = canvas.getContext("2d");
pura.backCanvas = document.createElement("canvas");
pura.backCanvas.width = canvas.width;
pura.backCanvas.height = canvas.height;
pura.backContext = pura.backCanvas.getContext("2d");
pura.webviewInfoByName = {};  // port, width, height, display_name, link_url
pura.webviewSelect = document.getElementById("webview-select");
pura.connectionStatus = document.getElementById("connection-status");
pura.haveNonLinkWebview = false;
pura.lastWebview = window.location.hash ? window.location.hash.slice(1) : null;
pura.lastButtons = [];
pura.lastAxes = [];
pura.imagesById = {};
pura.isImageLoadPending = false;
pura.pendingCommands = [];  // to queue commands during image loading

// Subscribe to a webview server to receive information about added views,
// which we then present in the selection dropdown.  See add_webview().
//
// The root webview server is tied to initialization of the view dropdown
// and the connection status display.
//
// TODO: fix race conditions due to retry handling
pura.webview_server_subscribe = function(base_url, is_root) {
    if (!is_root && pura.webviewServers.some(ws => ws.url === base_url + "_main")) {
        return;
    }

    if (is_root && pura.webviewSocket) {
        pura.webviewSocket.close();
    }

    window.console.info('webview server subscribe', base_url);
    let ws = new WebSocket(base_url + "_main");
    let open_success = false;

    ws.onopen = function() {
        if (is_root) {
            pura.webviewInfoByName = {};
            pura.haveNonLinkWebview = false;
            pura.webviewServers = [];
            pura.webviewSelect.innerHTML = "";
            if (pura.lastWebview) {
                window.console.info('waiting for view "%s"', pura.lastWebview);
            }
            pura.connectionStatus.className = "status in-progress";
        }
        pura.webviewServers.push(ws);
        open_success = true;
    };

    ws.onmessage = function(e) {
        pura.eval(e.data, null, base_url);
    };

    ws.onclose = function() {
        window.console.log('webview server connection closed', base_url);
        ws = null;
        if (is_root) {
            pura.webviewServers.slice(1).forEach(child_ws => child_ws.close());
            pura.connectionStatus.className = "status dead";
        }
        // Only root will retried indefinitely.  Others only until first
        // successful connect.
        if (is_root || !open_success) {
            setTimeout(pura.webview_server_subscribe, (4 + Math.random()) * 1000,
                       base_url, is_root);
        }
    };
};

pura.input_handler = function(e) {
    if (!pura.isConnected()) {
        return;
    }
    let msg = {
        type: e.type || "",
        x: e.offsetX || 0,
        y: e.offsetY || 0,
        button: e.button || 0,
        alt_key: e.altKey || false,
        ctrl_key: e.ctrlKey || false,
        meta_key: e.metaKey || false,
        shift_key: e.shiftKey || false,
        key_code: e.key || 0
    };
    pura.webviewSocket.send(JSON.stringify(msg));
};

pura.swap = function() {
    // Since requestAnimationFrame can be delayed it causes the buffer
    // copy to happen when the next frame is in progress.  Running the
    // drawImage immediately seems to work well without artifacts.
    //reqAnimFrame(function () {
        pura.context.drawImage(pura.backCanvas, 0, 0);
    //});
};

pura.eval = function(s, ctx, ws_url) {
    // (args appear unused but may be accessed by the evaluated code)
    eval(s);
};

pura.isConnected = function () {
    return pura.webviewSocket !== null && pura.webviewSocket.readyState === WebSocket.OPEN;
};

pura.add_webview = function(base_url, path, width, height, display_name, link_url) {
    let url = base_url + path;
    let name = display_name || path;
    window.console.log('add webview', url);
    pura.webviewInfoByName[name] =
        {url: url, width: width, height: height, link_url: link_url};
    let option = document.createElement("option");
    option.text = name;
    // add item to list in alphabetical order
    let i = 0;
    for (; i < pura.webviewSelect.options.length; ++i) {
        if (pura.webviewSelect.options[i].text.toLowerCase() > name.toLowerCase()) break;
    }
    pura.webviewSelect.add(option, i);
    if (pura.lastWebview) {
        if (name === pura.lastWebview) {
            pura.webviewSelect.value = name;
            pura.requestOpenWebview();
        }
    } else if (!pura.haveNonLinkWebview && !link_url) {
        // received the first valid (non-link) item, so select it
        pura.haveNonLinkWebview = true;
        pura.webviewSelect.value = name;
        pura.requestOpenWebview();
    }
};

let webview_onopen = function(e) {
    canvas.onmousedown = pura.input_handler;
    canvas.onmouseup   = pura.input_handler;
    canvas.onmousemove = pura.input_handler;
    canvas.onmouseout  = pura.input_handler;
    //canvas.onclick     = pura.input_handler;
    canvas.ondblclick  = pura.input_handler;
    canvas.oncontextmenu = function() { return false; };

    document.body.onkeydown  = pura.input_handler;
    document.body.onkeyup    = pura.input_handler;
    //document.body.onkeypress = pura.input_handler;

    pura.connectionStatus.className = "status open";

    //pura.webviewSocket.send(JSON.stringify({
    //    type: "setbounds", width: canvas.width, height: canvas.height
    //}));
};

let webview_onmessage = function(e) {
    if (pura.isImageLoadPending) {
        pura.pendingCommands.push(e.data);
    } else {
        pura.eval(e.data, pura.backContext);
    }
};

pura.resumeCommands = function() {
    while (pura.pendingCommands.length > 0 && !pura.isImageLoadPending) {
        pura.eval(pura.pendingCommands.shift(), pura.backContext);
    }
};

pura.webviewSelect.onchange = function() {
    let name = pura.webviewSelect.value;
    let info = pura.webviewInfoByName[name];

    // Hacky way to surface REPL, etc.:  named URL's are registered as "webviews".
    // When that item gets selected, restore the dropdown value and open the URL
    // in a new window.
    if (info.link_url) {
        pura.webviewSelect.value = pura.lastWebview;
        window.open(info.link_url, '_blank');
        return;
    }

    if (pura.webviewSocket) {
        pura.webviewSocket.close();
    }
    let pixelRatio = window.devicePixelRatio;
    canvas.width = pura.backCanvas.width = Math.trunc(info.width * pixelRatio);
    canvas.height = pura.backCanvas.height = Math.trunc(info.height * pixelRatio);
    canvas.style.width = info.width + 'px';
    canvas.style.height = info.height + 'px';
    pura.backContext.scale(pixelRatio, pixelRatio);
    // TODO: retry if webview socket is disconnected but main socket remains
    let ws = new WebSocket(info.url);
    ws.onopen = webview_onopen;
    ws.onmessage = webview_onmessage;
    pura.webviewSocket = ws;
    pura.webviewSelect.blur();
    pura.lastWebview = name;
    window.location.hash = '#' + name;
    document.title = [pura.baseTitle, name, window.location.hostname].join(" • ");
};

pura.requestOpenWebview = function() {
    if (!document.hidden) {
        pura.webviewSelect.onchange(null);
    } else {
        window.console.log('deferring webview connection (window hidden)');
    }
};

let option_exists = function(selectElement, optionValue) {
    return !!Array.prototype.find.call(
        selectElement.options, option => option.value === optionValue);
};

window.onhashchange = function() {
    let hash = window.location.hash;
    if (hash) {
        let name = hash.slice(1);
        if (name !== pura.webviewSelect.value) {
            if (option_exists(pura.webviewSelect, name)) {
                pura.webviewSelect.value = name;
                pura.requestOpenWebview();
                return;
            }
        }
    }
    // empty or unknown name, so revert to current view
    window.location.hash = '#' + pura.webviewSelect.value;
    document.title = [pura.baseTitle, pura.webviewSelect.value, window.location.hostname].join(" • ");
};

// disconnect webview if tab is hidden, reconnect when unhidden
// This is to avoid filling memory, since the WebSocket API does not have backpressure.
let handleVisibilityChange = function() {
    if (document.hidden && pura.webviewSocket) {
        window.console.log("disconnecting webview (window hidden)");
        pura.connectionStatus.className = "status in-progress";
        pura.webviewSocket.close();
        pura.webviewSocket = null;
    } else if (!document.hidden && pura.connectionStatus.className !== "status dead") {
        window.console.log("reconnecting webview (window unhidden)");
        pura.requestOpenWebview();
    }
};
document.addEventListener("visibilitychange", handleVisibilityChange, false);
pura.webview_server_subscribe(root_ws_url, true /*is_root*/);
