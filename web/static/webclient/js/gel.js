/**
 * gel.js -- Gelatinous Web Client
 *
 * Single-file GMCP WebSocket client for the Gelatinous MUD.
 * Connects via wss:// using the gmcp.mudstandards.org subprotocol.
 * Receives ANSI text on BINARY frames, GMCP messages on TEXT frames.
 *
 * Dependencies:
 *   - ansi_up v6.0.6 (loaded as ESM from CDN)
 *
 * No jQuery, no Bootstrap, no evennia.js, no build step.
 */

/* global AnsiUp */

(function () {
    "use strict";

    // ----------------------------------------------------------------
    // Configuration
    // ----------------------------------------------------------------

    var MAX_OUTPUT_LINES = 5000;
    var MAX_HISTORY = 500;
    var KEEPALIVE_MS = 30000;          // 30s Core.KeepAlive interval
    var PING_INTERVAL_MS = 60000;      // 60s latency probe interval
    var RECONNECT_BASE_MS = 1000;      // Initial reconnect delay
    var RECONNECT_MAX_MS = 30000;      // Max reconnect delay
    var RESIZE_DEBOUNCE_MS = 250;      // Screen size report debounce
    var STORAGE_KEY = "gel_history";

    // ----------------------------------------------------------------
    // DOM references
    // ----------------------------------------------------------------

    var elOutput = document.getElementById("output");
    var elOutputInner = document.getElementById("output-inner");
    var elScrollSentinel = document.getElementById("scroll-sentinel");
    var elMoreIndicator = document.getElementById("more-indicator");
    var elInput = document.getElementById("input-field");
    var elSendBtn = document.getElementById("send-btn");
    var elStateDot = document.getElementById("state-dot");
    var elStateText = document.getElementById("state-text");
    var elLatency = document.getElementById("latency");
    var elReconnectOverlay = document.getElementById("reconnect-overlay");
    var elReconnectMsg = document.getElementById("reconnect-msg");
    var elReconnectDetail = document.getElementById("reconnect-detail");

    // ----------------------------------------------------------------
    // State
    // ----------------------------------------------------------------

    var ws = null;
    var ansi = null;  // initialized in init() after AnsiUp is loaded

    var connected = false;
    var reconnectAttempts = 0;
    var reconnectTimer = null;
    var timerWorker = null;    // Web Worker for throttle-proof timers
    var pingTimestamp = 0;
    var resizeTimer = null;

    // Auto-scroll tracking via IntersectionObserver
    var autoScroll = true;
    var scrollObserver = null;

    // Command history
    var history = loadHistory();
    var historyIndex = -1;
    var historyDraft = "";

    // Screen size probe element
    var probeEl = null;

    // ----------------------------------------------------------------
    // ANSI rendering
    // ----------------------------------------------------------------

    function appendOutput(html) {
        elOutputInner.insertAdjacentHTML("beforeend", html);
        trimOutput();
        if (autoScroll) {
            scrollToBottom();
        }
    }

    function appendSystemMsg(text, cls) {
        var span = document.createElement("span");
        span.className = "sys-msg" + (cls ? " " + cls : "");
        span.textContent = text;
        elOutputInner.appendChild(span);
        elOutputInner.appendChild(document.createTextNode("\n"));
        if (autoScroll) {
            scrollToBottom();
        }
    }

    function scrollToBottom() {
        elOutput.scrollTop = elOutput.scrollHeight;
    }

    function trimOutput() {
        // Remove oldest lines if we exceed the buffer limit.
        // We count child nodes (each BINARY frame appends one chunk).
        var children = elOutputInner.childNodes;
        while (children.length > MAX_OUTPUT_LINES * 2) {
            elOutputInner.removeChild(children[0]);
        }
    }

    // ----------------------------------------------------------------
    // Auto-scroll via IntersectionObserver
    // ----------------------------------------------------------------

    function setupScrollObserver() {
        if (!("IntersectionObserver" in window)) {
            // Fallback: always auto-scroll
            autoScroll = true;
            return;
        }
        scrollObserver = new IntersectionObserver(
            function (entries) {
                autoScroll = entries[0].isIntersecting;
                if (autoScroll) {
                    elMoreIndicator.classList.remove("visible");
                } else {
                    elMoreIndicator.classList.add("visible");
                }
            },
            { root: elOutput, threshold: 0.1 }
        );
        scrollObserver.observe(elScrollSentinel);
    }

    // ----------------------------------------------------------------
    // WebSocket connection
    // ----------------------------------------------------------------

    function connect() {
        if (ws) {
            try { ws.close(); } catch (_) { /* ignore */ }
            ws = null;
        }

        setConnectionState("connecting");

        // Build URL with auth params (csessid and cuid come from the template).
        // Evennia's WebSocketClient.get_client_session() parses the URL as
        // wsurl?csessid&page_id&browserstr -- bare positional values, no keys.
        var url = wsurl;
        if (typeof csessid !== "undefined" && csessid) {
            url += "?" + csessid + "&" + cuid;
        }

        try {
            ws = new WebSocket(url, ["gmcp.mudstandards.org"]);
        } catch (e) {
            appendSystemMsg("WebSocket creation failed: " + e.message, "error");
            scheduleReconnect();
            return;
        }

        ws.binaryType = "arraybuffer";

        ws.onopen = function () {
            connected = true;
            reconnectAttempts = 0;
            setConnectionState("connected");
            hideReconnectOverlay();

            // Send GMCP handshake
            sendGMCP("Core.Hello", {
                client: "Gelatinous Web Client",
                version: "1.0"
            });
            sendGMCP("Core.Supports.Set", [
                "Client 1",
                "Char 1",
                "Room 1"
            ]);

            // Report screen size
            sendScreenSize();

            // Start keep-alive and ping timers
            startKeepAlive();
            startPingProbe();

            appendSystemMsg("Connected.", "success");
        };

        ws.onmessage = function (event) {
            if (event.data instanceof ArrayBuffer) {
                // BINARY frame: ANSI game text
                var text = new TextDecoder("utf-8").decode(event.data);
                var html = ansi.ansi_to_html(text);
                // ansi_up preserves literal \n in its output; convert to <br>
                // so line breaks render in any HTML container context.
                html = html.replace(/\n/g, "<br>");
                // Ensure each frame ends with a line break so the next
                // frame's content doesn't join the last line of this one.
                if (!html.endsWith("<br>")) {
                    html += "<br>";
                }
                appendOutput(html);
            } else {
                // TEXT frame: GMCP message
                handleGMCP(event.data);
            }
        };

        ws.onclose = function (event) {
            var wasConnected = connected;
            connected = false;
            stopTimers();
            setConnectionState("disconnected");

            if (wasConnected) {
                appendSystemMsg(
                    "Connection closed" +
                    (event.reason ? ": " + event.reason : "."),
                    "warning"
                );
            }
            scheduleReconnect();
        };

        ws.onerror = function () {
            // onclose will fire after this; avoid double-messaging
        };
    }

    // ----------------------------------------------------------------
    // GMCP messaging
    // ----------------------------------------------------------------

    function sendGMCP(pkg, data) {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        var msg = data !== undefined ? pkg + " " + JSON.stringify(data) : pkg;
        ws.send(msg);  // TEXT frame (string)
    }

    function sendCommand(text) {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        // Encode as UTF-8 ArrayBuffer for BINARY frame
        var encoded = new TextEncoder().encode(text);
        ws.send(encoded.buffer);
    }

    function handleGMCP(raw) {
        var spaceIdx = raw.indexOf(" ");
        var pkg, data;
        if (spaceIdx === -1) {
            pkg = raw;
            data = null;
        } else {
            pkg = raw.substring(0, spaceIdx);
            try {
                data = JSON.parse(raw.substring(spaceIdx + 1));
            } catch (_) {
                data = null;
            }
        }

        var handler = gmcpHandlers[pkg] || gmcpHandlers[pkg.toLowerCase()];
        if (handler) {
            handler(data);
        }
        // Unknown packages are silently ignored (forward-compatible)
    }

    var gmcpHandlers = {
        "Core.Ping": function () {
            if (pingTimestamp > 0) {
                var rtt = Date.now() - pingTimestamp;
                pingTimestamp = 0;
                elLatency.textContent = rtt + "ms";
            }
        },
        "Core.Goodbye": function (data) {
            var msg = (data && typeof data === "string") ? data : "Server closing connection.";
            appendSystemMsg(msg, "warning");
        }
        // Future: Char.Vitals, Room.Info, etc.
    };

    // ----------------------------------------------------------------
    // Keep-alive & ping via Web Worker
    //
    // Browsers aggressively throttle setInterval in background tabs
    // (Firefox/Safari clamp to >= 1min, may suspend entirely).
    // A Web Worker's timers run unthrottled regardless of tab visibility,
    // so we use one as a reliable clock and handle the sends on the
    // main thread where the WebSocket lives.
    // ----------------------------------------------------------------

    function createTimerWorker() {
        var code =
            "var timers = {};" +
            "onmessage = function(e) {" +
            "  if (e.data.cmd === 'start') {" +
            "    if (timers[e.data.id]) clearInterval(timers[e.data.id]);" +
            "    timers[e.data.id] = setInterval(function() {" +
            "      postMessage({ id: e.data.id });" +
            "    }, e.data.ms);" +
            "  } else if (e.data.cmd === 'stop') {" +
            "    clearInterval(timers[e.data.id]);" +
            "    delete timers[e.data.id];" +
            "  } else if (e.data.cmd === 'stopall') {" +
            "    for (var k in timers) clearInterval(timers[k]);" +
            "    timers = {};" +
            "  }" +
            "};";
        var blob = new Blob([code], { type: "application/javascript" });
        var worker = new Worker(URL.createObjectURL(blob));
        worker.onmessage = function (e) {
            if (e.data.id === "keepalive") {
                sendGMCP("Core.KeepAlive");
            } else if (e.data.id === "ping") {
                doPing();
            }
        };
        return worker;
    }

    function startKeepAlive() {
        if (!timerWorker) return;
        timerWorker.postMessage({ cmd: "start", id: "keepalive", ms: KEEPALIVE_MS });
    }

    function stopKeepAlive() {
        if (!timerWorker) return;
        timerWorker.postMessage({ cmd: "stop", id: "keepalive" });
    }

    function startPingProbe() {
        if (!timerWorker) return;
        // Initial ping after short delay
        setTimeout(function () {
            doPing();
        }, 3000);
        timerWorker.postMessage({ cmd: "start", id: "ping", ms: PING_INTERVAL_MS });
    }

    function doPing() {
        if (!connected) return;
        pingTimestamp = Date.now();
        sendGMCP("Core.Ping");
    }

    function stopPingProbe() {
        if (timerWorker) {
            timerWorker.postMessage({ cmd: "stop", id: "ping" });
        }
        pingTimestamp = 0;
    }

    function stopTimers() {
        if (timerWorker) {
            timerWorker.postMessage({ cmd: "stopall" });
        }
        pingTimestamp = 0;
    }

    // Fallback when Web Workers are unavailable: same interface, main-thread timers
    function createFallbackTimers() {
        var timers = {};
        var handlers = {
            keepalive: function () { sendGMCP("Core.KeepAlive"); },
            ping: function () { doPing(); }
        };
        return {
            postMessage: function (msg) {
                if (msg.cmd === "start") {
                    if (timers[msg.id]) clearInterval(timers[msg.id]);
                    timers[msg.id] = setInterval(handlers[msg.id], msg.ms);
                } else if (msg.cmd === "stop") {
                    clearInterval(timers[msg.id]);
                    delete timers[msg.id];
                } else if (msg.cmd === "stopall") {
                    for (var k in timers) clearInterval(timers[k]);
                    timers = {};
                }
            }
        };
    }

    // ----------------------------------------------------------------
    // Reconnect with exponential backoff + jitter
    // ----------------------------------------------------------------

    function scheduleReconnect() {
        if (reconnectTimer) return;

        reconnectAttempts++;
        var delay = Math.min(
            RECONNECT_BASE_MS * Math.pow(2, reconnectAttempts - 1),
            RECONNECT_MAX_MS
        );
        // Add up to 25% jitter
        delay += Math.random() * delay * 0.25;
        delay = Math.round(delay);

        showReconnectOverlay(delay);

        reconnectTimer = setTimeout(function () {
            reconnectTimer = null;
            connect();
        }, delay);
    }

    function showReconnectOverlay(delayMs) {
        elReconnectMsg.textContent = "Connection lost";
        elReconnectDetail.textContent =
            "Reconnecting in " + Math.ceil(delayMs / 1000) + "s" +
            " (attempt " + reconnectAttempts + ")";
        elReconnectOverlay.classList.add("visible");
    }

    function hideReconnectOverlay() {
        elReconnectOverlay.classList.remove("visible");
    }

    // Pause reconnect when tab is hidden, resume when visible
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible" && !connected && !reconnectTimer) {
            // Tab became visible and we're disconnected -- try now
            reconnectAttempts = 0;
            connect();
        }
    });

    // ----------------------------------------------------------------
    // Connection state UI
    // ----------------------------------------------------------------

    function setConnectionState(state) {
        elStateDot.className = "state-dot " + state;
        var labels = {
            connected: "Connected",
            connecting: "Connecting...",
            disconnected: "Disconnected"
        };
        elStateText.textContent = labels[state] || state;

        if (state !== "connected") {
            elLatency.textContent = "";
        }
    }

    // ----------------------------------------------------------------
    // Screen size detection & reporting
    // ----------------------------------------------------------------

    function measureScreen() {
        // Create a hidden probe element to measure character cell size
        if (!probeEl) {
            probeEl = document.createElement("span");
            probeEl.style.cssText =
                "position:absolute;visibility:hidden;white-space:pre;" +
                "font-family:" + getComputedStyle(elOutputInner).fontFamily + ";" +
                "font-size:" + getComputedStyle(elOutputInner).fontSize + ";" +
                "line-height:" + getComputedStyle(elOutputInner).lineHeight + ";";
            probeEl.textContent = "MMMMMMMMMM";  // 10 chars
            document.body.appendChild(probeEl);
        }

        var charWidth = probeEl.offsetWidth / 10;
        var charHeight = probeEl.offsetHeight || 16;

        if (charWidth <= 0) charWidth = 8;
        if (charHeight <= 0) charHeight = 16;

        var outputWidth = elOutput.clientWidth - 20;  // subtract padding
        var outputHeight = elOutput.clientHeight - 16;

        var cols = Math.max(40, Math.floor(outputWidth / charWidth));
        var rows = Math.max(10, Math.floor(outputHeight / charHeight));

        return { screenwidth: cols, screenheight: rows };
    }

    function sendScreenSize() {
        if (!connected) return;
        var size = measureScreen();
        sendGMCP("Client.Options", size);
    }

    function onResize() {
        if (resizeTimer) clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            resizeTimer = null;
            sendScreenSize();
        }, RESIZE_DEBOUNCE_MS);
    }

    // Use visualViewport API if available (better on mobile)
    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", onResize);
    } else {
        window.addEventListener("resize", onResize);
    }

    // ----------------------------------------------------------------
    // Input handling
    // ----------------------------------------------------------------

    function submitInput() {
        var text = elInput.value;
        if (text === "") {
            // Send newline for blank Enter -- a zero-length binary frame may be
            // silently dropped by the WebSocket transport.  A newline matches
            // what telnet sends; the server strips it to "" before forwarding.
            sendCommand("\n");
            return;
        }

        // Local echo -- MUD servers don't echo input back over the wire
        appendOutput("<br><span class=\"sys-echo\">&gt; " +
            text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") +
            "</span><br>");
        sendCommand(text);
        addToHistory(text);
        elInput.value = "";
        autoGrowInput();
        historyIndex = -1;
        historyDraft = "";
    }

    elInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submitInput();
            return;
        }

        // Command history navigation
        if (e.key === "ArrowUp") {
            if (historyIndex === -1) {
                historyDraft = elInput.value;
            }
            if (historyIndex < history.length - 1) {
                historyIndex++;
                elInput.value = history[history.length - 1 - historyIndex];
                // Move cursor to end
                setTimeout(function () {
                    elInput.selectionStart = elInput.selectionEnd = elInput.value.length;
                }, 0);
            }
            e.preventDefault();
            return;
        }

        if (e.key === "ArrowDown") {
            if (historyIndex > 0) {
                historyIndex--;
                elInput.value = history[history.length - 1 - historyIndex];
            } else if (historyIndex === 0) {
                historyIndex = -1;
                elInput.value = historyDraft;
            }
            // Move cursor to end
            setTimeout(function () {
                elInput.selectionStart = elInput.selectionEnd = elInput.value.length;
            }, 0);
            e.preventDefault();
            return;
        }
    });

    elInput.addEventListener("input", autoGrowInput);

    elSendBtn.addEventListener("click", function () {
        submitInput();
        elInput.focus();
    });

    // Auto-grow textarea
    function autoGrowInput() {
        elInput.style.height = "auto";
        elInput.style.height = Math.min(elInput.scrollHeight, 120) + "px";
    }

    // ----------------------------------------------------------------
    // Command history (localStorage)
    // ----------------------------------------------------------------

    function loadHistory() {
        try {
            var data = localStorage.getItem(STORAGE_KEY);
            if (data) {
                var arr = JSON.parse(data);
                if (Array.isArray(arr)) return arr;
            }
        } catch (_) { /* ignore */ }
        return [];
    }

    function saveHistory() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
        } catch (_) { /* ignore */ }
    }

    function addToHistory(text) {
        // Don't add duplicates of the most recent command
        if (history.length > 0 && history[history.length - 1] === text) {
            return;
        }
        history.push(text);
        if (history.length > MAX_HISTORY) {
            history = history.slice(-MAX_HISTORY);
        }
        saveHistory();
    }

    // ----------------------------------------------------------------
    // Focus management
    // ----------------------------------------------------------------

    // Click on output area should not steal focus from input
    // (but allow text selection)
    elOutput.addEventListener("mouseup", function () {
        var sel = window.getSelection();
        if (!sel || sel.isCollapsed) {
            elInput.focus();
        }
    });

    // ----------------------------------------------------------------
    // Boot
    // ----------------------------------------------------------------

    function init() {
        ansi = new AnsiUp();
        ansi.use_classes = false;  // inline styles, zero-maintenance xterm-256
        ansi.escape_html = true;   // XSS trust boundary: escape HTML in game text

        // Create Web Worker for throttle-proof timers (keepalive, ping).
        // Falls back to main-thread setInterval if Workers are unavailable.
        if (typeof Worker !== "undefined") {
            try {
                timerWorker = createTimerWorker();
            } catch (_) {
                timerWorker = null;
            }
        }
        if (!timerWorker) {
            // Fallback: main-thread timers (will be throttled in background tabs)
            timerWorker = createFallbackTimers();
        }

        setupScrollObserver();
        setConnectionState("disconnected");

        // Focus input
        elInput.focus();

        // Connect
        connect();
    }

    // Wait for AnsiUp to be loaded (it's an ES module imported async).
    // If it's already available, init immediately; otherwise wait for the event.
    function boot() {
        if (typeof AnsiUp !== "undefined") {
            init();
        } else {
            var timeout = setTimeout(function () {
                appendSystemMsg(
                    "Failed to load ANSI renderer. Try refreshing the page.",
                    "error"
                );
            }, 5000);
            window.addEventListener("ansi_up_ready", function () {
                clearTimeout(timeout);
                init();
            }, { once: true });
        }
    }

    // Wait for DOM ready (should already be, but be safe)
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

})();
