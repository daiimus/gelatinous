#!/usr/bin/env python3
"""
GMCP-over-WebSocket wire format validation test.

Connects to the Gelatinous WebSocket endpoint with the gmcp.mudstandards.org
subprotocol and validates:

  1. Subprotocol negotiation -- server accepts gmcp.mudstandards.org
  2. BINARY frames -- login screen arrives as BINARY with ANSI escape codes
  3. No JSON wrapping -- frames are NOT ["text", ...] JSON arrays
  4. No HTML -- frames do NOT contain <span> tags or HTML entities
  5. Command input -- sending a BINARY frame command gets a BINARY response
  6. GMCP TEXT frames -- (informational) reports any TEXT frames received

Usage:
    python tests/test_gmcp_websocket.py [--url wss://gel.monster/ws]

Requires:
    pip install websockets
"""

import argparse
import asyncio
import sys
import re

try:
    import websockets
except ImportError:
    print("ERROR: 'websockets' package required. Install with: pip install websockets")
    sys.exit(1)

# Default WebSocket URL
DEFAULT_URL = "wss://gel.monster/ws"

# ANSI escape code pattern
ANSI_RE = re.compile(r"\033\[[\d;]*m")

# HTML tag pattern -- look for actual HTML tags, not angle-bracket text like <email@example.com>
HTML_RE = re.compile(r"<(?:span|div|p|br|b|i|em|strong|a|table|tr|td|th|ul|ol|li|pre|code|font|img|h[1-6])[\s>/]", re.IGNORECASE)

# JSON array pattern (Evennia webclient format)
JSON_ARRAY_RE = re.compile(r'^\s*\["(text|prompt)"')


class TestResult:
    """Simple test result tracker."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def ok(self, name, detail=""):
        self.passed += 1
        self.results.append(("PASS", name, detail))
        print(f"  PASS  {name}" + (f" -- {detail}" if detail else ""))

    def fail(self, name, detail=""):
        self.failed += 1
        self.results.append(("FAIL", name, detail))
        print(f"  FAIL  {name}" + (f" -- {detail}" if detail else ""))

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'=' * 60}")
        print(f"Results: {self.passed}/{total} passed, {self.failed}/{total} failed")
        if self.failed:
            print("\nFailed tests:")
            for status, name, detail in self.results:
                if status == "FAIL":
                    print(f"  - {name}: {detail}")
        print(f"{'=' * 60}")
        return self.failed == 0


async def run_tests(url):
    """Connect and run wire format validation tests."""
    results = TestResult()

    print(f"\nConnecting to {url}")
    print(f"Subprotocol: gmcp.mudstandards.org")
    print(f"{'=' * 60}\n")

    try:
        async with websockets.connect(
            url,
            subprotocols=[websockets.Subprotocol("gmcp.mudstandards.org")],
            open_timeout=10,
        ) as ws:
            # Test 1: Subprotocol negotiation
            if ws.subprotocol == "gmcp.mudstandards.org":
                results.ok("Subprotocol negotiation", f"accepted: {ws.subprotocol}")
            else:
                results.fail(
                    "Subprotocol negotiation",
                    f"expected gmcp.mudstandards.org, got: {ws.subprotocol}",
                )

            # Collect initial frames (login screen)
            print("\n  Waiting for login screen frames...")
            binary_frames = []
            text_frames = []
            deadline = asyncio.get_running_loop().time() + 5
            while asyncio.get_running_loop().time() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if isinstance(msg, bytes):
                        binary_frames.append(msg)
                        decoded = msg.decode("utf-8", errors="replace")
                        preview = decoded[:120].replace("\n", "\\n")
                        print(f"    BINARY ({len(msg)} bytes): {preview}...")
                    else:
                        text_frames.append(msg)
                        preview = msg[:120]
                        print(f"    TEXT: {preview}")
                except asyncio.TimeoutError:
                    break
                except websockets.ConnectionClosed:
                    break

            # Test 2: Received BINARY frames
            if binary_frames:
                results.ok(
                    "BINARY frames received",
                    f"{len(binary_frames)} binary frame(s) from login screen",
                )
            else:
                results.fail("BINARY frames received", "no BINARY frames received")

            # Test 3: BINARY frames contain ANSI escape codes
            all_text = b"".join(binary_frames).decode("utf-8", errors="replace")
            if ANSI_RE.search(all_text):
                ansi_count = len(ANSI_RE.findall(all_text))
                results.ok("ANSI escape codes present", f"{ansi_count} ANSI sequences found")
            else:
                results.fail(
                    "ANSI escape codes present",
                    "no ANSI escape sequences (\\033[...m) found in BINARY frames",
                )

            # Test 4: No HTML in BINARY frames
            if HTML_RE.search(all_text):
                match = HTML_RE.search(all_text).group()
                results.fail("No HTML in BINARY frames", f"found HTML: {match}")
            else:
                results.ok("No HTML in BINARY frames")

            # Test 5: No JSON array wrapping
            for frame in binary_frames:
                decoded = frame.decode("utf-8", errors="replace").strip()
                if JSON_ARRAY_RE.match(decoded):
                    results.fail(
                        "No JSON array wrapping",
                        f'BINARY frame starts with JSON array: {decoded[:80]}',
                    )
                    break
            else:
                results.ok("No JSON array wrapping", "BINARY frames are raw text, not JSON")

            # Test 6: Send a command and check response
            print("\n  Sending test command via BINARY frame: 'look'")
            await ws.send(b"look")

            # Collect response frames
            response_binary = []
            response_text = []
            deadline = asyncio.get_running_loop().time() + 5
            while asyncio.get_running_loop().time() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if isinstance(msg, bytes):
                        response_binary.append(msg)
                        decoded = msg.decode("utf-8", errors="replace")
                        preview = decoded[:120].replace("\n", "\\n")
                        print(f"    BINARY ({len(msg)} bytes): {preview}...")
                    else:
                        response_text.append(msg)
                        preview = msg[:120]
                        print(f"    TEXT: {preview}")
                except asyncio.TimeoutError:
                    break
                except websockets.ConnectionClosed:
                    break

            if response_binary:
                results.ok(
                    "Command response as BINARY",
                    f"{len(response_binary)} BINARY frame(s) in response to 'look'",
                )
            else:
                results.fail(
                    "Command response as BINARY",
                    "no BINARY frames received in response to command",
                )

            # Report any TEXT (GMCP) frames
            all_gmcp = text_frames + response_text
            if all_gmcp:
                print(f"\n  INFO: {len(all_gmcp)} GMCP TEXT frame(s) received:")
                for frame in all_gmcp:
                    print(f"    {frame[:200]}")

    except websockets.InvalidHandshake as e:
        results.fail("WebSocket handshake", str(e))
    except ConnectionRefusedError:
        results.fail("Connection", f"refused by {url}")
    except OSError as e:
        results.fail("Connection", str(e))

    return results.summary()


def main():
    parser = argparse.ArgumentParser(
        description="Test GMCP-over-WebSocket wire format against Gelatinous"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"WebSocket URL to connect to (default: {DEFAULT_URL})",
    )
    args = parser.parse_args()

    print("GMCP-over-WebSocket Wire Format Test")
    print(f"Target: {args.url}")

    success = asyncio.run(run_tests(args.url))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
