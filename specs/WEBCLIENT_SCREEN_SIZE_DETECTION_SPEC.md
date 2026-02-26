# Webclient Screen Size Detection Specification

## Document Information

**Version:** 1.0  
**Date:** 2025-01-XX  
**Status:** Draft - Awaiting Review  
**Author:** AI Agent  
**Related Systems:** G.R.I.M. Combat System, Evennia Webclient  

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Research Findings](#research-findings)
3. [Proposed Solution](#proposed-solution)
4. [Technical Design](#technical-design)
5. [Implementation Plan](#implementation-plan)
6. [Testing Strategy](#testing-strategy)
7. [Risks & Mitigation](#risks--mitigation)
8. [Future Enhancements](#future-enhancements)

---

## Problem Statement

### Current Behavior

The Evennia webclient currently defaults to a fixed screen width of 78 characters (defined by `settings.CLIENT_DEFAULT_WIDTH`) and does not dynamically detect or report the actual browser window dimensions to the server. This results in:

1. **Suboptimal Display**: Text formatting, tables, and combat messages may not fully utilize available screen space
2. **Inconsistent Experience**: Telnet clients automatically negotiate screen size via NAWS protocol (RFC 1073), but webclient users have no equivalent
3. **Manual Configuration Required**: Users must manually set screen dimensions if they want accurate sizing
4. **Combat System Impact**: The G.R.I.M. combat system uses screen width for formatting combat messages, art, and status displays

### Telnet vs Webclient Comparison

| Feature | Telnet (NAWS Protocol) | Webclient (Current) | Webclient (Proposed) |
|---------|------------------------|---------------------|----------------------|
| **Width Detection** | ✅ Automatic | ❌ Static (78 chars) | ✅ Automatic |
| **Height Detection** | ✅ Automatic | ❌ Static (24 lines) | ✅ Automatic |
| **Window Resize** | ✅ Updates on resize | ❌ No updates | ✅ Updates on resize |
| **Font Changes** | ✅ Terminal handles | ❌ No detection | ✅ Detects & updates |
| **Protocol** | Telnet NAWS bytes | None | `client_options` inputfunc |

### User Impact

**Combat System Example:**
```
Current (78 chars):
===============================================================================
|r COMBAT |n Attacker vs Defender
===============================================================================

Desired (120 chars):
========================================================================================================================
|r COMBAT |n Attacker vs Defender - Round 3 - Initiative: 15 vs 12 - Proximity: CLOSE
========================================================================================================================
```

---

## Research Findings

### Evennia Server Architecture

#### 1. Client Options InputFunc

**Location:** `evennia/server/inputfuncs.py` lines 187-267

The server expects screen dimensions via the `client_options` inputfunc:

```python
def client_options(session, *args, **kwargs):
    """
    Handle client option updates.
    
    Kwargs:
        screenwidth (int): Screen width in characters
        screenheight (int): Screen height in lines
        # ... other options
    """
```

**Storage:** Dimensions are stored in `session.protocol_flags`:
```python
session.protocol_flags["SCREENWIDTH"] = {0: width}
session.protocol_flags["SCREENHEIGHT"] = {0: height}
```

**Retrieval:** Commands access dimensions via:
```python
# In Command class
def client_width(self):
    if self.session:
        return self.session.protocol_flags.get(
            "SCREENWIDTH", {0: settings.CLIENT_DEFAULT_WIDTH}
        )[0]
    return settings.CLIENT_DEFAULT_WIDTH

# In ServerSession class
def get_client_size(self):
    flags = self.protocol_flags
    width = flags.get("SCREENWIDTH", {}).get(0, settings.CLIENT_DEFAULT_WIDTH)
    height = flags.get("SCREENHEIGHT", {}).get(0, settings.CLIENT_DEFAULT_HEIGHT)
    return width, height
```

#### 2. Telnet NAWS Protocol

**Location:** `evennia/server/portal/naws.py`

Telnet clients negotiate screen size automatically:
```python
class Naws:
    """
    Implements NAWS (Negotiate About Window Size) - RFC 1073
    """
    def negotiate_sizes(self, width, height):
        """Send screen dimensions via telnet protocol bytes"""
        self.sessionhandler.data_in(
            self.protocol,
            text="",
            type="client_options",
            screenwidth={0: width},
            screenheight={0: height}
        )
```

**Key Insight:** Telnet clients send dimensions via protocol negotiation. Webclient needs JavaScript equivalent.

### Evennia Webclient Architecture

#### 1. Plugin System

**Location:** `evennia/web/static/webclient/js/plugins/`

Evennia webclient uses a plugin-based architecture with standardized callbacks:

```javascript
let plugin_name = (function () {
    // Plugin initialization
    var init = function () {
        console.log('Plugin initialized');
    }
    
    // Called after layout is ready
    var postInit = function () {
        // Setup UI interactions
    }
    
    // Add settings to options dialog
    var onOptionsUI = function (parentdiv) {
        // Add settings controls
    }
    
    // Called when layout changes
    var onLayoutChanged = function () {
        // Respond to layout changes
    }
    
    return {
        init: init,
        postInit: postInit,
        onOptionsUI: onOptionsUI,
        onLayoutChanged: onLayoutChanged
    }
})();
window.plugin_handler.add("plugin_name", plugin_name);
```

#### 2. GoldenLayout Integration

**Location:** `evennia/web/static/webclient/js/plugins/goldenlayout.js`

GoldenLayout manages multiple panes and window resizing:

```javascript
// Line 828: Window resize handler already exists
$(window).bind("resize", scrollAll);

function scrollAll() {
    myLayout.updateSize();
    $(".content").each(function() {
        let scrollHeight = $(this).prop("scrollHeight");
        let clientHeight = $(this).prop("clientHeight");
        $(this).scrollTop(scrollHeight - clientHeight);
    });
}
```

**Key Insight:** Resize handler exists but only updates scroll position, not character dimensions.

#### 3. Font Plugin

**Location:** `evennia/web/static/webclient/js/plugins/font.js`

Users can select font family and size:

```javascript
// Line 67: Font size changes CSS directly
var onFontSize = function (evnt) {
    var size = $(evnt.target).val();
    $(document.body).css("font-size", size+"em");
    localStorage.setItem("evenniaFontSize", size);
}

// Default font: DejaVu Sans Mono at 0.9em
// Sizes range from 0.4em to 2.0em
```

**Key Insight:** Font changes affect character width measurements. Plugin must detect font changes.

#### 4. Message Communication

**Location:** `evennia/web/static/webclient/js/evennia.js`

Client sends messages to server via:

```javascript
// Send client options
Evennia.msg("client_options", [], {
    screenwidth: width,
    screenheight: height
});

// Server receives as inputfunc call
```

**Key Insight:** Communication protocol already established, just need to send dimensions.

### CSS & Font Rendering

**Location:** `evennia/web/static/webclient/css/webclient.css`

```css
/* Line 19: Default monospace font */
body {
    font-size: .9em;
    font-family: 'DejaVu Sans Mono', Consolas, Inconsolata, 'Lucida Console', monospace;
    line-height: 1.4em;
}

/* Line 302: Content divs where text is displayed */
.content {
    border: 1px solid #C0C0C0;
    background-color: black;
    padding: 1rem;
    overflow-y: auto;
}
```

**Key Insight:** Monospace fonts ensure consistent character width, but width varies by font selection.

---

## Proposed Solution

### Overview

Create a new webclient plugin (`screensize.js`) that:

1. **Measures** character dimensions using a hidden test element
2. **Calculates** width and height in characters based on visible content area
3. **Reports** dimensions to server via `client_options` inputfunc
4. **Updates** automatically on window resize, font changes, and layout changes
5. **Integrates** seamlessly with existing plugin architecture

### Design Principles

1. **Non-Invasive**: Plugin-based approach, no core Evennia modifications
2. **Monospace-Aware**: Accurate measurement of monospace character width
3. **Responsive**: Immediate updates on window/font changes
4. **Fault-Tolerant**: Graceful fallback to defaults if measurement fails
5. **Performance-Conscious**: Debounced updates to avoid excessive server communication

---

## Technical Design

### Architecture Diagram

```mermaid
graph TD
    subgraph BROWSER["Browser Window"]
        subgraph GL["GoldenLayout Container"]
            subgraph CONTENT[".content div (Main Pane)"]
                VTA["Visible Text Area\n(calculate character dimensions)"]
            end
        end
        HIDDEN["Hidden Test Element\n#screensize-tester\n(measure monospace char width/height)"]
    end

    RESIZE["Window Resize Event"]
    FONT["Font Change Event"]

    subgraph PLUGIN["screensize.js Plugin"]
        MEASURE["measureCharacterDimensions()"]
        CALC["calculateScreenSize()"]
        SEND["sendDimensionsToServer()"]
        HANDLE["handleResize() — debounced"]
        FONTCHANGE["handleFontChange()"]
    end

    subgraph SERVER["Evennia Server"]
        INPUT["inputfuncs.client_options()"]
        PROTO["session.protocol_flags\nSCREENWIDTH / SCREENHEIGHT"]
        CMD["Command.client_width()"]
    end

    BROWSER --> RESIZE & FONT
    RESIZE --> HANDLE
    FONT --> FONTCHANGE
    HANDLE & FONTCHANGE --> MEASURE --> CALC --> SEND
    SEND -->|"client_options msg"| INPUT --> PROTO --> CMD
```

### Component Design

#### 1. Character Dimension Measurement

**Challenge:** Calculate pixel width/height of a single monospace character.

**Solution:** Create hidden test element with known monospace character.

```javascript
function measureCharacterDimensions() {
    // Create or reuse test element
    let tester = document.getElementById("screensize-tester");
    if (!tester) {
        tester = document.createElement("span");
        tester.id = "screensize-tester";
        tester.style.visibility = "hidden";
        tester.style.position = "absolute";
        tester.style.whiteSpace = "pre";
        tester.style.fontFamily = window.getComputedStyle(document.body).fontFamily;
        tester.style.fontSize = window.getComputedStyle(document.body).fontSize;
        tester.textContent = "M"; // Use 'M' for monospace width
        document.body.appendChild(tester);
    } else {
        // Update font properties in case they changed
        tester.style.fontFamily = window.getComputedStyle(document.body).fontFamily;
        tester.style.fontSize = window.getComputedStyle(document.body).fontSize;
    }
    
    const charWidth = tester.offsetWidth;
    const charHeight = tester.offsetHeight;
    
    return { width: charWidth, height: charHeight };
}
```

**Why 'M'?** In monospace fonts, all characters have the same width. 'M' is typically the widest character in proportional fonts, but in monospace it's standard width.

#### 2. Screen Size Calculation

**Challenge:** Determine how many characters fit in the visible content area.

**Solution:** Find main content div, measure usable area, divide by character dimensions.

```javascript
function calculateScreenSize() {
    // Get character dimensions
    const { width: charWidth, height: charHeight } = measureCharacterDimensions();
    
    if (charWidth === 0 || charHeight === 0) {
        console.warn("screensize: Invalid character dimensions, using defaults");
        return {
            width: 78,  // CLIENT_DEFAULT_WIDTH
            height: 24  // CLIENT_DEFAULT_HEIGHT
        };
    }
    
    // Find the main content div (goldenlayout main pane)
    // Priority: tagged "main", first .content, or fallback to #messagewindow
    let contentDiv = $(".content[types*='main']").first();
    if (contentDiv.length === 0) {
        contentDiv = $(".content").first();
    }
    if (contentDiv.length === 0) {
        contentDiv = $("#messagewindow");
    }
    
    if (contentDiv.length === 0) {
        console.warn("screensize: No content div found, using defaults");
        return { width: 78, height: 24 };
    }
    
    // Get usable area (subtract padding and borders)
    const paddingLeft = parseInt(contentDiv.css("padding-left")) || 0;
    const paddingRight = parseInt(contentDiv.css("padding-right")) || 0;
    const paddingTop = parseInt(contentDiv.css("padding-top")) || 0;
    const paddingBottom = parseInt(contentDiv.css("padding-bottom")) || 0;
    
    const usableWidth = contentDiv.width() - paddingLeft - paddingRight;
    const usableHeight = contentDiv.height() - paddingTop - paddingBottom;
    
    // Calculate character dimensions
    const widthInChars = Math.floor(usableWidth / charWidth);
    const heightInChars = Math.floor(usableHeight / charHeight);
    
    // Sanity checks
    const finalWidth = Math.max(20, Math.min(500, widthInChars)); // 20-500 chars
    const finalHeight = Math.max(10, Math.min(200, heightInChars)); // 10-200 lines
    
    return { width: finalWidth, height: finalHeight };
}
```

#### 3. Server Communication

**Challenge:** Send dimensions to server using established protocol.

**Solution:** Use `client_options` inputfunc via Evennia.msg().

```javascript
function sendDimensionsToServer() {
    const { width, height } = calculateScreenSize();
    
    console.log(`screensize: Reporting dimensions: ${width}x${height}`);
    
    // Send to server via client_options inputfunc
    Evennia.msg("client_options", [], {
        screenwidth: width,
        screenheight: height
    });
}
```

#### 4. Event Handling

**Challenge:** Detect when screen size changes (window resize, font change, layout change).

**Solution:** Hook into multiple event sources with debouncing.

```javascript
// Debounce helper to avoid excessive updates
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Debounced resize handler (500ms delay)
const debouncedResize = debounce(function() {
    console.log("screensize: Window resized");
    sendDimensionsToServer();
}, 500);

// Window resize event
$(window).on("resize", debouncedResize);

// Font change detection
// Hook into font plugin if available
if (window.plugins && window.plugins["font"]) {
    // Wrap font change handlers
    const originalOnFontSize = window.plugins["font"].onFontSize;
    if (originalOnFontSize) {
        window.plugins["font"].onFontSize = function(...args) {
            originalOnFontSize.apply(this, args);
            // Font size changed, remeasure after CSS updates
            setTimeout(sendDimensionsToServer, 100);
        };
    }
    
    const originalOnFontFamily = window.plugins["font"].onFontFamily;
    if (originalOnFontFamily) {
        window.plugins["font"].onFontFamily = function(...args) {
            originalOnFontFamily.apply(this, args);
            // Font family changed, remeasure after CSS updates
            setTimeout(sendDimensionsToServer, 100);
        };
    }
}

// GoldenLayout change event
function onLayoutChanged() {
    console.log("screensize: Layout changed");
    // Give layout time to stabilize
    setTimeout(sendDimensionsToServer, 200);
}
```

**Note on Debouncing:** Window resize events fire continuously while dragging. Debouncing with 500ms delay ensures we only measure after user stops resizing.

#### 5. Initialization

**Challenge:** Send initial dimensions when client connects.

**Solution:** Hook into Evennia connection and GoldenLayout initialization.

```javascript
var init = function () {
    console.log('Screensize plugin initialized');
    
    // Send initial dimensions when connected
    Evennia.emitter.on("connection_open", function() {
        console.log("screensize: Connection opened");
        // Give GoldenLayout time to initialize
        setTimeout(sendDimensionsToServer, 1000);
    });
}

var postInit = function () {
    console.log('Screensize plugin post-init');
    
    // Send dimensions after layout is ready
    setTimeout(sendDimensionsToServer, 500);
}
```

### Full Plugin Code Structure

```javascript
/*
 * Evennia Webclient Screen Size Detection Plugin
 * 
 * Automatically detects browser window dimensions and reports to server
 * via client_options inputfunc, similar to telnet NAWS protocol.
 */

let screensize_plugin = (function () {
    "use strict"
    
    // Configuration
    const DEBOUNCE_DELAY = 500;        // ms to wait after resize
    const MIN_WIDTH = 20;              // minimum reasonable width
    const MAX_WIDTH = 500;             // maximum reasonable width
    const MIN_HEIGHT = 10;             // minimum reasonable height
    const MAX_HEIGHT = 200;            // maximum reasonable height
    const DEFAULT_WIDTH = 78;          // fallback width
    const DEFAULT_HEIGHT = 24;         // fallback height
    
    // Private functions
    function measureCharacterDimensions() { /* ... */ }
    function calculateScreenSize() { /* ... */ }
    function sendDimensionsToServer() { /* ... */ }
    function debounce(func, wait) { /* ... */ }
    
    // Debounced resize handler
    const debouncedResize = debounce(function() {
        sendDimensionsToServer();
    }, DEBOUNCE_DELAY);
    
    // Plugin callbacks
    var init = function () { /* ... */ }
    var postInit = function () { /* ... */ }
    var onLayoutChanged = function () { /* ... */ }
    
    // Public API
    return {
        init: init,
        postInit: postInit,
        onLayoutChanged: onLayoutChanged
    }
})();

// Register plugin
window.plugin_handler.add("screensize", screensize_plugin);
```

---

## Implementation Plan

### Phase 1: Core Plugin Development

**Files to Create:**
- `web/static/webclient/js/plugins/screensize.js`

**Tasks:**
1. ✅ Create plugin skeleton with init/postInit callbacks
2. ✅ Implement `measureCharacterDimensions()` function
3. ✅ Implement `calculateScreenSize()` function
4. ✅ Implement `sendDimensionsToServer()` function
5. ✅ Add debounce utility function
6. ✅ Hook window resize events
7. ✅ Hook Evennia connection events
8. ✅ Add logging and error handling

**Acceptance Criteria:**
- Plugin loads without errors
- Dimensions are measured accurately
- Server receives `client_options` messages
- Window resize triggers updates (debounced)
- Initial dimensions sent on connection

### Phase 2: Font Integration

**Files to Modify:**
- `web/static/webclient/js/plugins/screensize.js` (add font detection)

**Tasks:**
1. ✅ Detect when font plugin changes font size
2. ✅ Detect when font plugin changes font family
3. ✅ Re-measure dimensions after font changes
4. ✅ Update test element with current font properties

**Acceptance Criteria:**
- Font size changes trigger dimension updates
- Font family changes trigger dimension updates
- Measurements use correct font properties

### Phase 3: GoldenLayout Integration

**Files to Modify:**
- `web/static/webclient/js/plugins/screensize.js` (add layout detection)

**Tasks:**
1. ✅ Implement `onLayoutChanged()` callback
2. ✅ Detect when main pane is resized
3. ✅ Detect when layout configuration changes
4. ✅ Target correct content div for measurement

**Acceptance Criteria:**
- Layout changes trigger dimension updates
- Main pane is correctly identified
- Multi-pane layouts are handled gracefully

### Phase 4: Testing & Validation

**Tasks:**
1. ⬜ Test with different fonts (DejaVu, Consolas, Fira Mono, etc.)
2. ⬜ Test with different font sizes (0.4em to 2.0em)
3. ⬜ Test with different window sizes
4. ⬜ Test with different browsers (Chrome, Firefox, Safari, Edge)
5. ⬜ Test with mobile/responsive layouts
6. ⬜ Test with GoldenLayout pane changes
7. ⬜ Verify server receives correct dimensions
8. ⬜ Verify combat system uses new dimensions

**Acceptance Criteria:**
- All manual tests pass
- No console errors
- Dimensions are accurate (±2 characters)
- Server protocol_flags are updated correctly

### Phase 5: Documentation

**Files to Create/Update:**
- `web/static/webclient/js/plugins/README_SCREENSIZE.md` (plugin documentation)
- `CHANGELOG.md` (add feature entry)
- `COMMIT_READY_CHECKLIST.md` (verify against checklist)

**Tasks:**
1. ⬜ Document plugin architecture
2. ⬜ Document configuration options
3. ⬜ Document browser compatibility
4. ⬜ Document known limitations
5. ⬜ Update CHANGELOG with feature description
6. ⬜ Update project documentation if needed

---

## Testing Strategy

### Unit Testing (Manual)

#### Test 1: Character Measurement

**Objective:** Verify accurate monospace character width measurement

**Steps:**
1. Open browser console
2. Run `screensize_plugin.measureCharacterDimensions()`
3. Verify returned width/height are reasonable (e.g., 7-12px width, 14-20px height)
4. Change font size via options
5. Re-run measurement
6. Verify dimensions change proportionally

**Expected:** Character dimensions match CSS-computed font size

#### Test 2: Screen Size Calculation

**Objective:** Verify accurate character-based screen dimensions

**Steps:**
1. Open webclient in 1920x1080 window
2. Check console for dimension report
3. Manually measure content div width in DevTools
4. Calculate expected characters: `(width - padding) / char_width`
5. Compare with reported dimension

**Expected:** Reported width within ±2 characters of calculated

#### Test 3: Window Resize

**Objective:** Verify resize detection and debouncing

**Steps:**
1. Open webclient
2. Note initial dimensions in console
3. Resize window significantly (e.g., half width)
4. Wait 600ms (debounce delay + buffer)
5. Check console for new dimension report

**Expected:** New dimensions reported once, not continuously during resize

#### Test 4: Font Changes

**Objective:** Verify font change detection

**Steps:**
1. Open webclient options
2. Note initial dimensions
3. Change font size from 0.9 to 1.5
4. Wait 200ms
5. Check console for dimension update

**Expected:** New dimensions reflect larger font (fewer characters fit)

### Integration Testing

#### Test 5: Server Communication

**Objective:** Verify server receives dimensions correctly

**Steps:**
1. Connect to game via webclient
2. SSH to server
3. Open Evennia Python shell: `evennia shell`
4. Run:
```python
from evennia.server.sessionhandler import SESSIONS
session = SESSIONS.get()[0]  # First session
width, height = session.get_client_size()
print(f"Width: {width}, Height: {height}")
```

**Expected:** Width/height match webclient console output

#### Test 6: Combat System Integration

**Objective:** Verify G.R.I.M. combat uses correct width

**Steps:**
1. Connect via webclient
2. Resize window to 120+ character width
3. Initiate combat with NPC
4. Observe combat message formatting

**Expected:** Combat messages use full width (not defaulting to 78)

### Browser Compatibility Testing

| Browser | Version | Width Accuracy | Height Accuracy | Resize | Font Change | Status |
|---------|---------|----------------|-----------------|--------|-------------|--------|
| Chrome  | Latest  | ⬜ Test       | ⬜ Test        | ⬜ Test | ⬜ Test    | ⬜ Pass |
| Firefox | Latest  | ⬜ Test       | ⬜ Test        | ⬜ Test | ⬜ Test    | ⬜ Pass |
| Safari  | Latest  | ⬜ Test       | ⬜ Test        | ⬜ Test | ⬜ Test    | ⬜ Pass |
| Edge    | Latest  | ⬜ Test       | ⬜ Test        | ⬜ Test | ⬜ Test    | ⬜ Pass |
| Mobile  | iOS     | ⬜ Test       | ⬜ Test        | ⬜ Test | ⬜ Test    | ⬜ Pass |
| Mobile  | Android | ⬜ Test       | ⬜ Test        | ⬜ Test | ⬜ Test    | ⬜ Pass |

### Performance Testing

#### Test 7: Resize Performance

**Objective:** Verify debouncing prevents excessive server messages

**Steps:**
1. Open browser DevTools Network tab
2. Filter for websocket messages
3. Rapidly resize window multiple times over 2 seconds
4. Count `client_options` messages sent

**Expected:** 1-2 messages sent, not 10+

#### Test 8: Memory Leaks

**Objective:** Verify no memory leaks from event handlers

**Steps:**
1. Open webclient in Chrome DevTools
2. Take heap snapshot
3. Resize window 20 times
4. Force garbage collection
5. Take another heap snapshot
6. Compare retained size

**Expected:** No significant memory growth (< 1MB)

---

## Risks & Mitigation

### Risk 1: Inaccurate Measurements

**Risk:** Character width calculation may be inaccurate due to font rendering differences.

**Probability:** Medium  
**Impact:** Medium

**Mitigation:**
- Use hidden test element with actual monospace character
- Use `offsetWidth` which accounts for actual rendered width
- Apply same font-family and font-size as body element
- Add sanity checks (min/max bounds)
- Provide manual override option in future enhancement

**Fallback:** If measurement fails, default to `CLIENT_DEFAULT_WIDTH` (78)

### Risk 2: Font Plugin Conflicts

**Risk:** Wrapping font plugin handlers could break if plugin architecture changes.

**Probability:** Low  
**Impact:** Medium

**Mitigation:**
- Check for plugin existence before wrapping
- Preserve original handler behavior
- Use try/catch around plugin interaction
- Provide alternative: re-measure periodically (every 60s)

**Fallback:** If font plugin unavailable, only detect window resize (still better than static)

### Risk 3: GoldenLayout Incompatibility

**Risk:** Finding correct content div may fail with custom layouts.

**Probability:** Low  
**Impact:** Low

**Mitigation:**
- Use priority fallback chain: main pane → first .content → #messagewindow
- Test with multiple layout configurations
- Document expected layout structure
- Graceful degradation to defaults

**Fallback:** Measure #messagewindow if GoldenLayout unavailable

### Risk 4: Performance Issues

**Risk:** Frequent measurements could impact browser performance.

**Probability:** Low  
**Impact:** Low

**Mitigation:**
- Debounce resize events (500ms)
- Only measure on significant events (not every frame)
- Cache character dimensions until font changes
- Avoid DOM manipulation during measurement

**Fallback:** Increase debounce delay if performance issues reported

### Risk 5: Mobile/Touch Devices

**Risk:** Mobile devices may report inaccurate dimensions or resize unexpectedly.

**Probability:** Medium  
**Impact:** Low

**Mitigation:**
- Test on iOS and Android
- Handle orientation changes
- Account for virtual keyboard appearance
- Consider device-specific CSS (@media queries)

**Fallback:** Mobile users can use static defaults if dynamic detection problematic

---

## Future Enhancements

### Phase 6: Manual Override Option

**Description:** Allow users to manually set dimensions via options dialog.

**UI Design:**
```
Options Dialog:
├── Screen Size Detection
│   ├── [x] Auto-detect screen size (recommended)
│   ├── Manual Width: [____] characters (disabled if auto)
│   └── Manual Height: [____] lines (disabled if auto)
```

**Benefits:**
- Users can override if automatic detection inaccurate
- Useful for accessibility tools
- Allows users to prefer specific width (e.g., 80 chars for nostalgia)

### Phase 7: Orientation Change Detection

**Description:** Detect mobile device orientation changes.

**Implementation:**
```javascript
window.addEventListener("orientationchange", function() {
    setTimeout(sendDimensionsToServer, 300);
});
```

**Benefits:**
- Better mobile experience
- Handles tablet rotation
- Responsive to device context

### Phase 8: Visibility Change Optimization

**Description:** Pause measurements when tab is not visible.

**Implementation:**
```javascript
document.addEventListener("visibilitychange", function() {
    if (document.hidden) {
        // Pause resize listener
    } else {
        // Resume and re-measure
        sendDimensionsToServer();
    }
});
```

**Benefits:**
- Reduced CPU usage when tab backgrounded
- Battery savings on mobile
- Still updates when user returns

### Phase 9: Advanced Telemetry

**Description:** Optional telemetry to help tune defaults.

**Data Collected (anonymously):**
- Screen width distribution (histogram)
- Font preferences (which fonts/sizes most common)
- Browser/OS combinations
- Mobile vs desktop ratio

**Benefits:**
- Improve default values based on real usage
- Identify common screen sizes for testing
- Optimize font recommendations

**Privacy:** Only if user opts in, all data anonymized

---

## Appendices

### Appendix A: Evennia File Locations

**Server-Side:**
```
evennia/server/
├── inputfuncs.py              # client_options() handler
├── serversession.py           # get_client_size() method
└── portal/
    └── naws.py                # Telnet NAWS reference implementation
```

**Webclient:**
```
evennia/web/
├── static/webclient/
│   ├── js/
│   │   ├── evennia.js         # Core websocket communication
│   │   └── plugins/
│   │       ├── goldenlayout.js    # Window management
│   │       ├── font.js            # Font selection
│   │       └── options2.js        # Options system
│   └── css/
│       └── webclient.css      # Default styling
└── templates/webclient/
    └── base.html              # Plugin loading order
```

**Our Implementation:**
```
mygame/web/static/webclient/js/plugins/
└── screensize.js              # New plugin (this spec)
```

### Appendix B: Browser API Reference

**Character Width Measurement:**
```javascript
// Create test element
const span = document.createElement("span");
span.textContent = "M";
span.style.fontFamily = "monospace";
span.style.fontSize = "1em";
span.style.visibility = "hidden";
document.body.appendChild(span);

// Measure
const width = span.offsetWidth;   // Actual rendered width
const height = span.offsetHeight; // Actual rendered height

// Clean up
document.body.removeChild(span);
```

**Computed Styles:**
```javascript
const styles = window.getComputedStyle(element);
const fontSize = styles.fontSize;      // e.g., "14.4px"
const fontFamily = styles.fontFamily;  // e.g., "DejaVu Sans Mono, monospace"
```

**jQuery Dimension Methods:**
```javascript
const $div = $(".content").first();
const width = $div.width();            // Inner width (no padding/border)
const outerWidth = $div.outerWidth();  // Includes padding/border
const padding = {
    left: parseInt($div.css("padding-left")),
    right: parseInt($div.css("padding-right"))
};
```

### Appendix C: Protocol Flags Structure

**Database Storage:**
```python
# In ServerSession
self.protocol_flags = {
    "SCREENWIDTH": {
        0: 120  # windowID 0 (main window) is 120 characters wide
    },
    "SCREENHEIGHT": {
        0: 40   # windowID 0 is 40 lines tall
    },
    # Other flags...
}
```

**Why `{0: width}` format?**
Evennia supports multiple windows per session (though webclient currently only uses one). WindowID 0 is the main window. This structure allows future expansion for multi-window support.

### Appendix D: Monospace Font Considerations

**Why Monospace Matters:**
- All characters have identical width
- Simplifies column-based formatting
- Tables and ASCII art align correctly
- Single measurement represents all characters

**Default Fonts (in priority order):**
1. DejaVu Sans Mono (custom webfont)
2. Consolas (Windows)
3. Inconsolata (Google Fonts)
4. Lucida Console (fallback)
5. Generic monospace (system default)

**Font Size Scaling:**
```
Base: 1.0em = ~10px character width
0.4em = ~4px  → ~200 chars @ 1920px width
0.9em = ~9px  → ~110 chars @ 1920px width (default)
2.0em = ~20px → ~50 chars  @ 1920px width
```

### Appendix E: Glossary

| Term | Definition |
|------|------------|
| **NAWS** | Negotiate About Window Size - Telnet protocol (RFC 1073) for screen size negotiation |
| **inputfunc** | Evennia server-side function that processes client input messages |
| **protocol_flags** | Server-side storage for client capabilities and settings |
| **GoldenLayout** | JavaScript library for drag-and-drop window management |
| **Debouncing** | Delaying function execution until after rapid events stop firing |
| **Monospace Font** | Font where all characters have identical width (e.g., Courier, Consolas) |
| **em** | CSS unit relative to font size (1em = current font size) |
| **offsetWidth** | DOM property returning element's rendered width including padding/border |
| **clientWidth** | DOM property returning element's inner width excluding borders |
| **Evennia.msg()** | Client-side function to send messages to Evennia server |
| **Plugin Callback** | Function called by plugin system at specific lifecycle points |

---

## Approval & Sign-Off

**Specification Status:** ⬜ Draft → ⬜ Review → ⬜ Approved → ⬜ Implemented

**Reviewed By:** _________________  
**Date:** _________________  

**Approved By:** _________________  
**Date:** _________________  

**Implementation Assigned To:** _________________  
**Target Completion:** _________________  

---

**Document History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-XX | AI Agent | Initial draft based on comprehensive research |

---

**Related Documents:**
- `AGENTS.md` - G.R.I.M. Combat System architecture reference
- `PROJECT_OVERVIEW.md` - Overall project context
- `specs/COMBAT_SYSTEM.md` - Combat system user documentation
- Evennia Documentation: [Web Client](https://www.evennia.com/docs/latest/Components/Webclient.html)
- Evennia Documentation: [Inputfuncs](https://www.evennia.com/docs/latest/Components/Inputfuncs.html)
- RFC 1073: [Telnet NAWS Protocol](https://www.ietf.org/rfc/rfc1073.txt)

---

**End of Specification**
