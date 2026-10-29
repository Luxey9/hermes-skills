// Rewrite the Win32 version resource of a renamed/copied Electron exe.
// Usage: node set-exe-metadata.js <path-to-exe> <path-to-icon.ico> [ProductName] [Company] [Version]
// Requires the `rcedit` npm package: npm i --no-audit --no-fund rcedit@4
// Run this BEFORE wrapping the app dir into an NSIS installer — the installer
// copies the exe at build time, so a post-wrap edit is lost.
const rcedit = require("rcedit");

const [exe, icon, product = "AppName", company = "Author Name", version = "1.0.0.0"] = process.argv.slice(2);
if (!exe) {
  console.error("usage: node set-exe-metadata.js <exe> [icon.ico] [Product] [Company] [Version]");
  process.exit(1);
}

rcedit(exe, {
  "version-string": {
    CompanyName: company,
    FileDescription: product,
    ProductName: product,
    InternalName: product,
    OriginalFilename: `${product}.exe`,
    LegalCopyright: `Copyright \u00a9 ${new Date().getFullYear()} ${company}`,
  },
  "file-version": version,
  "product-version": version,
  ...(icon ? { icon } : {}),
})
  .then(() => console.log("rcedit ok"))
  .catch((e) => {
    console.error("rcedit failed:", e.message);
    process.exit(1);
  });
