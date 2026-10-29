/**
 * Splice/remove JS expressions in a minified one-line bundle, safely.
 *
 * Reads a file, applies one operation, writes it back, then parses with acorn
 * using the right sourceType. Prints the byte offset and a context window on
 * failure so the broken token is named immediately — no quote-insertion loops.
 *
 * Usage (from a scratch dir with `npm i acorn` done, so ./acornjs resolves):
 *   node splice-js.js <file> module cut "ge===14&&"        # remove expr
 *   node splice-js.js <file> module cutrange "A-anchor" "B-anchor"
 *   node splice-js.js <file> script parse                  # verify only
 *
 * `cut` walks forward from the anchor counting ()[]{} while skipping strings
 * and template literals, and stops when depth returns to 0 at a container
 * boundary — the trailing comma / `]` / `}` is consumed with the expression, so
 * the surrounding array stays valid.
 *
 * acorn path: prefers ./acornjs/node_modules/acorn, falls back to a plain
 * require("acorn") so the script also runs from a dir where acorn is installed.
 */
const fs = require("fs");
const path = require("path");

function loadAcorn() {
  const local = path.join(__dirname, "acornjs", "node_modules", "acorn");
  if (fs.existsSync(local)) return require(local);
  try {
    return require("acorn");
  } catch {
    console.error("acorn not found — run: npm i acorn  (in this dir)");
    process.exit(2);
  }
}

const acorn = loadAcorn();
const [file, mode, sourceType = "module"] = process.argv.slice(2);
if (!file || !mode) {
  console.error("usage: node splice-js.js <file> <cut|cutrange|parse> [args]");
  process.exit(2);
}

let src = fs.readFileSync(file, "utf8");

function exprEnd(s, from) {
  let depth = 0;
  let j = from;
  let inStr = null;
  let esc = false;
  for (; j < s.length; j++) {
    const c = s[j];
    if (inStr) {
      if (esc) { esc = false; continue; }
      if (c === "\\") { esc = true; continue; }
      if (c === inStr) inStr = null;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") { inStr = c; continue; }
    if (c === "(" || c === "[" || c === "{") { depth++; continue; }
    if (c === ")" || c === "]" || c === "}") {
      depth--;
      if (depth < 0) return j; // closed the container we were inside
      if (depth === 0) {
        let k = j + 1;
        while (k < s.length && /\s/.test(s[k])) k++;
        if (s[k] === "," || s[k] === "]" || s[k] === "}") return k;
      }
    }
  }
  return s.length;
}

if (mode === "cut") {
  const anchor = process.argv[4];
  const i = src.indexOf(anchor);
  if (i < 0) {
    console.error("anchor not found:", anchor);
    process.exit(1);
  }
  const end = exprEnd(src, i + anchor.length);
  const before = src.length;
  src = src.slice(0, i) + src.slice(end);
  console.log(`cut ${before - src.length} chars from offset ${i}`);
} else if (mode === "cutrange") {
  const a = src.indexOf(process.argv[4]);
  const b = src.indexOf(process.argv[5], a >= 0 ? a : 0);
  if (a < 0 || b < 0) {
    console.error("anchor missing", { a, b });
    process.exit(1);
  }
  const before = src.length;
  src = src.slice(0, a) + src.slice(b);
  console.log(`cutrange ${before - src.length} chars`);
}

if (mode !== "parse") fs.writeFileSync(file, src);

try {
  acorn.parse(src, { ecmaVersion: "latest", sourceType });
  console.log("PARSE OK", src.length, "bytes");
} catch (e) {
  console.log("PARSE ERR:", e.message, "pos", e.pos);
  console.log(JSON.stringify(src.slice(Math.max(0, e.pos - 250), e.pos + 120)));
  process.exit(1);
}
