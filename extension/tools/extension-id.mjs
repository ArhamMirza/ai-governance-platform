// The ID Chrome and Edge give an extension signed with a given key: the first
// 128 bits of the SHA-256 of the public key (DER), written with the letters
// a-p in place of the hex digits 0-f.
import { createHash } from "node:crypto";

export function extensionId(publicKeyBase64) {
  const der = Buffer.from(publicKeyBase64.trim(), "base64");
  if (der.length === 0) throw new Error("The public key is empty or not base64.");
  const hex = createHash("sha256").update(der).digest("hex").slice(0, 32);
  return [...hex].map((digit) => String.fromCharCode("a".charCodeAt(0) + parseInt(digit, 16))).join("");
}
