import { createHash, generateKeyPairSync } from "node:crypto";
import { describe, expect, it } from "vitest";

import { extensionId } from "../tools/extension-id.mjs";

function publicKey(): string {
  const { publicKey: key } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  return key.export({ type: "spki", format: "der" }).toString("base64");
}

describe("extensionId", () => {
  it("is 32 letters from a to p", () => {
    expect(extensionId(publicKey())).toMatch(/^[a-p]{32}$/);
  });

  it("is the first half of the key's SHA-256, with the hex digits written a to p", () => {
    const key = publicKey();
    const hex = createHash("sha256").update(Buffer.from(key, "base64")).digest("hex").slice(0, 32);
    const expected = hex.replace(/[0-9a-f]/g, (digit) => "abcdefghijklmnop"["0123456789abcdef".indexOf(digit)]);

    expect(extensionId(key)).toBe(expected);
  });

  it("is the same for the same key, whatever surrounds it, and different for another", () => {
    const key = publicKey();

    expect(extensionId(`  ${key}\n`)).toBe(extensionId(key));
    expect(extensionId(publicKey())).not.toBe(extensionId(key));
  });

  it("maps a known digest to known letters", () => {
    // sha256 of the single byte 0x00 begins 6e340b9cffb37a989ca544e6bb780a2c
    expect(extensionId(Buffer.from([0]).toString("base64"))).toBe("godealjmppldhkjijmkfeeogllhiakcm");
  });

  it("refuses a key that isn't there", () => {
    expect(() => extensionId("")).toThrow();
    expect(() => extensionId("   ")).toThrow();
  });
});
