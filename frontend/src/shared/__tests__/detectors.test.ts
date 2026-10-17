import { describe, expect, it } from "vitest";

import {
  BUILTIN_KEYS,
  MAX_SCAN_LENGTH,
  type ScanRule,
  findRule,
  ibanValid,
  luhnValid,
  mask,
  ruleApplies,
  scan,
  strictestAction,
} from "../dlp/detectors";

function builtin(key: string, overrides: Partial<ScanRule> = {}): ScanRule {
  return {
    id: 1,
    name: key,
    kind: "builtin",
    builtin_key: key,
    keywords: null,
    pattern: null,
    classification: "confidential",
    action: "block",
    ...overrides,
  };
}

function found(key: string, text: string): string[] {
  return findRule(text, builtin(key)).map((range) => text.slice(range.start, range.end));
}

describe("check digits", () => {
  it.each(["4111111111111111", "5500005555555559", "378282246310005", "6011111111111117"])(
    "accepts the card number %s",
    (digits) => expect(luhnValid(digits)).toBe(true),
  );

  it.each(["4111111111111112", "5500005555555558", "1234567890123456", "", "41111111x1111111"])(
    "rejects %s",
    (digits) => expect(luhnValid(digits)).toBe(false),
  );

  it.each(["GB82WEST12345698765432", "DE89370400440532013000", "FR1420041010050500013M02606"])(
    "accepts the IBAN %s",
    (iban) => expect(ibanValid(iban)).toBe(true),
  );

  it.each(["GB82WEST12345698765433", "DE89370400440532013001", "GB82", "gb82west12345698765432"])(
    "rejects %s",
    (iban) => expect(ibanValid(iban)).toBe(false),
  );
});

describe("payment card numbers", () => {
  it("finds a card number however it is written", () => {
    expect(found("credit_card", "Card 4111111111111111 expires soon")).toEqual(["4111111111111111"]);
    expect(found("credit_card", "4111 1111 1111 1111")).toEqual(["4111 1111 1111 1111"]);
    expect(found("credit_card", "5500-0055-5555-5559.")).toEqual(["5500-0055-5555-5559"]);
    expect(found("credit_card", "amex 378282246310005!")).toEqual(["378282246310005"]);
  });

  it("finds several, with their places in the text", () => {
    const text = "a 4111111111111111 b 5500005555555559 c";
    const ranges = findRule(text, builtin("credit_card"));

    expect(ranges).toEqual([
      { start: 2, end: 18 },
      { start: 21, end: 37 },
    ]);
  });

  it("ignores digit strings that aren't card numbers", () => {
    expect(found("credit_card", "order 4111111111111112")).toEqual([]); // fails the check digit
    expect(found("credit_card", "0000000000000000")).toEqual([]); // all one digit
    expect(found("credit_card", "call 0300 1234567")).toEqual([]); // too short
    expect(found("credit_card", "ref 1234")).toEqual([]);
    expect(found("credit_card", "")).toEqual([]);
  });

  it("doesn't find a card inside a longer run of digits", () => {
    expect(found("credit_card", "14111111111111111")).toEqual([]);
    expect(found("credit_card", "a4111111111111111")).toEqual([]);
  });
});

describe("bank accounts (IBAN)", () => {
  it("finds an IBAN with or without spaces", () => {
    expect(found("iban", "Pay to GB82 WEST 1234 5698 7654 32 today")).toEqual([
      "GB82 WEST 1234 5698 7654 32",
    ]);
    expect(found("iban", "DE89370400440532013000")).toEqual(["DE89370400440532013000"]);
  });

  it("ignores a lookalike whose check fails", () => {
    expect(found("iban", "GB82 WEST 1234 5698 7654 33")).toEqual([]);
    expect(found("iban", "AB12 CDEF GHIJ KLMN")).toEqual([]);
  });
});

describe("national identifiers", () => {
  it("finds US Social Security numbers but not impossible ones", () => {
    expect(found("us_ssn", "SSN 123-45-6789.")).toEqual(["123-45-6789"]);
    for (const bad of ["000-12-3456", "666-12-3456", "900-12-3456", "123-00-3456", "123-45-0000"]) {
      expect(found("us_ssn", bad), bad).toEqual([]);
    }
    expect(found("us_ssn", "123456789")).toEqual([]);
  });

  it("finds UK National Insurance numbers, with or without spaces and in any case", () => {
    expect(found("uk_nino", "AB 12 34 56 C")).toEqual(["AB 12 34 56 C"]);
    expect(found("uk_nino", "ab123456c")).toEqual(["ab123456c"]);
    for (const bad of ["BG123456A", "GB123456A", "ZZ123456A", "AB123456E", "DA123456A"]) {
      expect(found("uk_nino", bad), bad).toEqual([]);
    }
  });

  it("finds Pakistan CNIC numbers in their dashed form", () => {
    expect(found("pk_cnic", "CNIC 42101-1234567-8 attached")).toEqual(["42101-1234567-8"]);
    expect(found("pk_cnic", "4210112345678")).toEqual([]);
    expect(found("pk_cnic", "421011-1234567-8")).toEqual([]);
    expect(found("pk_cnic", "42101-123456-78")).toEqual([]);
    // Not a CNIC if a digit runs on after it.
    expect(found("pk_cnic", "42101-1234567-89")).toEqual([]);
  });
});

