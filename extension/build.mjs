// Bundles the extension into dist/, ready to "Load unpacked" or to zip.
//
//   npm run build
//
// EXTENSION_PUBLIC_KEY (optional) is the base64 public key from your signing
// key; with it the extension keeps one stable ID across machines, which the
// force-install policy needs when you self-host. See README.md.
import { build } from "esbuild";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { extensionId } from "./tools/extension-id.mjs";

const out = "dist";
await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });

const dev = process.env.DEV_CONFIG === "1";
if (dev) console.warn("DEV_CONFIG=1: this build reads its settings from its own storage. Do not deploy it.");
const common = {
  bundle: true,
  target: "es2023",
  sourcemap: false,
  logLevel: "info",
  // Compiled in only for a development build; absent from every other.
  define: { __DEV_CONFIG__: dev ? "true" : "false" },
};

// The service worker is declared "type": "module".
await build({ ...common, entryPoints: ["src/background.ts"], outfile: `${out}/background.js`, format: "esm" });
// Pages and the content script are plain scripts.
for (const name of ["content", "blocked", "popup"]) {
  await build({ ...common, entryPoints: [`src/${name}.ts`], outfile: `${out}/${name}.js`, format: "iife" });
}

const pkg = JSON.parse(await readFile("package.json", "utf8"));
const manifest = JSON.parse(await readFile("manifest.json", "utf8"));
manifest.version = pkg.version;
if (dev) manifest.name += " (DEV)";
if (process.env.EXTENSION_PUBLIC_KEY) {
  manifest.key = process.env.EXTENSION_PUBLIC_KEY.trim();
  console.log(`Extension ID: ${extensionId(manifest.key)}`);
}
await writeFile(`${out}/manifest.json`, JSON.stringify(manifest, null, 2) + "\n");

await cp("managed_schema.json", `${out}/managed_schema.json`);
await cp("public", out, { recursive: true });
console.log(`Built ${manifest.name} ${manifest.version} into ${out}/`);
