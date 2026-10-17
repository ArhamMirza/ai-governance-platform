// Serves the stub chat page over HTTPS on port 8766. Some AI domains are on the
// browser's built-in HTTPS-only list, so plain http can't be used; the test
// browser is told to accept this throwaway self-signed certificate.
// Needs `openssl` on the path to make the certificate.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import https from "node:https";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "e2e-stub-"));
const key = path.join(dir, "key.pem");
const cert = path.join(dir, "cert.pem");
const made = spawnSync(
  "openssl",
  ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", cert, "-days", "2", "-subj", "/CN=stub"],
  { env: { ...process.env, MSYS_NO_PATHCONV: "1" }, encoding: "utf8" },
);
if (made.status !== 0) {
  console.error("Could not make a test certificate; is openssl installed?\n" + (made.stderr ?? made.error));
  process.exit(1);
}
const page = fs.readFileSync(path.join(here, "stub", "index.html"));
https
  .createServer({ key: fs.readFileSync(key), cert: fs.readFileSync(cert) }, (_req, res) => {
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    res.end(page);
  })
  .listen(8766, () => console.log("stub on 8766"));
