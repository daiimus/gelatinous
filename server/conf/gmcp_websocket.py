"""
GMCP-over-WebSocket protocol handler for Gelatinous.

Speaks GMCP wire format when the client negotiates the gmcp.mudstandards.org
WebSocket subprotocol. Falls back to Evennia's standard JSON webclient
protocol for browser clients that don't request the subprotocol.

Wire format (GMCP mode):
    BINARY frames (server -> client): Raw ANSI/UTF-8 game text
    TEXT frames (server -> client):   GMCP messages ("Package.Name json")
    BINARY frames (client -> server): Player command input (UTF-8)
    TEXT frames (client -> server):   GMCP messages ("Package.Name json")

Each BINARY frame represents one complete output cycle, acting as an
implicit GA/EOR signal for clients.

Standard GMCP packages handled:
    Core.Hello          Client identification (name, version)
    Core.Ping           Latency measurement (echo back)
    Core.KeepAlive      Reset idle timeout (no response)
    Core.Supports.Set   Declare supported GMCP modules
    Core.Supports.Add   Append to supported module list
    Core.Supports.Remove  Remove from supported module list

Gelatinous-specific packages:
    Client.Options      Screen dimensions and client capabilities,
                        translated to Evennia's client_options inputfunc
"""

import json
import re

from autobahn.exception import Disconnected
from django.conf import settings

from evennia.server.portal.webclient import WebSocketClient
from evennia.utils.ansi import parse_ansi

# Subprotocol identifier for GMCP-over-WebSocket
GMCP_SUBPROTOCOL = "gmcp.mudstandards.org"

# Strip trailing |n from text before we add our own reset
# (matches the pattern used by Evennia's telnet handler)
_RE_N = re.compile(r"\|n$")

# Strip screenreader-unfriendly content
_RE_SCREENREADER_REGEX = re.compile(
    r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE
)