describe("keys, tokens and passwords", () => {
  const aws = "AKIAIOSFODNN7EXAMPLE";
  const github = "ghp_" + "a1B2c3D4".repeat(5);
  const slack = "xoxb-123456789012-abcdefghij";
  const stripe = "sk_live_" + "x9Y8z7W6".repeat(3);
  const google = "AIza" + "SyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q"; // 39 characters
  const secret = "sk-proj-" + "abcdEFGH1234".repeat(3);

  it.each([
    ["AWS access key", aws],
    ["GitHub token", github],
    ["Slack token", slack],
    ["Stripe live key", stripe],
    ["Google API key", google],
    ["secret key", secret],
  ])("finds a %s", (_name, key) => {
    expect(found("api_key", `use ${key} here`)).toEqual([key]);
  });

  it("doesn't flag ordinary words that start the same way", () => {
    expect(found("api_key", "skip this sk-short and AKIA123 and ghp_x")).toEqual([]);
    expect(found("api_key", "the task is risky")).toEqual([]);
  });

  it("finds the start of a private key", () => {
    expect(found("private_key", "-----BEGIN RSA PRIVATE KEY-----\nMIIE")).toEqual([
      "-----BEGIN RSA PRIVATE KEY-----",
    ]);
    expect(found("private_key", "-----BEGIN PRIVATE KEY-----")).toHaveLength(1);
    expect(found("private_key", "-----BEGIN OPENSSH PRIVATE KEY-----")).toHaveLength(1);
    expect(found("private_key", "-----BEGIN PUBLIC KEY-----")).toEqual([]);
    expect(found("private_key", "-----BEGIN CERTIFICATE-----")).toEqual([]);
  });

  it("finds a signed web token", () => {
    const jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r";
    expect(found("jwt", `Authorization: Bearer ${jwt}`)).toEqual([jwt]);
    expect(found("jwt", "eyJhbGci.notatoken")).toEqual([]);
  });

  it("finds a password written out, whatever the case", () => {
    expect(found("password_assignment", "db password = hunter22!")).toEqual(["password = hunter22!"]);
    expect(found("password_assignment", "PASSWD: s3cretvalue")).toEqual(["PASSWD: s3cretvalue"]);
    expect(found("password_assignment", "pwd=abcd")).toEqual(["pwd=abcd"]);
    expect(found("password_assignment", "reset your password")).toEqual([]);
    expect(found("password_assignment", "password: ab")).toEqual([]);
    expect(found("password_assignment", "passwords = abcdef")).toEqual([]);
  });
});

describe("keyword rules", () => {
  const keywords = (list: string[]): ScanRule => ({
    id: 2,
    name: "Clients",
    kind: "keywords",
    builtin_key: null,
    keywords: list,
    pattern: null,
    classification: "confidential",
    action: "warn",
  });

  it("matches words and phrases ignoring case", () => {
    const text = "We won PROJECT falcon and acme corp.";

    const hits = findRule(text, keywords(["Project Falcon", "Acme Corp"]));

    expect(hits.map((r) => text.slice(r.start, r.end))).toEqual(["PROJECT falcon", "acme corp"]);
  });

  it("doesn't match inside a longer word", () => {
    expect(findRule("falconer and falcons", keywords(["falcon"]))).toEqual([]);
    expect(findRule("peregrinefalcon and 2falcon", keywords(["falcon"]))).toEqual([]);
    expect(findRule("a falcon.", keywords(["falcon"]))).toHaveLength(1);
    expect(findRule("(falcon)", keywords(["falcon"]))).toHaveLength(1);
  });

  it("treats the words literally, not as a pattern", () => {
    expect(findRule("Acme (Pty) Ltd. is a client", keywords(["Acme (Pty) Ltd."]))).toHaveLength(1);
    expect(findRule("anything at all", keywords([".*"]))).toEqual([]);
  });

  it("finds nothing with nothing to look for", () => {
    expect(findRule("text", keywords([]))).toEqual([]);
    expect(findRule("text", { ...keywords([]), keywords: null })).toEqual([]);
  });

  it("works on non-English text", () => {
    expect(findRule("منصوبہ فالکن کا ہے", keywords(["فالکن"]))).toHaveLength(1);
  });
});

