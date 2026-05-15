"use strict";
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, LevelFormat, TableOfContents,
} = require("docx");
const fs = require("fs");

// ── Colour palette ───────────────────────────────────────────────────────────
const C = {
  navy:      "1B3A5C",
  teal:      "0D7377",
  gold:      "C8860A",
  red:       "C0392B",
  green:     "1A7A4A",
  lightBlue: "EAF4FB",
  lightGold: "FEF9EC",
  lightRed:  "FDECEA",
  lightGreen:"EAF7F0",
  lightGray: "F5F5F5",
  midGray:   "DDDDDD",
  white:     "FFFFFF",
  black:     "1A1A1A",
};

// ── Border helpers ───────────────────────────────────────────────────────────
const bdr = (color = C.midGray, size = 4) => ({
  top:    { style: BorderStyle.SINGLE, size, color },
  bottom: { style: BorderStyle.SINGLE, size, color },
  left:   { style: BorderStyle.SINGLE, size, color },
  right:  { style: BorderStyle.SINGLE, size, color },
});
const noBorder = () => ({
  top:    { style: BorderStyle.NONE, size: 0, color: C.white },
  bottom: { style: BorderStyle.NONE, size: 0, color: C.white },
  left:   { style: BorderStyle.NONE, size: 0, color: C.white },
  right:  { style: BorderStyle.NONE, size: 0, color: C.white },
});

// ── Page geometry (US Letter, 1-inch margins) ────────────────────────────────
const PAGE_W   = 12240;
const MARGIN   = 1440;
const CONTENT  = PAGE_W - MARGIN * 2; // 9360

// ── Typography helpers ───────────────────────────────────────────────────────
const run  = (text, opts = {}) => new TextRun({ text, font: "Arial", ...opts });
const bold = (text, opts = {}) => run(text, { bold: true, ...opts });

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    children: [new TextRun({ text, font: "Arial", bold: true, size: 36, color: C.navy })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120 },
    children: [new TextRun({ text, font: "Arial", bold: true, size: 28, color: C.teal })],
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, font: "Arial", bold: true, size: 24, color: C.navy })],
  });
}
function h4(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_4,
    spacing: { before: 160, after: 60 },
    children: [new TextRun({ text, font: "Arial", bold: true, size: 22, color: C.black })],
  });
}
function body(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [run(text, { size: 20, ...opts })],
  });
}
function spacer(n = 1) {
  return Array.from({ length: n }, () =>
    new Paragraph({ spacing: { before: 0, after: 0 }, children: [run("")] })
  );
}
function pageBreak() {
  return new Paragraph({
    pageBreakBefore: true,
    children: [run("")],
  });
}

// ── Bullet helpers ───────────────────────────────────────────────────────────
function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: [run(text, { size: 20 })],
  });
}
function step(num, text) {
  return new Paragraph({
    numbering: { reference: "steps", level: 0 },
    spacing: { before: 60, after: 60 },
    children: [run(text, { size: 20 })],
  });
}
function subBullet(text) {
  return bullet(text, 1);
}

// ── Code block ───────────────────────────────────────────────────────────────
function code(text) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    indent: { left: 360 },
    children: [new TextRun({ text, font: "Courier New", size: 18, color: "2E5090" })],
  });
}

// ── Coloured box ─────────────────────────────────────────────────────────────
function box(label, text, fillColor = C.lightBlue, labelColor = C.navy) {
  const rows = [
    new TableRow({
      children: [
        new TableCell({
          borders: bdr(labelColor, 6),
          shading: { fill: labelColor, type: ShadingType.CLEAR },
          margins: { top: 60, bottom: 60, left: 120, right: 120 },
          width: { size: CONTENT, type: WidthType.DXA },
          children: [new Paragraph({ children: [bold(label, { size: 18, color: C.white })] })],
        }),
      ],
    }),
    new TableRow({
      children: [
        new TableCell({
          borders: bdr(labelColor, 6),
          shading: { fill: fillColor, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 160, right: 160 },
          width: { size: CONTENT, type: WidthType.DXA },
          children: Array.isArray(text)
            ? text
            : [new Paragraph({ spacing: { before: 40, after: 40 }, children: [run(text, { size: 20 })] })],
        }),
      ],
    }),
  ];
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: [CONTENT],
    rows,
  });
}

function passBox(items) {
  return box(
    "✅  EXPECTED RESULT (PASS CRITERIA)",
    Array.isArray(items)
      ? items.map(t => new Paragraph({ spacing: { before: 30, after: 30 }, children: [run("✓  " + t, { size: 20 })] }))
      : [new Paragraph({ children: [run(items, { size: 20 })] })],
    C.lightGreen, C.green
  );
}
function failBox(items) {
  return box(
    "❌  COMMON FAILURE MODES",
    Array.isArray(items)
      ? items.map(t => new Paragraph({ spacing: { before: 30, after: 30 }, children: [run("✗  " + t, { size: 20 })] }))
      : [new Paragraph({ children: [run(items, { size: 20 })] })],
    C.lightRed, C.red
  );
}
function prereqBox(items) {
  return box(
    "⚙  PREREQUISITES",
    Array.isArray(items)
      ? items.map(t => new Paragraph({ spacing: { before: 30, after: 30 }, children: [run("•  " + t, { size: 20 })] }))
      : [new Paragraph({ children: [run(items, { size: 20 })] })],
    C.lightGold, C.gold
  );
}
function noteBox(text) {
  return box("📝  NOTE", text, C.lightBlue, C.teal);
}

// ── Generic 2-column table ────────────────────────────────────────────────────
function twoCol(rows, colWidths = [3120, 6240], headerFill = C.navy) {
  const [w0, w1] = colWidths;
  const headerRow = new TableRow({
    tableHeader: true,
    children: rows[0].map((cell, i) =>
      new TableCell({
        borders: bdr(C.navy),
        shading: { fill: headerFill, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        width: { size: colWidths[i], type: WidthType.DXA },
        children: [new Paragraph({ children: [bold(cell, { size: 18, color: C.white })] })],
      })
    ),
  });
  const dataRows = rows.slice(1).map((r, ri) =>
    new TableRow({
      children: r.map((cell, i) =>
        new TableCell({
          borders: bdr(C.midGray, 3),
          shading: { fill: ri % 2 === 0 ? C.white : C.lightGray, type: ShadingType.CLEAR },
          margins: { top: 50, bottom: 50, left: 100, right: 100 },
          width: { size: colWidths[i], type: WidthType.DXA },
          children: [new Paragraph({ spacing: { before: 20, after: 20 }, children: [run(cell, { size: 18 })] })],
        })
      ),
    })
  );
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRow, ...dataRows],
  });
}

// ── Three-column table ────────────────────────────────────────────────────────
function threeCol(rows, colWidths = [2500, 3430, 3430], headerFill = C.navy) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: rows[0].map((cell, i) =>
      new TableCell({
        borders: bdr(C.navy),
        shading: { fill: headerFill, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        width: { size: colWidths[i], type: WidthType.DXA },
        children: [new Paragraph({ children: [bold(cell, { size: 18, color: C.white })] })],
      })
    ),
  });
  const dataRows = rows.slice(1).map((r, ri) =>
    new TableRow({
      children: r.map((cell, i) =>
        new TableCell({
          borders: bdr(C.midGray, 3),
          shading: { fill: ri % 2 === 0 ? C.white : C.lightGray, type: ShadingType.CLEAR },
          margins: { top: 50, bottom: 50, left: 100, right: 100 },
          width: { size: colWidths[i], type: WidthType.DXA },
          children: [new Paragraph({ spacing: { before: 20, after: 20 }, children: [run(cell, { size: 18 })] })],
        })
      ),
    })
  );
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRow, ...dataRows],
  });
}

// ── Divider ───────────────────────────────────────────────────────────────────
function divider() {
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.teal, space: 1 } },
    children: [run("")],
  });
}

// ── Test-case wrapper (numbered heading + steps) ──────────────────────────────
let _tcCounter = 0;
function tc(id, title, prereqs, steps, pass, fail, notes) {
  const elems = [];
  elems.push(h3(`TC-${id}: ${title}`));
  if (prereqs && prereqs.length) elems.push(prereqBox(prereqs));
  elems.push(...spacer(1));
  elems.push(body("Steps:", { bold: true }));
  steps.forEach((s, i) => {
    if (typeof s === "string") {
      elems.push(new Paragraph({
        spacing: { before: 60, after: 40 },
        indent: { left: 0 },
        children: [
          bold(`${i + 1}.  `, { size: 20 }),
          run(s, { size: 20 }),
        ],
      }));
    } else {
      // object with { text, cmd } — show command in monospace
      elems.push(new Paragraph({
        spacing: { before: 60, after: 20 },
        children: [bold(`${i + 1}.  `, { size: 20 }), run(s.text, { size: 20 })],
      }));
      if (s.cmd) elems.push(code("    " + s.cmd));
    }
  });
  elems.push(...spacer(1));
  if (pass) elems.push(passBox(Array.isArray(pass) ? pass : [pass]));
  if (fail) { elems.push(...spacer(1)); elems.push(failBox(Array.isArray(fail) ? fail : [fail])); }
  if (notes) { elems.push(...spacer(1)); elems.push(noteBox(notes)); }
  elems.push(...spacer(1));
  elems.push(divider());
  return elems;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOCUMENT BODY
// ═══════════════════════════════════════════════════════════════════════════════
const children = [];

// ── Cover Page ────────────────────────────────────────────────────────────────
children.push(
  ...spacer(6),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 120 },
    children: [new TextRun({ text: "VIBE TRADING", font: "Arial", size: 72, bold: true, color: C.navy })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 80 },
    children: [new TextRun({ text: "India Trade CLI", font: "Arial", size: 44, color: C.teal })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 200 },
    children: [new TextRun({ text: "Complete Testing Guide", font: "Arial", size: 36, bold: true, color: C.gold })],
  }),
  divider(),
  ...spacer(2),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [run("End-to-end test flows, acceptance criteria, edge cases & failure modes", { size: 22, color: C.teal })],
  }),
  ...spacer(2),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [run("Version 1.0  ·  May 2026  ·  For Codex QA Review", { size: 20, color: "888888" })],
  }),
  pageBreak(),
);