class GmcpWebSocketClient(WebSocketClient):
    """
    WebSocket protocol handler that speaks GMCP wire format when the client
    negotiates the gmcp.mudstandards.org subprotocol, and falls back to
    standard Evennia JSON protocol otherwise.

    GMCP mode sends:
        - Game text as BINARY frames with ANSI escape codes (not HTML)
        - OOB/GMCP data as TEXT frames in "Package.Name json" format
        - Prompts as BINARY frames (implicit GA/EOR per frame)

    Standard mode delegates entirely to the parent WebSocketClient.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gmcp_mode = False
        self.gmcp_supported = {}  # {"Module": version_int, ...}

    def onConnect(self, request):
        """
        WebSocket opening handshake. If the client offers the
        gmcp.mudstandards.org subprotocol, accept it and enable GMCP mode.

        Args:
            request: autobahn ConnectionRequest with request.protocols
                     listing the client's offered subprotocols.

        Returns:
            The accepted subprotocol string, or None for default behavior.
        """
        if GMCP_SUBPROTOCOL in (request.protocols or []):
            self.gmcp_mode = True
            return GMCP_SUBPROTOCOL
        return None

    def onOpen(self):
        """
        Called when the WebSocket connection is fully established.
        Sets up session and protocol flags.
        """
        # Let the parent handle session initialization, client address
        # resolution, auto-login from browser session, and connection
        # registration with the session handler.
        super().onOpen()

        if self.gmcp_mode:
            # Override protocol flags for GMCP clients.
            # The parent already set ANSI, XTERM256, TRUECOLOR, UTF-8, OOB
            # to True -- we keep those and adjust the client name.
            self.protocol_flags["CLIENTNAME"] = "GMCP WebSocket Client"
            # Ensure we don't accidentally trigger raw/nocolor modes
            self.protocol_flags["RAW"] = False
            self.protocol_flags["NOCOLOR"] = False

    def onMessage(self, payload, isBinary):
        """
        Handle incoming WebSocket messages.

        In GMCP mode:
            BINARY frames = player command input (UTF-8 text)
            TEXT frames = GMCP messages ("Package.Name json")

        Standard GMCP Core packages are handled directly by this handler.
        Game-specific GMCP packages are routed through Evennia's inputfunc
        system. Client.Options is translated to Evennia's client_options
        inputfunc with flat kwargs for screen size and capability reporting.

        In standard mode:
            Delegates to parent (expects JSON ["inputfunc", [args], {kwargs}]).

        Args:
            payload (bytes): The WebSocket message received.
            isBinary (bool): True for BINARY frames, False for TEXT frames.
        """
        if not self.gmcp_mode:
            super().onMessage(payload, isBinary)
            return

        if isBinary:
            # Player command input -- decode and pass as text command
            try:
                text = payload.decode("utf-8").strip()
            except UnicodeDecodeError:
                return
            if text:
                self.data_in(text=[[text], {}])
        else:
            # GMCP message from client: "Package.Name optional_json"
            try:
                message = payload.decode("utf-8").strip()
            except UnicodeDecodeError:
                return
            if not message:
                return

            # Parse "Package.Name json_payload"
            parts = message.split(" ", 1)
            package = parts[0]
            try:
                data = json.loads(parts[1]) if len(parts) > 1 else {}
            except (json.JSONDecodeError, IndexError):
                data = {}

            # Handle standard GMCP Core packages directly
            if self._handle_gmcp_core(package, data):
                return

            # Translate Client.Options to Evennia's client_options inputfunc
            if package == "Client.Options":
                if isinstance(data, dict):
                    self.data_in(client_options=[[], data])
                return

            # Route all other GMCP packages through Evennia's OOB system
            self.data_in(**{package: [[], {"data": data}]})

    def _handle_gmcp_core(self, package, data):
        """
        Handle standard GMCP Core.* packages.

        These are protocol-level messages defined by the GMCP standard
        (IRE/Gammon specs) and are handled directly by the transport
        layer rather than routed to Evennia's inputfunc system.

        Args:
            package (str): The GMCP package name (e.g. "Core.Hello").
            data: The parsed JSON payload.

        Returns:
            True if the package was handled, False otherwise.
        """
        pkg = package.lower()

        if pkg == "core.hello":
            # Client identification: {"client": "Name", "version": "1.0"}
            if isinstance(data, dict):
                client = data.get("client", "Unknown")
                version = data.get("version", "")
                name = "{} {}".format(client, version).strip()
                self.protocol_flags["CLIENTNAME"] = name
            return True

        if pkg == "core.ping":
            # Latency measurement: echo back Core.Ping
            try:
                self.sendMessage(b"Core.Ping", isBinary=False)
            except Disconnected:
                pass
            return True

        if pkg == "core.keepalive":
            # Idle timeout reset: no response needed, the message
            # receipt itself resets the connection timeout
            return True

        if pkg == "core.supports.set":
            # Replace supported module list
            self.gmcp_supported = self._parse_supports(data)
            return True

        if pkg == "core.supports.add":
            # Append to supported module list
            self.gmcp_supported.update(self._parse_supports(data))
            return True

        if pkg == "core.supports.remove":
            # Remove from supported module list
            for entry in (data if isinstance(data, list) else []):
                if isinstance(entry, str):
                    module = entry.split()[0]
                    self.gmcp_supported.pop(module, None)
            return True

        return False

    @staticmethod
    def _parse_supports(data):
        """
        Parse a Core.Supports.Set/Add payload into a dict.

        The payload is an array of strings like ["Char 1", "Room 1"].
        Each string is a module name followed by a version number.

        Args:
            data: The parsed JSON payload (expected to be a list).

        Returns:
            dict: Mapping of module name to version integer.
        """
        result = {}
        for entry in (data if isinstance(data, list) else []):
            if isinstance(entry, str):
                parts = entry.split()
                module = parts[0]
                try:
                    version = int(parts[1]) if len(parts) > 1 else 1
                except (ValueError, IndexError):
                    version = 1
                result[module] = version
        return result

    def send_text(self, *args, **kwargs):
        """
        Send text data to the client.

        In GMCP mode: Convert Evennia markup to ANSI escape codes and send
        as a BINARY WebSocket frame. No HTML conversion. No JSON wrapping.

        In standard mode: Delegates to parent (HTML + JSON).

        Args:
            *args: First arg is the text string to send.
        Keyword Args:
            options (dict): Send-option flags (raw, nocolor, screenreader, etc.)
        """
        if not self.gmcp_mode:
            super().send_text(*args, **kwargs)
            return

        if args:
            args = list(args)
            text = args[0]
            if text is None:
                return
        else:
            return

        flags = self.protocol_flags
        options = kwargs.pop("options", {})
        raw = options.get("raw", flags.get("RAW", False))
        nocolor = options.get("nocolor", flags.get("NOCOLOR", False))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))

        if screenreader:
            # Screenreader mode: strip all ANSI and visual clutter
            text = parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE_SCREENREADER_REGEX.sub("", text)
        elif raw:
            # Raw mode: send text as-is without any ANSI processing.
            # The text may contain Evennia markup that won't be converted,
            # but the caller explicitly requested no processing.
            pass
        else:
            # Normal mode: convert Evennia markup to ANSI escape codes.
            # Normalize trailing color reset (same pattern as Evennia's telnet handler)
            text = _RE_N.sub("", text) + ("||n" if text.endswith("|") else "|n")
            text = parse_ansi(
                text,
                strip_ansi=nocolor,
                xterm256=flags.get("XTERM256", True),
                truecolor=flags.get("TRUECOLOR", True),
                mxp=False,
            )

        # Send as BINARY frame -- raw ANSI text, no JSON wrapping
        try:
            self.sendMessage(text.encode("utf-8"), isBinary=True)
        except Disconnected:
            self.disconnect(reason="Connection already closed.")

    def send_prompt(self, *args, **kwargs):
        """
        Send a prompt to the client.

        In GMCP mode: Sent as a regular BINARY frame. Each BINARY frame
        acts as an implicit GA/EOR signal, so no special framing is needed.

        In standard mode: Delegates to parent.
        """
        if not self.gmcp_mode:
            super().send_prompt(*args, **kwargs)
            return

        # Send prompt as regular text -- the BINARY frame boundary
        # is the implicit GA/EOR signal for GMCP clients.
        kwargs["options"] = kwargs.get("options", {})
        self.send_text(*args, **kwargs)

    def send_default(self, cmdname, *args, **kwargs):
        """
        Send OOB/GMCP data to the client.

        In GMCP mode: Format as "Package.Name json_payload" and send as a
        TEXT WebSocket frame.

        In standard mode: Delegates to parent (JSON array format).

        Args:
            cmdname (str): The OOB command/GMCP package name.
            *args: Arguments for the command.
        Keyword Args:
            options (dict): Ignored for OOB commands.
        """
        if not self.gmcp_mode:
            super().send_default(cmdname, *args, **kwargs)
            return

        # Skip the "options" command (internal Evennia protocol negotiation)
        if cmdname == "options":
            return

        # Build GMCP message: "Package.Name json_payload"
        # args typically contains the payload dict/list as the first element
        if args:
            payload = args[0] if len(args) == 1 else list(args)
            message = "{} {}".format(cmdname, json.dumps(payload, ensure_ascii=False))
        else:
            message = cmdname

        # Send as TEXT frame
        try:
            self.sendMessage(message.encode("utf-8"), isBinary=False)
        except Disconnected:
            self.disconnect(reason="Connection already closed.")