describe("pattern rules", () => {
  const pattern = (text: string): ScanRule => ({
    id: 3,
    name: "Tickets",
    kind: "regex",
    builtin_key: null,
    keywords: null,
    pattern: text,
    classification: "internal",
    action: "monitor",
  });

  it("finds every match of the pattern", () => {
    const text = "see PROJ-1234 and PROJ-9876, not PROJ-12";

    expect(findRule(text, pattern(String.raw`\bPROJ-\d{4}\b`))).toHaveLength(2);
  });

  it("finds nothing for a pattern that won't compile, instead of failing", () => {
    expect(findRule("text", pattern("(unclosed"))).toEqual([]);
    expect(findRule("text", { ...pattern("x"), pattern: null })).toEqual([]);
  });

  it("skips matches of no length, which would otherwise be reported everywhere", () => {
    expect(findRule("a", pattern("(?=a)"))).toEqual([]);
  });

  it("is case-sensitive unless the pattern says otherwise", () => {
    expect(findRule("proj-1234", pattern(String.raw`PROJ-\d{4}`))).toEqual([]);
    expect(findRule("proj-1234", pattern(String.raw`[Pp][Rr][Oo][Jj]-\d{4}`))).toHaveLength(1);
  });
});

describe("a rule with an unknown detector", () => {
  it("finds nothing", () => {
    expect(findRule("4111111111111111", builtin("not_a_detector"))).toEqual([]);
    expect(findRule("4111111111111111", builtin("credit_card", { builtin_key: null }))).toEqual([]);
  });
});

describe("which rules hold for which tool", () => {
  const rule = (classification: ScanRule["classification"]) =>
    builtin("credit_card", { classification });

  it("stops data more sensitive than the tool is cleared for", () => {
    expect(ruleApplies(rule("confidential"), "internal")).toBe(true);
    expect(ruleApplies(rule("confidential"), "public")).toBe(true);
    expect(ruleApplies(rule("internal"), "public")).toBe(true);
  });

  it("lets through data the tool is cleared to receive", () => {
    expect(ruleApplies(rule("confidential"), "confidential")).toBe(false);
    expect(ruleApplies(rule("internal"), "internal")).toBe(false);
    expect(ruleApplies(rule("internal"), "confidential")).toBe(false);
    expect(ruleApplies(rule("public"), "public")).toBe(false);
  });

  it("treats an unapproved tool as cleared for nothing beyond public", () => {
    expect(ruleApplies(rule("confidential"), null)).toBe(true);
    expect(ruleApplies(rule("internal"), null)).toBe(true);
    expect(ruleApplies(rule("public"), null)).toBe(false);
  });
});

describe("scan", () => {
  const card = builtin("credit_card", { id: 1, action: "warn" });
  const key = builtin("api_key", { id: 2, action: "block" });
  const ticket: ScanRule = {
    id: 3,
    name: "Tickets",
    kind: "regex",
    builtin_key: null,
    keywords: null,
    pattern: String.raw`\bPROJ-\d{4}\b`,
    classification: "internal",
    action: "monitor",
  };
  const text = "PROJ-1234 card 4111111111111111 key AKIAIOSFODNN7EXAMPLE";

  it("returns the rules that matched, strictest first", () => {
    const hits = scan(text, [ticket, card, key], null);

    expect(hits.map((hit) => hit.rule.id)).toEqual([2, 1, 3]);
    expect(strictestAction(hits)).toBe("block");
  });

  it("holds a tool only to rules about data it isn't cleared for", () => {
    expect(scan(text, [ticket, card, key], "internal").map((hit) => hit.rule.id)).toEqual([2, 1]);
    expect(scan(text, [ticket, card, key], "confidential")).toEqual([]);
  });

  it("returns where each rule matched", () => {
    const [hit] = scan(text, [card], null);

    expect(hit.ranges).toEqual([{ start: 15, end: 31 }]);
  });

  it("says nothing matched for clean text", () => {
    expect(scan("Please summarise this article about gardening.", [ticket, card, key], null)).toEqual([]);
    expect(strictestAction([])).toBeNull();
    expect(scan("", [card], null)).toEqual([]);
    expect(scan(text, [], null)).toEqual([]);
  });

  it("still checks the other rules when one is broken", () => {
    const broken: ScanRule = { ...ticket, id: 9, pattern: "(unclosed" };

    expect(scan(text, [broken, card], null).map((hit) => hit.rule.id)).toEqual([1]);
  });

  it("checks only the start of a very long text", () => {
    const filler = "x ".repeat(MAX_SCAN_LENGTH / 2);

    expect(scan("4111111111111111 " + filler, [card], null)).toHaveLength(1);
    expect(scan(filler + "4111111111111111", [card], null)).toEqual([]);
  });
});

describe("mask", () => {
  it("hides the middle of a match", () => {
    expect(mask("4111111111111111")).toBe("41••••••••••••11");
    expect(mask("abcde")).toBe("ab•de");
  });

  it("hides a very short match entirely", () => {
    expect(mask("abcd")).toBe("••••");
    expect(mask("")).toBe("");
  });
});

describe("the built-in list", () => {
  it("has a detector for every key", () => {
    for (const key of BUILTIN_KEYS) {
      expect(typeof findRule("", builtin(key))).toBe("object");
    }
    expect(new Set(BUILTIN_KEYS).size).toBe(BUILTIN_KEYS.length);
  });
});