// ── Table of Contents ─────────────────────────────────────────────────────────
children.push(
  h1("Table of Contents"),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  pageBreak(),
);

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 1 — TEST ENVIRONMENT SETUP
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("1.  Test Environment Setup"));
children.push(body("Before running any test, verify the following are in place:"));
children.push(...spacer(1));

children.push(h2("1.1  System Requirements"));
children.push(twoCol([
  ["Requirement", "Value / Command"],
  ["Python version", "3.11, 3.12, or 3.13"],
  ["Install dependencies", "pip install -e \".[dev]\""],
  ["Run all fast tests", "pytest tests/ -m \"not network and not slow\" -n auto"],
  ["Node.js (doc generation)", "v18+ (node --version)"],
  ["macOS Keychain / Secret Service", "Required for credentials storage"],
], [3200, 6160]));

children.push(...spacer(1), h2("1.2  Environment Variables (.env or keychain)"));
children.push(body("Create a .env file at the project root with at least one broker configured:"));
children.push(code("# Minimum for demo / yfinance testing (no broker)"));
children.push(code("AI_PROVIDER=anthropic"));
children.push(code("ANTHROPIC_API_KEY=sk-ant-..."));
children.push(...spacer(1));
children.push(body("Optional (for live broker testing):"));
children.push(code("KITE_API_KEY=...    KITE_API_SECRET=..."));
children.push(code("FYERS_APP_ID=...    FYERS_SECRET_KEY=..."));
children.push(code("ANGEL_API_KEY=...   ANGEL_CLIENT_CODE=...  ANGEL_PASSWORD=...  ANGEL_TOTP_SECRET=..."));
children.push(...spacer(1));

children.push(h2("1.3  Starting the CLI"));
children.push(twoCol([
  ["Mode", "Command"],
  ["Demo / no broker", "trade --no-broker"],
  ["Live (Zerodha)", "trade  (then select 2 from broker menu)"],
  ["Live (Angel One)", "trade  (then select 3 — TOTP auto-login)"],
  ["Live (Fyers)", "trade  (then select 5 from broker menu)"],
  ["TUI mode", "trade --tui"],
], [3200, 6160]));

children.push(...spacer(1));
children.push(noteBox("All test cases below use --no-broker (demo mode) unless a live broker section is explicitly indicated. Output values will vary; focus on structure, not exact numbers."));
children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 2 — STARTUP & REPL SHELL
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("2.  Startup & REPL Shell"));

children.push(...tc(
  "01", "CLI starts in demo mode",
  ["Python 3.11+ installed", "pip install -e . completed"],
  [
    { text: "Run the CLI in no-broker mode:", cmd: "trade --no-broker" },
    "Observe the banner printed to terminal.",
    "Confirm the REPL prompt appears.",
  ],
  [
    "ASCII art banner displays without errors",
    "Line '[dim] Running without broker... Using yfinance' appears",
    "REPL prompt (e.g. 'trade> ' or similar) is ready for input",
  ],
  ["ImportError on startup → run: pip install -e \".[dev]\"",
   "ModuleNotFoundError for 'rich' → pip install rich"],
  "On first run the web server on port 8765 also starts in the background."
));

children.push(...tc(
  "02", "help command",
  ["CLI started (TC-01 passed)"],
  [
    { text: "Type at the REPL prompt:", cmd: "help" },
    "Scroll through the output.",
  ],
  [
    "Formatted Rich panels displayed for each command group",
    "All major commands listed: quote, analyze, backtest, alert, credentials, etc.",
    "No tracebacks or errors",
  ],
  ["If only a short list prints, check that app/repl.py loaded correctly"],
));

children.push(...tc(
  "03", "quit / exit",
  ["CLI started"],
  [
    { text: "Type:", cmd: "quit" },
  ],
  ["'Goodbye.' message printed", "Process exits with code 0"],
  ["Hangs → Ctrl-C; investigate event loop not closing"],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 3 — CREDENTIALS MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("3.  Credentials Management"));

children.push(...tc(
  "04", "List all credentials",
  ["CLI started"],
  [
    { text: "Run:", cmd: "credentials" },
    "Observe the table rendered.",
  ],
  [
    "Table with columns: Key, Label, Keychain, Env/.env, Status",
    "Each row shows ● (set) or ○ (not set) per source",
    "Status column shows ✓ Set or ✗ Missing",
    "All known keys listed: KITE_API_KEY, ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, etc.",
  ],
  ["Table empty → keychain library not installed; run: pip install keyring"],
));

children.push(...tc(
  "05", "Set a single credential",
  ["CLI started"],
  [
    { text: "Run:", cmd: "credentials set ANTHROPIC_API_KEY" },
    "When prompted, enter a test value (e.g. sk-ant-test).",
    "Run 'credentials' again to verify.",
  ],
  [
    "Prompt appears: 'Enter value for ANTHROPIC_API_KEY:'",
    "After entry: '✓ Saved ANTHROPIC_API_KEY to keychain'",
    "'credentials' table shows ● in Keychain column for that key",
  ],
  ["Keychain write failure → check OS permissions; on Linux ensure libsecret is installed"],
));

children.push(...tc(
  "06", "Delete a credential",
  ["TC-05 completed — ANTHROPIC_API_KEY stored in keychain"],
  [
    { text: "Run:", cmd: "credentials delete ANTHROPIC_API_KEY" },
    "Confirm the deletion when prompted.",
    "Run 'credentials' and verify keychain column shows ○.",
  ],
  [
    "Confirmation prompt appears",
    "'✓ Deleted ANTHROPIC_API_KEY from keychain'",
    "Table shows ○ in Keychain for that key",
  ],
  ["If key not found → 'Key not in keychain' warning (non-fatal)"],
));

children.push(...tc(
  "07", "credentials setup wizard",
  ["CLI started", "No credentials configured yet (fresh install)"],
  [
    { text: "Run:", cmd: "credentials setup" },
    "Follow the interactive wizard — enter dummy values when prompted.",
    "Exit with Ctrl-C after testing one section.",
  ],
  [
    "Wizard groups keys by broker (Zerodha, Fyers, AI, etc.)",
    "Each key prompted in order with a description",
    "'Saved to keychain' confirms each entry",
    "Ctrl-C gracefully exits without corrupting stored values",
  ],
  ["Wizard loops forever → press Ctrl-C to exit cleanly"],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 4 — BROKER CONNECT / DISCONNECT
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("4.  Broker Connect & Disconnect"));

children.push(...tc(
  "08", "Demo mode (no broker login)",
  ["CLI started with: trade --no-broker"],
  [
    { text: "Run any data command:", cmd: "quote NIFTY" },
    "Observe header of the output table.",
  ],
  [
    "Quote table displays with simulated/yfinance data",
    "Yellow dim banner: '(Demo mode — data below is simulated...)'",
    "No crash or authentication error",
  ],
  ["yfinance rate-limit → wait 60 seconds; NSE symbol formats differ from Yahoo symbols"],
  "Demo mode uses yfinance as data source. Symbol must be Yahoo-compatible (e.g. RELIANCE.NS). The REPL auto-appends .NS for NSE symbols."
));

children.push(...tc(
  "09", "Broker login menu",
  ["CLI started without --no-broker", "At least one broker's API key stored in keychain"],
  [
    { text: "Start CLI:", cmd: "trade" },
    "Observe the broker selection menu (0–5).",
    "Choose 0 (Demo mode) to verify the menu works without real credentials.",
  ],
  [
    "Menu displays: 0 Demo, 1 Zerodha, 2 Groww, 3 Angel One, 4 Upstox, 5 Fyers",
    "Selecting 0 → proceeds to REPL in demo mode (same as --no-broker)",
    "Menu re-prompts on invalid input",
  ],
  ["Menu not showing → check app/main.py for startup flow; verify rich installed"],
));

children.push(...tc(
  "10", "Angel One TOTP auto-login",
  ["ANGEL_API_KEY, ANGEL_CLIENT_CODE, ANGEL_PASSWORD, ANGEL_TOTP_SECRET all stored",
   "smartapi-python installed: pip install smartapi-python logzero"],
  [
    { text: "Start CLI:", cmd: "trade" },
    "Select 3 (Angel One) from the menu.",
    "Observe auto-login (no browser, no manual TOTP entry).",
  ],
  [
    "No browser opens — login happens automatically in background",
    "REPL starts with 'Connected: Angel One' status",
    "funds or profile command returns real account data",
  ],
  [
    "TOTP error → ANGEL_TOTP_SECRET is wrong; run: credentials delete ANGEL_TOTP_SECRET then re-enter",
    "Password error → ANGEL_PASSWORD incorrect in keychain",
    "'smartapi-python not installed' → pip install smartapi-python logzero",
  ],
));

children.push(...tc(
  "11", "Add second broker (connect)",
  ["Primary broker already logged in"],
  [
    { text: "In REPL, add a second broker:", cmd: "connect 5" },
    "Complete the Fyers OAuth flow (browser opens).",
    { text: "Check connected brokers:", cmd: "brokers" },
  ],
  [
    "Browser opens to Fyers auth URL",
    "After OAuth: 'Connected Fyers (secondary).'",
    "'brokers' table shows both primary and Fyers with roles: primary=execution, secondary=data",
    "If both Fyers and Zerodha present: auto-role assignment shown (Fyers=data, Zerodha=execution)",
  ],
  ["OAuth redirect fails → ensure http://localhost:8765/fyers/callback is registered in Fyers app console"],
));

children.push(...tc(
  "12", "Disconnect a broker",
  ["Two brokers connected (TC-11 completed)"],
  [
    { text: "Disconnect Fyers:", cmd: "disconnect fyers" },
    { text: "Verify only primary remains:", cmd: "brokers" },
  ],
  [
    "'Disconnected fyers.' message",
    "'brokers' table shows only the primary broker",
    "All subsequent commands route to remaining broker",
  ],
  ["Unknown broker name → 'No broker named X connected'; check spelling"],
));

children.push(...tc(
  "13", "Set broker role via API",
  ["Two brokers connected", "Web server running on port 8765"],
  [
    { text: "Send role assignment via curl:", cmd: "curl -X POST http://localhost:8765/api/broker/role -H 'Content-Type: application/json' -d '{\"broker\":\"fyers\",\"role\":\"data\"}'" },
    { text: "Verify role changed:", cmd: "brokers" },
  ],
  [
    "API returns: {\"status\": \"ok\", \"broker\": \"fyers\", \"role\": \"data\"}",
    "brokers table reflects updated role",
  ],
  ["404 on /api/broker/role → web server not started; run: web in REPL first"],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 5 — MARKET DATA COMMANDS
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("5.  Market Data Commands"));

children.push(...tc(
  "14", "Single quote",
  ["CLI started (demo or live)"],
  [
    { text: "Run:", cmd: "quote RELIANCE" },
    "Observe the output table.",
  ],
  [
    "Table with columns: Symbol, LTP, Open, High, Low, Vol, Change, Change%",
    "LTP value is a positive number (₹ formatted)",
    "Change% colored green (positive) or red (negative)",
    "Single row for RELIANCE",
  ],
  ["'Symbol not found' → try RELIANCE.NS in demo mode; live brokers accept bare NSE symbols"],
));

children.push(...tc(
  "15", "Multi-symbol quote",
  ["CLI started"],
  [
    { text: "Run:", cmd: "quote RELIANCE INFY TCS HDFCBANK NIFTY" },
    "Verify all 5 symbols appear.",
  ],
  [
    "Table has 5 rows, one per symbol",
    "All columns populated for each symbol",
    "No duplicate rows",
  ],
  ["Partial results (some missing) → that symbol unavailable in data source; expected in demo mode for some symbols"],
));

children.push(...tc(
  "16", "Morning brief",
  ["CLI started", "AI provider key configured (ANTHROPIC_API_KEY or GEMINI_API_KEY)"],
  [
    { text: "Run:", cmd: "morning-brief" },
    "Wait 15–30 seconds for AI generation.",
  ],
  [
    "Narrative text printed: market context, FII/DII flows, key levels, sector highlights",
    "No traceback",
    "Response is India-specific (mentions NIFTY/SENSEX, not S&P 500 primarily)",
  ],
  ["Timeout → AI provider key invalid or rate-limited; check ANTHROPIC_API_KEY"],
  "morning-brief calls multiple data tools internally (flows, macro, earnings) then synthesises via LLM."
));

children.push(...tc(
  "17", "FII/DII flows",
  ["CLI started"],
  [
    { text: "Run:", cmd: "flows" },
  ],
  [
    "Table with columns: FII Buy, FII Sell, DII Buy, DII Sell, Net Flow, Signal",
    "Signal is BULLISH / BEARISH / NEUTRAL",
    "Numbers are in crores (₹Cr format)",
  ],
  ["All zeros → data source unreachable in demo mode; expected behaviour"],
));

children.push(...tc(
  "18", "Macro snapshot",
  ["CLI started"],
  [
    { text: "Run:", cmd: "macro" },
  ],
  [
    "USD/INR rate, Brent Crude price, Gold price displayed",
    "Directional arrows or colour indicators for trend",
    "India-specific macro linkage commentary (e.g. crude impact on OMCs)",
  ],
  [],
));

children.push(...tc(
  "19", "Earnings calendar",
  ["CLI started"],
  [
    { text: "Run:", cmd: "earnings" },
    { text: "Also test with symbol filter:", cmd: "earnings INFY" },
  ],
  [
    "Table: Company, Date, Next Earnings Date, Consensus EPS",
    "With symbol filter: only INFY rows",
    "Dates are in future or recent past",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 6 — PORTFOLIO & ACCOUNT COMMANDS
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("6.  Portfolio & Account Commands"));

children.push(...tc(
  "20", "funds",
  ["CLI started (demo or live)"],
  [
    { text: "Run:", cmd: "funds" },
  ],
  [
    "Shows: Available Cash, Used Margin, Total Balance",
    "Demo mode: simulated values with yellow dim banner",
    "Live mode: real broker margin values",
  ],
  ["Expired session → 'Your broker session may have expired. Try: logout → login'"],
));

children.push(...tc(
  "21", "profile",
  ["CLI started (live broker preferred)"],
  [
    { text: "Run:", cmd: "profile" },
  ],
  [
    "Key-value pairs: Name, Client ID, Email, Broker",
    "Live mode: real account name from broker API",
    "Demo mode: simulated profile",
  ],
  [],
));

children.push(...tc(
  "22", "holdings",
  ["Live broker connected with actual holdings, OR demo mode"],
  [
    { text: "Run:", cmd: "holdings" },
    "Verify each column is populated.",
  ],
  [
    "Table columns: Symbol, Qty, Avg, LTP, Today P&L, Today %, Overall P&L, Overall %",
    "P&L values colour-coded: green positive, red negative",
    "Demo mode: simulated positions shown",
  ],
  ["Empty table → no holdings in account (valid state, not a bug)"],
));

children.push(...tc(
  "23", "positions (intraday)",
  ["Live broker OR demo mode"],
  [
    { text: "Run:", cmd: "positions" },
  ],
  [
    "Table: Symbol, Product, Qty (± for long/short), Avg, LTP, P&L",
    "Product is CNC / MIS / NRML",
    "Empty outside market hours is normal",
  ],
  [],
));

children.push(...tc(
  "24", "orders",
  ["Live broker OR demo mode"],
  [
    { text: "Run:", cmd: "orders" },
  ],
  [
    "Table: Order ID (truncated), Symbol, Type (BUY/SELL), Qty, Price, Status",
    "Status values: COMPLETE, OPEN, REJECTED, CANCELLED",
    "Demo mode shows simulated orders or empty list",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 7 — ANALYSIS & AI COMMANDS
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("7.  Analysis & AI Commands"));

children.push(...tc(
  "25", "Quick analysis (analyze)",
  ["CLI started", "AI provider key configured"],
  [
    { text: "Run:", cmd: "analyze RELIANCE" },
    "Wait 10–20 seconds.",
    "Observe the scorecard output.",
  ],
  [
    "AnalystScorecard panel displayed",
    "Overall Rating: 0–100",
    "Direction: BUY / SELL / HOLD",
    "7 analyst reports listed (Technical, Fundamental, Options, NewsMacro, Sentiment, SectorRotation, Risk)",
    "Each report shows rating, direction, confidence, key findings",
    "Debate summary shown (consensus / disagreements)",
    "Trade recommendations for 3 risk personas (conservative / balanced / aggressive)",
  ],
  ["Timeout → AI provider rate limit; wait 60s and retry",
   "Missing analyst report → that analyst module failed silently; check logs"],
));

children.push(...tc(
  "26", "Deep analysis (deep-analyze)",
  ["CLI started", "AI provider key configured"],
  [
    { text: "Run:", cmd: "deep-analyze INFY" },
    "Wait 30–60 seconds.",
  ],
  [
    "11 analyst reports (4 additional LLM-only analysts vs analyze)",
    "Full narrative text per analyst (not just key findings)",
    "Longer, more detailed trade plans",
    "No truncation in output",
  ],
  ["Takes >60s → expected on slow AI providers; not a bug unless it never completes"],
));

children.push(...tc(
  "27", "Quick scorecard (quick)",
  ["CLI started", "AI provider configured"],
  [
    { text: "Run:", cmd: "quick TCS" },
  ],
  [
    "Output in ~5 seconds (faster than analyze)",
    "Condensed scorecard: overall rating + direction + top 3 signals",
    "No full analyst debate",
  ],
  [],
));

children.push(...tc(
  "28", "AI free-text chat (ai)",
  ["CLI started", "AI provider key configured"],
  [
    { text: "Run:", cmd: "ai \"What should I trade today in Indian markets?\"" },
    "Observe the response.",
  ],
  [
    "Free-form LLM response relevant to Indian markets",
    "References NIFTY / NSE context",
    "Response is coherent prose (not JSON)",
  ],
  ["Generic non-India response → AI_PROVIDER env var may point to a model without India context"],
));

children.push(...tc(
  "29", "Fundamentals",
  ["CLI started"],
  [
    { text: "Run:", cmd: "fundamentals HDFC" },
  ],
  [
    "India-specific fundamental metrics displayed",
    "Columns include: ROE, Net Profit Margin, Debt-to-Equity, Pledge %",
    "Values shown for most recent reported period",
  ],
  [],
));

children.push(...tc(
  "30", "Sentiment analysis",
  ["CLI started", "NEWSAPI_KEY or EXA_API_KEY configured for live data (optional)"],
  [
    { text: "Run:", cmd: "sentiment WIPRO" },
  ],
  [
    "Sentiment score (0–100 or -100 to +100) displayed",
    "Breakdown: News sentiment, FII activity, Bulk deals",
    "Key positive/negative keywords listed",
  ],
  ["All zeros → news API key not set; sentiment uses simulated data in demo mode"],
));

children.push(...tc(
  "31", "Ensemble signals",
  ["CLI started"],
  [
    { text: "Run:", cmd: "ensemble NIFTY" },
  ],
  [
    "5 signals shown: Trend, Momentum, Mean-Reversion, Hurst, Volatility",
    "Weighted vote output: BUY / SELL / HOLD with confidence %",
    "Individual signal contributions shown",
  ],
  [],
));

children.push(...tc(
  "32", "DCF valuation",
  ["CLI started"],
  [
    { text: "Run:", cmd: "dcf RELIANCE" },
  ],
  [
    "Intrinsic value (₹ per share) displayed",
    "Upside/downside % vs current price",
    "± range (bull/base/bear scenarios)",
    "Key assumptions listed (growth rate, WACC, terminal value)",
  ],
  [],
));

children.push(...tc(
  "33", "Risk report",
  ["CLI started with broker (or demo)", "Some positions/holdings present"],
  [
    { text: "Run:", cmd: "risk-report" },
  ],
  [
    "VaR (Value at Risk) at 95% and 99% confidence shown",
    "CVaR (Expected Shortfall) shown",
    "Portfolio-level risk warnings if thresholds breached",
    "No crash even on empty portfolio",
  ],
  [],
));

children.push(...tc(
  "34", "What-if scenario",
  ["CLI started"],
  [
    { text: "Run a market drop scenario:", cmd: "whatif nifty -3" },
    { text: "Run a single stock scenario:", cmd: "whatif RELIANCE -10" },
  ],
  [
    "P&L impact in ₹ shown for the given % move",
    "Portfolio-level delta displayed for NIFTY move",
    "Individual position deltas for stock scenario",
    "Negative values rendered in red",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 8 — STRATEGY SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("8.  Strategy System"));

children.push(h2("8.1  Built-in Strategy Templates"));
children.push(twoCol([
  ["Strategy ID", "Description"],
  ["rsi", "RSI(14) oversold/overbought mean-reversion"],
  ["ma", "Simple moving average crossover (default 20/50)"],
  ["ema", "Exponential MA crossover"],
  ["macd", "MACD signal line crossover"],
  ["bb", "Bollinger Band breakout / mean-reversion"],
  ["supertrend", "Supertrend trend-following"],
  ["momentum", "Price momentum (rate of change)"],
  ["breakout", "52-week high/low breakout"],
  ["pairs", "Statistical pairs trading (cointegration)"],
  ["straddle", "Long straddle options strategy"],
  ["iron-condor", "Iron condor options strategy"],
], [2800, 6560]));

children.push(...spacer(1));

children.push(...tc(
  "35", "List saved strategies",
  ["CLI started"],
  [
    { text: "Run:", cmd: "strategy list" },
  ],
  [
    "Table of saved custom strategies (may be empty on fresh install)",
    "Columns: Name, Type, Symbol, Created",
    "Built-in templates are not listed here (they are referenced directly by name)",
  ],
  [],
));

children.push(...tc(
  "36", "Create a new strategy (interactive builder)",
  ["CLI started"],
  [
    { text: "Launch builder:", cmd: "strategy new" },
    "Follow the prompts: name, type, entry/exit rules.",
    "Save when prompted.",
    "Verify with 'strategy list'.",
  ],
  [
    "Interactive wizard steps through: name, indicators, entry conditions, exit conditions, position size",
    "Strategy saved to JSON in ~/.trading_platform/strategies/",
    "'strategy list' shows the new strategy",
  ],
  ["Ctrl-C cancels without saving (no corrupted state)"],
));

children.push(...tc(
  "37", "Create simple strategy (--simple flag)",
  ["CLI started"],
  [
    { text: "Run:", cmd: "strategy new --simple" },
    "Answer the simplified prompts.",
  ],
  [
    "Fewer prompts than full builder",
    "Strategy created with sensible defaults for unspecified fields",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 9 — BACKTESTING
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("9.  Backtesting Engine"));

children.push(...tc(
  "38", "Basic backtest (RSI strategy)",
  ["CLI started"],
  [
    { text: "Run:", cmd: "backtest RELIANCE rsi" },
    "Wait 5–10 seconds for data fetch + computation.",
    "Read the results panel.",
  ],
  [
    "Results panel shows all required metrics:",
    "  • Total Return %, CAGR %, Sharpe Ratio, Max Drawdown %",
    "  • Total Trades, Win Rate, Avg Win %, Avg Loss %, Profit Factor, Avg Hold Days",
    "  • Buy & Hold % and Alpha vs buy-and-hold",
    "Trades table lists each trade: Entry Date, Exit Date, Direction, Entry/Exit Price, Qty, P&L, P&L%",
    "Equity curve values shown or plotted",
  ],
  ["'No trades found' → strategy found no signals in the period; try a longer period with --period 5y"],
));

children.push(...tc(
  "39", "Backtest with custom period",
  ["CLI started"],
  [
    { text: "Run:", cmd: "backtest INFY ma 20 50 --period 3y" },
  ],
  [
    "Period covers 3 years of data",
    "MA crossover parameters (20, 50) respected",
    "Start/end dates shown in results header",
  ],
  ["Insufficient data for period → yfinance may not have 3y for all symbols in demo mode"],
));

children.push(...tc(
  "40", "Backtest with PDF export",
  ["CLI started"],
  [
    { text: "Run:", cmd: "backtest TCS macd --pdf" },
    "Check the docs/ or output directory for the generated PDF.",
  ],
  [
    "Terminal output as usual",
    "PDF file created: backtest_TCS_macd_<date>.pdf or similar",
    "PDF contains metrics table + trades list",
  ],
  ["PDF not created → fpdf2 not installed; run: pip install fpdf2"],
));

children.push(...tc(
  "41", "Backtest with explain flag",
  ["CLI started", "AI provider configured"],
  [
    { text: "Run:", cmd: "backtest HDFCBANK rsi --explain" },
  ],
  [
    "Standard backtest metrics shown first",
    "Plain-English AI explanation appended: why the strategy worked/failed, key periods, suggestions",
  ],
  [],
));

children.push(...tc(
  "42", "Multi-strategy comparison",
  ["CLI started"],
  [
    { text: "Run:", cmd: "backtest NIFTY rsi macd --compare" },
  ],
  [
    "Side-by-side comparison of RSI and MACD strategies",
    "Columns: Metric, RSI result, MACD result",
    "Winner highlighted per metric",
  ],
  [],
));

children.push(...tc(
  "43", "Walk-forward validation",
  ["CLI started"],
  [
    { text: "Run:", cmd: "walkforward RELIANCE rsi" },
  ],
  [
    "Multiple rolling windows tested (e.g. 6 windows of 6 months each)",
    "Per-window Sharpe and return shown",
    "Overall walk-forward efficiency ratio displayed",
    "Indicates strategy robustness vs. in-sample overfitting",
  ],
  ["Takes 2–3x longer than standard backtest (multiple windows); expected"],
));

children.push(...tc(
  "44", "Options backtest (straddle)",
  ["CLI started"],
  [
    { text: "Run:", cmd: "backtest NIFTY straddle" },
  ],
  [
    "Options-specific P&L at expiry shown",
    "Strike price selection logic described",
    "Max profit, max loss, breakeven points displayed",
  ],
  ["Options data unavailable in yfinance demo → simulated P&L using approximations; expected"],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 10 — POSITION SIZING
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("10.  Position Sizing"));

children.push(noteBox("Position sizing is embedded in trade recommendations. It can also be accessed directly via the 'analyze' output under 'Trade Recommendations'."));

children.push(...spacer(1));
children.push(twoCol([
  ["Method", "Description & Formula"],
  ["Half-Kelly", "f* = (p/a - q/b)/2  where p=win prob, a=avg win, q=1-p, b=avg loss. Capped at 20% of capital."],
  ["Risk-based", "Size = (Capital × RiskPct) / StopLossDistance. RiskPct configurable in config.yaml."],
  ["Fixed-fraction", "Fixed % of capital per trade (e.g. 2%). Simplest method."],
], [2800, 6560]));

children.push(...spacer(1));

children.push(...tc(
  "45", "Position size in trade recommendation",
  ["TC-25 passed (analyze command working)", "AI provider key configured"],
  [
    { text: "Run:", cmd: "analyze RELIANCE" },
    "Scroll to the 'Trade Recommendations' section.",
    "Verify three personas are shown.",
  ],
  [
    "Three personas shown: Conservative, Balanced, Aggressive",
    "Each persona shows: Direction, Entry, Stop Loss, Target, Position Size (shares or lots), Risk Amount (₹)",
    "Balanced persona uses half-Kelly sizing",
    "Position size is a positive integer or lot count",
  ],
  ["Position size shows 0 → capital not configured in config.yaml; set trading_capital under user config"],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 11 — PAPER TRADING
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("11.  Paper Trading"));

children.push(...tc(
  "46", "Switch to paper trading mode",
  ["CLI started"],
  [
    { text: "Run:", cmd: "mode paper" },
    { text: "Verify mode changed:", cmd: "paper" },
  ],
  [
    "'Switched to paper broker' message displayed",
    "'paper' command shows: Paper Trading: ACTIVE, Starting Capital, Current P&L",
    "Subsequent trade commands execute against paper broker",
  ],
  ["'mode' command not found → check app/repl.py for mode handler"],
));

children.push(...tc(
  "47", "Place a paper trade (market order)",
  ["TC-46 passed (paper mode active)"],
  [
    { text: "Buy 10 shares of RELIANCE at market:", cmd: "buy RELIANCE 10" },
    { text: "Check positions:", cmd: "positions" },
    { text: "Check orders:", cmd: "orders" },
  ],
  [
    "Order accepted immediately (market order)",
    "'positions' shows RELIANCE, Qty 10, CNC product",
    "'orders' shows COMPLETE status for the buy order",
    "Paper portfolio cash reduced by: 10 × LTP × (1 + 0.0005) slippage",
  ],
  ["Order rejected → insufficient paper capital; check funds and reduce qty"],
));

children.push(...tc(
  "48", "Paper trade P&L tracking",
  ["TC-47 passed (open paper position exists)"],
  [
    { text: "Check paper P&L:", cmd: "paper" },
    { text: "Check holdings:", cmd: "holdings" },
  ],
  [
    "'paper' shows current unrealised P&L for the position",
    "'holdings' lists RELIANCE with paper position",
    "P&L updates each time 'paper' is called (reflects latest LTP)",
  ],
  [],
));

children.push(...tc(
  "49", "Sell paper position",
  ["TC-47 passed (open paper position exists)"],
  [
    { text: "Sell all RELIANCE:", cmd: "sell RELIANCE 10" },
    { text: "Confirm position closed:", cmd: "positions" },
    { text: "Confirm realised P&L:", cmd: "paper" },
  ],
  [
    "Order fills immediately at market (with slippage)",
    "positions shows RELIANCE Qty 0 (or row removed)",
    "'paper' shows updated Realised P&L",
    "Cash balance increases by proceeds",
  ],
  [],
));

children.push(...tc(
  "50", "Switch back to live broker",
  ["TC-46 passed", "Live broker was previously connected"],
  [
    { text: "Switch back:", cmd: "mode zerodha" },
  ],
  [
    "'Switched to zerodha' message",
    "Subsequent data/trade commands route to live Zerodha broker",
    "Paper portfolio state persisted to ~/.trading_platform/paper_portfolio.json",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 12 — ALERTS
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("12.  Alerts"));

children.push(...tc(
  "51", "Create a price alert",
  ["CLI started"],
  [
    { text: "Set alert for RELIANCE above ₹2800:", cmd: "alert RELIANCE above 2800" },
    { text: "List all alerts:", cmd: "alerts" },
  ],
  [
    "'✓ Alert added: RELIANCE price ABOVE ₹2800' with UUID",
    "'alerts' table shows the new alert with status: Active",
    "Alert columns: ID (short), Symbol, Type, Condition, Threshold, Status",
  ],
  ["Duplicate alert warning if same condition already exists"],
));

children.push(...tc(
  "52", "Create a technical / RSI alert",
  ["CLI started"],
  [
    { text: "Set RSI overbought alert:", cmd: "alert INFY RSI above 70" },
    { text: "Verify:", cmd: "alerts" },
  ],
  [
    "Alert created with Type: TECHNICAL, Indicator: RSI, Threshold: 70",
    "Listed in alerts table separately from price alerts",
  ],
  [],
));

children.push(...tc(
  "53", "Create a conditional (AND) alert",
  ["CLI started"],
  [
    { text: "Set compound condition:", cmd: "alert NIFTY above 24500 AND RSI above 70" },
    { text: "Verify:", cmd: "alerts" },
  ],
  [
    "Alert created with Type: CONDITIONAL",
    "Both conditions shown in alerts table",
    "Alert only triggers when BOTH conditions are simultaneously true",
  ],
  [],
));

children.push(...tc(
  "54", "Remove an alert",
  ["TC-51 completed (alert exists)"],
  [
    { text: "Run 'alerts' and note an alert ID (first 8 chars):", cmd: "alerts" },
    { text: "Remove it:", cmd: "alert remove <ID>" },
    { text: "Verify removed:", cmd: "alerts" },
  ],
  [
    "'Alert removed' confirmation",
    "Alert no longer in 'alerts' list",
  ],
  ["ID not found → copy full UUID from alerts list; partial ID only works if unambiguous"],
));

children.push(...tc(
  "55", "Alert firing (simulated)",
  ["TC-51 completed", "Demo mode or live broker connected"],
  [
    { text: "Set an alert that is already triggered (e.g., below current price):", cmd: "alert RELIANCE above 1" },
    "Wait ~60 seconds (polling interval).",
    "Observe terminal notification.",
  ],
  [
    "Terminal notification: '⚠ Alert triggered: RELIANCE above ₹1'",
    "Alert status in 'alerts' changes to Triggered with timestamp",
    "If Telegram configured: push notification sent to bot",
  ],
  ["No notification after 60s → market hours check; alerts only fire during NSE hours (9:15–15:30 IST Mon–Fri)"],
  "During demo mode, LTP comes from yfinance. Set a threshold well below current price to guarantee trigger."
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 13 — MULTI-AGENT ORCHESTRATION
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("13.  Multi-Agent Orchestration"));

children.push(noteBox("The multi-agent system runs internally when you call 'analyze' or 'deep-analyze'. These tests verify the correctness of analyst outputs, DAG scheduling, and debate consensus."));
children.push(...spacer(1));

children.push(...tc(
  "56", "Analyst swarm completeness",
  ["CLI started", "AI provider key configured"],
  [
    { text: "Run full analysis:", cmd: "analyze RELIANCE" },
    "Count the analyst reports in the output.",
    "Verify each analyst is present.",
  ],
  [
    "Exactly 7 analysts present: TechnicalAnalyst, FundamentalAnalyst, OptionsAnalyst, NewsMacroAnalyst, SentimentAnalyst, SectorRotationAnalyst, RiskAnalyst",
    "Each report has: Rating (0–100), Direction, Confidence, Key Findings (at least 1)",
    "No 'None' or 'N/A' entries in critical fields",
  ],
  ["Fewer than 7 analysts → one module crashed; run with verbose logging to identify which"],
));

children.push(...tc(
  "57", "Debate consensus output",
  ["TC-56 passed"],
  [
    { text: "Run:", cmd: "analyze HDFCBANK" },
    "Focus on the 'Debate' section of output.",
  ],
  [
    "Debate section shows: overall consensus direction (BUY/SELL/HOLD)",
    "Dissenting analysts listed (if any disagree with consensus)",
    "Confidence-weighted vote shown (not just majority)",
    "Edge case: if all 7 agree → 'Unanimous consensus: BUY/SELL/HOLD'",
  ],
  [],
));

children.push(...tc(
  "58", "Deep-analyze extra analysts",
  ["CLI started", "AI provider configured"],
  [
    { text: "Run:", cmd: "deep-analyze TCS" },
    "Count analysts in output.",
  ],
  [
    "11 analysts present (4 more than analyze)",
    "Full narrative text per analyst (not just key findings bullets)",
    "Longer processing time: 30–60s",
  ],
  [],
));

children.push(...tc(
  "59", "DAG orchestration ordering",
  ["CLI started"],
  [
    { text: "Run analyze with verbose output (if --verbose flag exists):", cmd: "analyze INFY" },
    "Observe the order analysts complete vs. order they start.",
  ],
  [
    "RiskAnalyst runs after all other analysts (it depends on their outputs)",
    "Data-fetching analysts (Technical, Fundamental) run first in parallel",
    "LLM synthesis analysts run after data analysts complete",
    "No deadlock (all analysts complete within 60s)",
  ],
  [],
  "The DAG uses Kahn's topological sort. If an analyst fails, its dependents receive a null input and gracefully degrade."
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 14 — ML ANALYST
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("14.  ML Feature Pipeline & Analyst"));

children.push(...tc(
  "60", "ML analyst training",
  ["CLI started", "scikit-learn installed (in pyproject.toml deps)"],
  [
    { text: "Trigger ML training by running analysis on a symbol with enough history:", cmd: "analyze RELIANCE" },
    "The MLPredictor trains on first use.",
    "Check for ML confidence score in the output.",
  ],
  [
    "No sklearn import errors",
    "ML confidence score visible in analyst output (0–1.0)",
    "Training completes without hanging (GradientBoosting on 300 candles: <5s)",
  ],
  ["sklearn not installed → pip install scikit-learn>=1.3.0",
   "Training data too short (<100 candles) → MLPredictor returns None confidence; non-fatal"],
));

children.push(...tc(
  "61", "ML prediction direction",
  ["TC-60 passed"],
  [
    { text: "Run analysis twice on same symbol, 1 hour apart:", cmd: "analyze RELIANCE" },
    "Compare ML direction in both outputs.",
  ],
  [
    "ML direction (BUY/SELL/HOLD) is consistent with recent price action",
    "Direction can change between runs as new data comes in (expected)",
    "Confidence score is in range 0.0–1.0",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 15 — WEB API & SSE STREAMING
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("15.  Web API & SSE Streaming"));

children.push(prereqBox([
  "CLI running (trade --no-broker)",
  "Web server auto-starts on port 8765",
  "curl or Postman available for API tests",
]));
children.push(...spacer(1));

children.push(...tc(
  "62", "Health check endpoint",
  ["Web server running on 8765"],
  [
    { text: "Run:", cmd: "curl http://localhost:8765/health" },
  ],
  ['Response: {"status": "ok"}', "HTTP 200 status code"],
  ["Connection refused → web server not started; run 'web' in REPL"],
));

children.push(...tc(
  "63", "Broker status endpoint",
  ["Web server running"],
  [
    { text: "Run:", cmd: "curl http://localhost:8765/api/status" },
  ],
  [
    "JSON response with keys: zerodha, groww, angelone, upstox, fyers",
    "Each key has: connected (bool), role (data/execution/primary)",
    "Demo mode → all connected: false",
  ],
  [],
));

children.push(...tc(
  "64", "Skills API — quote",
  ["Web server running"],
  [
    { text: "Run:", cmd: "curl -X POST http://localhost:8765/skills/quote -H 'Content-Type: application/json' -d '{\"symbol\":\"RELIANCE\"}'" },
  ],
  [
    "JSON response with quote object: symbol, ltp, open, high, low, volume, change_pct",
    "HTTP 200",
  ],
  [],
));

children.push(...tc(
  "65", "Skills API — backtest",
  ["Web server running"],
  [
    { text: "Run:", cmd: "curl -X POST http://localhost:8765/skills/backtest -H 'Content-Type: application/json' -d '{\"symbol\":\"INFY\",\"strategy\":\"rsi\",\"period\":\"1y\"}'" },
    "Wait 10–15 seconds.",
  ],
  [
    "JSON BacktestResult object returned",
    "Fields: total_return_pct, cagr, sharpe, max_drawdown, win_rate, total_trades",
    "Trades array with individual trade records",
    "HTTP 200",
  ],
  [],
));

children.push(...tc(
  "66", "SSE prices stream",
  ["Web server running"],
  [
    { text: "Connect to SSE stream:", cmd: "curl -N http://localhost:8765/stream/prices" },
    "Observe events in terminal.",
    "Press Ctrl-C after 30 seconds.",
  ],
  [
    "HTTP 200 with Content-Type: text/event-stream",
    "Cache-Control: no-cache header present",
    "Events appear in format: 'data: {\"symbol\":\"...\",\"ltp\":...}\\n\\n'",
    "Ctrl-C disconnects cleanly (no server error)",
  ],
  ["No events for 60s → publisher not running; events only fire when broker sends a price tick or test publisher is active"],
));

children.push(...tc(
  "67", "SSE alerts stream",
  ["Web server running", "TC-51 passed (alert configured)"],
  [
    { text: "Connect to SSE alerts stream:", cmd: "curl -N http://localhost:8765/stream/alerts" },
    "Trigger an alert (e.g. set alert below current price).",
    "Observe the SSE event arrive.",
  ],
  [
    "Alert event in format: 'data: {\"alert_id\":\"...\",\"symbol\":\"...\",\"message\":\"...\"}\\n\\n'",
    "Event arrives within ~60 seconds of alert condition being met",
  ],
  [],
));

children.push(...tc(
  "68", "Skills API — streaming analysis",
  ["Web server running", "AI provider key configured"],
  [
    { text: "Connect to streaming analysis:", cmd: "curl -N 'http://localhost:8765/skills/analyze/stream?symbol=RELIANCE&exchange=NSE'" },
    "Observe analyst reports streaming in real-time.",
  ],
  [
    "SSE events appear as each analyst completes",
    "Events contain partial AnalystReport JSON",
    "Final event contains completed scorecard",
    "Stream closes automatically after all analysts finish",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 16 — TELEGRAM BOT
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("16.  Telegram Bot"));

children.push(prereqBox([
  "TELEGRAM_BOT_TOKEN set in keychain or .env",
  "Bot created via @BotFather on Telegram",
  "Your Telegram user ID whitelisted (if access control configured)",
]));
children.push(...spacer(1));

children.push(...tc(
  "69", "Start Telegram bot",
  ["Prerequisites met"],
  [
    { text: "Start the bot:", cmd: "telegram" },
    "Open Telegram and message the bot: /start",
    "Observe the welcome message.",
  ],
  [
    "'Telegram bot started' message in REPL",
    "/start returns welcome message with command list",
    "Bot remains running (background task)",
  ],
  ["'Unauthorized' from Telegram API → TELEGRAM_BOT_TOKEN is incorrect",
   "Bot not responding → check REPL is still running (bot needs the event loop)"],
));

children.push(...tc(
  "70", "Telegram /quote command",
  ["TC-69 passed (bot running)"],
  [
    "In Telegram, send: /quote RELIANCE",
    "Wait for bot response.",
  ],
  [
    "Bot replies with live price data for RELIANCE",
    "Format: Symbol, LTP, Change% in a clean message",
    "Response within 10 seconds",
  ],
  [],
));

children.push(...tc(
  "71", "Telegram /analyze command",
  ["TC-69 passed", "AI provider key configured"],
  [
    "In Telegram, send: /analyze INFY",
    "Wait up to 30 seconds.",
  ],
  [
    "Bot replies with condensed analysis: Overall rating, Direction, Top 3 findings",
    "Response formatted for mobile (no Rich tables — plain text or Markdown)",
  ],
  [],
));

children.push(...tc(
  "72", "Telegram alert push notification",
  ["TC-69 passed", "TC-51 passed (alert configured)", "Alert set to trigger condition"],
  [
    "Set an alert that will trigger immediately: 'alert RELIANCE above 1'",
    "Wait up to 60 seconds.",
    "Check Telegram for a push notification.",
  ],
  [
    "Telegram message received: '⚠ Alert: RELIANCE price ABOVE ₹1 — Current: ₹X,XXX'",
    "Message arrives within 60 seconds of trigger",
  ],
  ["Notification not received → TELEGRAM_BOT_TOKEN missing or bot not running"],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 17 — MEMORY & LEARNING SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("17.  Memory & Learning System"));

children.push(...tc(
  "73", "View recent analyses (memory)",
  ["Several 'analyze' commands run earlier in session"],
  [
    { text: "Run:", cmd: "memory" },
  ],
  [
    "List of recent analyses shown: symbol, date, direction, overall rating",
    "Most recent first",
    "SQLite DB populated (not empty after running analyze commands)",
  ],
  ["Empty → analysis results not being persisted; check DB path in app/repl.py"],
));

children.push(...tc(
  "74", "Filter memory by symbol",
  ["TC-73 passed (memory populated)"],
  [
    { text: "Run:", cmd: "memory RELIANCE" },
  ],
  [
    "Only RELIANCE analyses shown",
    "Other symbols filtered out",
  ],
  [],
));

children.push(...tc(
  "75", "Record trade outcome",
  ["TC-73 passed", "At least one analysis in memory — note its ID"],
  [
    { text: "Record a WIN for an analysis ID:", cmd: "memory outcome <ID> WIN 5000" },
    { text: "View stats:", cmd: "memory stats" },
  ],
  [
    "'Outcome recorded: WIN ₹5,000' confirmation",
    "'memory stats' shows updated Win Rate and total P&L",
    "Sharpe ratio updates after sufficient outcomes",
  ],
  [],
));

children.push(...tc(
  "76", "AI reflection on trading patterns",
  ["TC-75 passed (outcomes recorded)", "AI provider configured"],
  [
    { text: "Run:", cmd: "memory reflect" },
  ],
  [
    "AI-generated reflection on trading patterns",
    "References specific symbols or strategies from recorded history",
    "Actionable suggestions based on outcomes",
  ],
  [],
));

children.push(...tc(
  "77", "Model drift detection",
  ["Some memory/outcomes recorded"],
  [
    { text: "Run:", cmd: "drift" },
  ],
  [
    "Drift report shows: recent performance vs. historical baseline",
    "If recent Sharpe < historical: drift warning displayed in yellow/red",
    "If no drift: 'No significant model drift detected'",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 18 — GRACEFUL FALLBACKS
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("18.  Graceful Fallbacks & Error Resilience"));

children.push(twoCol([
  ["Scenario", "Expected Fallback Behaviour"],
  ["py_vollib not installed", "Built-in Black-Scholes formula used; no crash; options pricing still works"],
  ["Broker API unavailable", "Drops to paper/mock broker; yellow warning banner; REPL continues"],
  ["AI provider rate-limited", "Retries with exponential backoff; after 3 failures: graceful error message"],
  ["yfinance unavailable (demo)", "Returns cached/mock data; non-fatal warning"],
  ["SQLite DB locked", "Memory commands fail gracefully with message; analysis still runs"],
  ["Port 8765 already in use", "Web server logs warning; CLI REPL continues without web API"],
  ["TOTP misconfigured", "Angel One login fails; drops to demo mode with instructions to fix TOTP"],
  ["Network timeout during OAuth", "Cancels login; REPL continues in demo mode"],
], [4200, 5160]));

children.push(...spacer(1));

children.push(...tc(
  "78", "py_vollib fallback",
  ["py_vollib NOT installed (pip uninstall py_vollib)"],
  [
    { text: "Run options analysis:", cmd: "analyze NIFTY" },
    "Look for options-related metrics in OptionsAnalyst report.",
  ],
  [
    "No ImportError for py_vollib",
    "Options IV, Delta, Theta displayed (via built-in BS formula)",
    "May show slightly different values vs py_vollib but no crash",
  ],
  ["If crash with 'py_vollib not found' → fallback not implemented; file a bug"],
));

children.push(...tc(
  "79", "Broker unavailable fallback",
  ["Fyers credentials set but intentionally wrong (wrong APP_ID)"],
  [
    { text: "Start CLI and attempt Fyers login:", cmd: "trade" },
    "Select Fyers from menu.",
    "Observe error handling.",
  ],
  [
    "Error message shown: 'Fyers login failed: ...'",
    "REPL drops to demo mode with --no-broker behaviour",
    "Yellow banner: '(Demo mode — data below is simulated...)'",
    "No crash / no unhandled exception traceback",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 19 — OPTIONS ANALYTICS
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("19.  Options Analytics"));

children.push(...tc(
  "80", "Options chain",
  ["CLI started (live broker with options data OR Fyers connected)"],
  [
    { text: "Run:", cmd: "quote NIFTY" },
    { text: "Or via web API:", cmd: "curl -X POST http://localhost:8765/skills/options_chain -H 'Content-Type: application/json' -d '{\"symbol\":\"NIFTY\"}'" },
  ],
  [
    "Options chain table: Strike, CE LTP, CE IV, CE Delta, CE OI, PE LTP, PE IV, PE Delta, PE OI",
    "ATM strike highlighted",
    "Multiple expiries available",
  ],
  ["Demo mode → limited options data from yfinance; some columns may be 0"],
));

children.push(...tc(
  "81", "GEX (Gamma Exposure) report",
  ["CLI started"],
  [
    { text: "Run:", cmd: "gex" },
  ],
  [
    "NIFTY GEX levels displayed",
    "Key GEX strike levels shown (major walls)",
    "Market direction bias from GEX indicated",
  ],
  [],
));

children.push(...tc(
  "82", "Delta hedge suggestions",
  ["CLI started", "Options positions in portfolio (live or paper)"],
  [
    { text: "Run:", cmd: "delta-hedge" },
  ],
  [
    "Current net delta displayed",
    "Hedging trades suggested to neutralise delta",
    "Trade size in lots/shares specified",
    "Empty → no open options positions (valid; not a bug)",
  ],
  [],
));

children.push(...tc(
  "83", "Roll options suggestions",
  ["CLI started", "Near-expiry options positions in portfolio"],
  [
    { text: "Run:", cmd: "roll-options" },
  ],
  [
    "Expiring positions listed with days-to-expiry",
    "Roll-to strike and expiry suggested for each",
    "Net debit/credit of roll shown",
  ],
  [],
));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 20 — END-TO-END FLOWS
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("20.  End-to-End Happy Path Flows"));

children.push(h2("Flow A — Full Research-to-Trade Workflow (Demo Mode)"));
children.push(body("This flow simulates a complete trading session from market open to trade placement. Run in order."));
children.push(...spacer(1));

const flowASteps = [
  { text: "Start CLI:", cmd: "trade --no-broker" },
  { text: "Get morning context:", cmd: "morning-brief" },
  { text: "Check macro environment:", cmd: "macro" },
  { text: "Check FII/DII flows:", cmd: "flows" },
  { text: "Get a quote on your watchlist:", cmd: "quote RELIANCE INFY TCS HDFCBANK" },
  { text: "Pick the strongest (e.g. RELIANCE) and analyse:", cmd: "analyze RELIANCE" },
  { text: "Run a backtest on the suggested strategy:", cmd: "backtest RELIANCE rsi --explain" },
  { text: "Switch to paper mode:", cmd: "mode paper" },
  { text: "Place the paper trade:", cmd: "buy RELIANCE 5" },
  { text: "Confirm positions:", cmd: "positions" },
  { text: "Set a stop-loss alert:", cmd: "alert RELIANCE below 2700" },
  { text: "Set a target alert:", cmd: "alert RELIANCE above 2900" },
  { text: "Check paper P&L:", cmd: "paper" },
];
flowASteps.forEach((s, i) => {
  children.push(new Paragraph({
    spacing: { before: 60, after: 40 },
    children: [bold(`${i + 1}.  `, { size: 20 }), run(s.text, { size: 20 })],
  }));
  if (s.cmd) children.push(code("    " + s.cmd));
});
children.push(...spacer(1));
children.push(passBox([
  "No errors at any step",
  "Morning brief is India-specific (NIFTY/SENSEX references)",
  "analyze returns 7 analysts + debate + 3 trade plans",
  "Backtest shows positive Sharpe in at least one period",
  "Paper trade fills immediately at market",
  "Both alerts created with unique IDs",
  "paper shows open position with unrealised P&L",
]));
children.push(...spacer(1));
children.push(divider());

children.push(h2("Flow B — Broker Session Lifecycle (Live Broker)"));
children.push(body("Tests the full login → use → logout → re-login cycle. Requires actual broker credentials."));
children.push(...spacer(1));

const flowBSteps = [
  { text: "Start CLI (no flag):", cmd: "trade" },
  "Select broker from menu (e.g. 3 for Angel One).",
  "Observe auto-TOTP login (Angel) or browser OAuth (others).",
  { text: "Verify connection:", cmd: "profile" },
  { text: "Fetch live funds:", cmd: "funds" },
  { text: "Fetch live holdings:", cmd: "holdings" },
  { text: "Fetch live positions:", cmd: "positions" },
  { text: "Logout:", cmd: "logout" },
  { text: "Re-login to verify re-authentication works:", cmd: "trade" },
  "Select same broker — confirm login succeeds again.",
];
flowBSteps.forEach((s, i) => {
  children.push(new Paragraph({
    spacing: { before: 60, after: 40 },
    children: [bold(`${i + 1}.  `, { size: 20 }), run(typeof s === "string" ? s : s.text, { size: 20 })],
  }));
  if (typeof s === "object" && s.cmd) children.push(code("    " + s.cmd));
});
children.push(...spacer(1));
children.push(passBox([
  "Login completes in <30 seconds",
  "profile shows real name and client ID from broker",
  "funds returns actual ₹ balance (not zeros unless account has no funds)",
  "logout clears token file in ~/.trading_platform/",
  "Re-login succeeds without stale token errors",
]));
children.push(...spacer(1));
children.push(divider());

children.push(h2("Flow C — Web API + SSE Integration"));
children.push(body("Tests the FastAPI sidecar end-to-end from a separate terminal."));
children.push(...spacer(1));

const flowCSteps = [
  { text: "In Terminal 1, start CLI:", cmd: "trade --no-broker" },
  { text: "In Terminal 2, check health:", cmd: "curl http://localhost:8765/health" },
  { text: "Get a quote via skills API:", cmd: "curl -X POST http://localhost:8765/skills/quote -H 'Content-Type: application/json' -d '{\"symbol\":\"NIFTY\"}'" },
  { text: "Connect to SSE price stream:", cmd: "curl -N http://localhost:8765/stream/prices" },
  "In Terminal 1, set an alert. Observe SSE event in Terminal 2 when it fires.",
  { text: "Connect to SSE alert stream:", cmd: "curl -N http://localhost:8765/stream/alerts" },
  { text: "In Terminal 1, set and immediately trigger alert:", cmd: "alert NIFTY above 1" },
  "Observe the SSE alert event arrive in Terminal 2.",
];
flowCSteps.forEach((s, i) => {
  children.push(new Paragraph({
    spacing: { before: 60, after: 40 },
    children: [bold(`${i + 1}.  `, { size: 20 }), run(typeof s === "string" ? s : s.text, { size: 20 })],
  }));
  if (typeof s === "object" && s.cmd) children.push(code("    " + s.cmd));
});
children.push(...spacer(1));
children.push(passBox([
  "Health check returns {\"status\": \"ok\"}",
  "Quote API returns JSON with ltp field",
  "SSE stream stays open (does not return 404 or close immediately)",
  "Alert SSE event arrives in data: {...}\\n\\n format",
  "JSON in SSE event is parseable and contains symbol and message",
]));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 21 — EDGE CASES & REGRESSION TESTS
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("21.  Edge Cases & Regression Tests"));

children.push(twoCol([
  ["Edge Case", "Steps & Expected Behaviour"],
  ["Invalid symbol", "Run: quote XXXINVALID — should show 'Symbol not found' or empty row, not crash"],
  ["Empty portfolio commands", "Run: holdings / positions on fresh account — empty table, no error"],
  ["Backtest with no trades", "Run: backtest RELIANCE rsi --period 1d — no trades; message: 'No trades in this period'"],
  ["Duplicate alert", "Set same alert twice — second should warn 'Alert already exists' with existing ID"],
  ["Very long symbol list", "Run: quote + 20 symbols — should paginate or truncate; no timeout/crash"],
  ["Special chars in ai command", "Run: ai \"What's ₹500 worth in USD?\" — no encoding error; AI responds"],
  ["Broker disconnect mid-session", "Kill broker process / revoke token externally; next command should fail gracefully and suggest re-login"],
  ["Paper trade over-allocation", "Buy 100000 shares at ₹2000 each in paper (exceeds capital) — should reject with insufficient funds message"],
  ["Concurrent SSE subscribers", "Open 5 curl sessions to /stream/prices simultaneously — all should receive events; no server crash"],
  ["Port conflict on 8765", "Run netcat to bind 8765 before starting CLI; CLI should start with warning, not crash"],
], [3200, 6160]));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// SECTION 22 — AUTOMATED TEST SUITE
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("22.  Automated Test Suite Reference"));

children.push(body("Run the automated tests to verify core logic before manual testing:"));
children.push(...spacer(1));

children.push(twoCol([
  ["Command", "What it tests"],
  ["pytest tests/ -m 'not network and not slow' -n auto", "All fast unit tests in parallel (~2 min)"],
  ["pytest tests/test_sse_streaming.py -m 'not slow'", "SSE event bus unit tests (no HTTP connection)"],
  ["pytest tests/test_ml_analyst.py", "ML training/predict pipeline"],
  ["pytest tests/test_178_broker_routing.py", "Multi-broker role routing (48 tests)"],
  ["pytest tests/ -m slow -n auto", "Slow tests: SSE live connections, Monte Carlo (nightly)"],
  ["pytest tests/ -m network", "Network tests: live yfinance, NSE API (requires internet)"],
  ["ruff check .", "Linting — no errors expected"],
  ["ruff format --check .", "Format check — no diffs expected"],
], [5200, 4160]));

children.push(...spacer(1));
children.push(noteBox("Test coverage by area: SSE event bus (10 tests), ML analyst (26 tests), broker routing (48 tests), backtest engine, strategy system, alert manager. Run 'pytest tests/ --co -q' to see all test names."));

children.push(pageBreak());

// ═══════════════════════════════════════════════════════════════════════════════
// APPENDIX — QUICK COMMAND CHEATSHEET
// ═══════════════════════════════════════════════════════════════════════════════
children.push(h1("Appendix — Test Command Quick Reference"));

children.push(h2("Startup"));
children.push(code("trade --no-broker              # Demo mode"));
children.push(code("trade                          # Live broker login"));
children.push(code("trade --tui                    # TUI interface"));
children.push(...spacer(1));

children.push(h2("Credentials"));
children.push(code("credentials                    # List all"));
children.push(code("credentials setup              # Interactive wizard"));
children.push(code("credentials set KITE_API_KEY   # Set one key"));
children.push(code("credentials delete ANGEL_TOTP_SECRET"));
children.push(...spacer(1));

children.push(h2("Market Data"));
children.push(code("quote RELIANCE INFY TCS        # Multi-symbol quote"));
children.push(code("morning-brief                  # AI market brief"));
children.push(code("flows                          # FII/DII"));
children.push(code("macro                          # USD/INR, crude, gold"));
children.push(code("earnings [SYMBOL]              # Earnings calendar"));
children.push(...spacer(1));

children.push(h2("Analysis"));
children.push(code("analyze RELIANCE               # 7 analysts, ~15s"));
children.push(code("deep-analyze RELIANCE          # 11 analysts, ~45s"));
children.push(code("quick RELIANCE                 # Fast scorecard, ~5s"));
children.push(code("fundamentals RELIANCE"));
children.push(code("sentiment RELIANCE"));
children.push(code("ensemble NIFTY                 # 5-signal ensemble"));
children.push(code("dcf RELIANCE                   # DCF valuation"));
children.push(code("ai \"What to trade today?\"      # Free chat"));
children.push(...spacer(1));

children.push(h2("Backtesting"));
children.push(code("backtest RELIANCE rsi           # RSI strategy"));
children.push(code("backtest INFY ma 20 50 --period 3y"));
children.push(code("backtest NIFTY rsi macd --compare"));
children.push(code("backtest TCS macd --pdf --explain"));
children.push(code("walkforward RELIANCE rsi"));
children.push(code("whatif nifty -3                # Scenario analysis"));
children.push(...spacer(1));

children.push(h2("Paper Trading"));
children.push(code("mode paper                     # Switch to paper"));
children.push(code("buy RELIANCE 10               # Paper buy"));
children.push(code("sell RELIANCE 10              # Paper sell"));
children.push(code("paper                          # P&L status"));
children.push(code("mode zerodha                   # Switch back to live"));
children.push(...spacer(1));

children.push(h2("Alerts"));
children.push(code("alert RELIANCE above 2800      # Price alert"));
children.push(code("alert INFY RSI above 70        # Technical alert"));
children.push(code("alert NIFTY above 24500 AND RSI above 70"));
children.push(code("alerts                         # List all"));
children.push(code("alert remove <ID>              # Delete alert"));
children.push(...spacer(1));

children.push(h2("Broker Management"));
children.push(code("brokers                        # Connected brokers"));
children.push(code("connect 5                      # Add Fyers"));
children.push(code("disconnect fyers               # Remove Fyers"));
children.push(code("funds / profile / holdings / positions / orders"));
children.push(code("logout                         # End session"));
children.push(...spacer(1));

children.push(h2("Options"));
children.push(code("gex                            # Gamma exposure"));
children.push(code("delta-hedge                    # Hedge suggestions"));
children.push(code("roll-options                   # Roll suggestions"));
children.push(code("risk-report                    # VaR / CVaR"));
children.push(...spacer(1));

children.push(h2("Memory"));
children.push(code("memory                         # Recent analyses"));
children.push(code("memory RELIANCE                # Filter by symbol"));
children.push(code("memory stats                   # Win rate / Sharpe"));
children.push(code("memory outcome <ID> WIN 5000   # Record outcome"));
children.push(code("memory reflect                 # AI reflection"));
children.push(code("drift                          # Model drift check"));
children.push(...spacer(1));

children.push(h2("Telegram Bot"));
children.push(code("telegram                       # Start bot"));
children.push(code("# Then in Telegram:"));
children.push(code("/quote RELIANCE  /analyze INFY  /brief  /alerts"));
children.push(...spacer(1));

children.push(h2("Web API (from terminal 2)"));
children.push(code("curl http://localhost:8765/health"));
children.push(code("curl -X POST http://localhost:8765/skills/quote -H 'Content-Type: application/json' -d '{\"symbol\":\"RELIANCE\"}'"));
children.push(code("curl -N http://localhost:8765/stream/prices"));
children.push(code("curl -N http://localhost:8765/stream/alerts"));

// ═══════════════════════════════════════════════════════════════════════════════
// BUILD DOCUMENT
// ═══════════════════════════════════════════════════════════════════════════════
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 300 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 900, hanging: 300 } } } },
        ],
      },
      {
        reference: "steps",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 300 } } } },
        ],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: "Arial", size: 20 } },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: C.navy },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: C.teal },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: C.navy },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: C.black },
        paragraph: { spacing: { before: 160, after: 60 }, outlineLevel: 3 } },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.teal, space: 1 } },
              spacing: { before: 0, after: 120 },
              children: [
                new TextRun({ text: "Vibe Trading — India Trade CLI", font: "Arial", size: 18, color: C.navy, bold: true }),
                new TextRun({ text: "   |   Complete Testing Guide", font: "Arial", size: 18, color: "888888" }),
              ],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              border: { top: { style: BorderStyle.SINGLE, size: 6, color: C.teal, space: 1 } },
              spacing: { before: 120, after: 0 },
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({ text: "Page ", font: "Arial", size: 16, color: "888888" }),
                new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "888888" }),
                new TextRun({ text: " of ", font: "Arial", size: 16, color: "888888" }),
                new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 16, color: "888888" }),
                new TextRun({ text: "   ·   Confidential — For Internal QA Use", font: "Arial", size: 16, color: "888888" }),
              ],
            }),
          ],
        }),
      },
      children,
    },
  ],
});

const OUTPUT = "/Users/arkidmitra/Desktop/TheFICompany/india-trade-cli/docs/india-trade-cli-testing-guide.docx";
Packer.toBuffer(doc).then((buffer) => {
  fs.mkdirSync("/Users/arkidmitra/Desktop/TheFICompany/india-trade-cli/docs", { recursive: true });
  fs.writeFileSync(OUTPUT, buffer);
  console.log("✅  Written:", OUTPUT);
});
