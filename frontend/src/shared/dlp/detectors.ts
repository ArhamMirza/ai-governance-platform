/**
 * Finding sensitive data in text -- the data-loss-prevention rules, evaluated.
 *
 * Pure functions with no browser or React dependency, so the very same code
 * runs in the rule tester on the Rules page and in the browser extension that
 * guards the AI sites. What the tester says is therefore what the extension
 * does. The text scanned is never sent anywhere by this module; callers get
 * back which rules matched and where, and decide what to report (the
 * extension reports counts only).
 *
 * The built-in detector keys must match backend/app/core/dlp_rules.py
 * (BUILTIN_DETECTORS); a backend test reads BUILTIN_KEYS below to check.
 */

export type Classification = "public" | "internal" | "confidential";
export type RuleAction = "monitor" | "warn" | "block";

/** The built-in detectors. Keep in step with the backend's list. */
export const BUILTIN_KEYS = [
  "credit_card",
  "iban",
  "us_ssn",
  "uk_nino",
  "pk_cnic",
  "api_key",
  "private_key",
  "jwt",
  "password_assignment",
] as const;

export type BuiltinKey = (typeof BUILTIN_KEYS)[number];

export interface ScanRule {
  id: number;
  name: string;
  kind: "builtin" | "keywords" | "regex";
  builtin_key: string | null;
  keywords: string[] | null;
  pattern: string | null;
  classification: Classification;
  action: RuleAction;
}

export interface Range {
  start: number;
  end: number;
}

export interface RuleHit {
  rule: ScanRule;
  /** Where in the text, for highlighting in the tester. The extension never reports these. */
  ranges: Range[];
}

/** The longest text scanned in one go. Longer text is cut, not refused: a
 * pasted document is checked from the start, which is where a reviewer
 * looks first, and the page never stalls on a huge paste. */
export const MAX_SCAN_LENGTH = 200_000;

const CLASSIFICATION_RANK: Record<Classification, number> = {
  public: 0,
  internal: 1,
  confidential: 2,
};

const ACTION_RANK: Record<RuleAction, number> = { monitor: 0, warn: 1, block: 2 };

/**
 * Whether a rule holds for a tool approved for data up to `toolMax`. A tool
 * cleared for confidential data isn't stopped from receiving it; one cleared
 * only for public data is stopped from receiving anything more sensitive. A
 * tool with no clearance (unapproved) is treated as public.
 */
export function ruleApplies(rule: ScanRule, toolMax: Classification | null): boolean {
  return CLASSIFICATION_RANK[rule.classification] > CLASSIFICATION_RANK[toolMax ?? "public"];
}

/** The most severe action among the hits: block over warn over monitor. */
export function strictestAction(hits: RuleHit[]): RuleAction | null {
  let strictest: RuleAction | null = null;
  for (const hit of hits) {
    if (strictest === null || ACTION_RANK[hit.rule.action] > ACTION_RANK[strictest]) {
      strictest = hit.rule.action;
    }
  }
  return strictest;
}

// ---------- check digits ----------

/** The Luhn check every payment card number passes. */
export function luhnValid(digits: string): boolean {
  if (!/^\d+$/.test(digits)) return false;
  let sum = 0;
  let double = false;
  for (let index = digits.length - 1; index >= 0; index -= 1) {
    let digit = digits.charCodeAt(index) - 48;
    if (double) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    double = !double;
  }
  return sum % 10 === 0;
}

/** The mod-97 check an IBAN passes. `iban` has no spaces and is upper case. */
export function ibanValid(iban: string): boolean {
  if (!/^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$/.test(iban)) return false;
  const rearranged = iban.slice(4) + iban.slice(0, 4);
  let remainder = 0;
  for (const char of rearranged) {
    const value = char >= "A" ? String(char.charCodeAt(0) - 55) : char;
    for (const digit of value) {
      remainder = (remainder * 10 + (digit.charCodeAt(0) - 48)) % 97;
    }
  }
  return remainder === 1;
}

function allSameDigit(digits: string): boolean {
  return /^(\d)\1+$/.test(digits);
}

// ---------- the built-in detectors ----------

type Finder = (text: string) => Range[];

function matchesOf(text: string, pattern: RegExp, accept?: (match: string) => boolean): Range[] {
  const found: Range[] = [];
  const global = new RegExp(pattern.source, pattern.flags.includes("g") ? pattern.flags : pattern.flags + "g");
  for (const match of text.matchAll(global)) {
    if (match.index === undefined || match[0].length === 0) continue;
    if (accept && !accept(match[0])) continue;
    found.push({ start: match.index, end: match.index + match[0].length });
  }
  return found;
}

const BUILTIN_FINDERS: Record<BuiltinKey, Finder> = {
  // 13-19 digits (the pattern's length), optionally grouped with spaces or
  // dashes, that pass Luhn and aren't one digit repeated.
  credit_card: (text) =>
    matchesOf(text, /\b\d(?:[ -]?\d){12,18}\b/, (candidate) => {
      const digits = candidate.replace(/[ -]/g, "");
      return !allSameDigit(digits) && luhnValid(digits);
    }),

  iban: (text) =>
    matchesOf(text, /\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b/, (candidate) =>
      ibanValid(candidate.replace(/ /g, "")),
    ),

  // Area numbers 000, 666 and 900-999 are never issued, nor group 00 or serial 0000.
  us_ssn: (text) => matchesOf(text, /\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b/),

  uk_nino: (text) =>
    matchesOf(
      text,
      /\b(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z] ?\d{2} ?\d{2} ?\d{2} ?[A-D]\b/i,
    ),

  pk_cnic: (text) => matchesOf(text, /\b\d{5}-\d{7}-\d\b/),

  api_key: (text) =>
    matchesOf(
      text,
      new RegExp(
        [
          "\\bAKIA[0-9A-Z]{16}\\b", // AWS access key id
          "\\bgh[pousr]_[A-Za-z0-9]{36,}\\b", // GitHub tokens
          "\\bxox[abprs]-[A-Za-z0-9-]{10,}", // Slack tokens
          "\\b[sr]k_live_[A-Za-z0-9]{16,}", // Stripe live keys
          "\\bAIza[0-9A-Za-z_-]{35}\\b", // Google API keys
          "\\bsk-[A-Za-z0-9_-]{20,}", // OpenAI / Anthropic style secret keys
        ].join("|"),
      ),
    ),

  private_key: (text) => matchesOf(text, /-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----/),

  jwt: (text) => matchesOf(text, /\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/),

  password_assignment: (text) =>
    matchesOf(text, /\b(?:password|passwd|pwd|passphrase)\b[ \t]*[:=][ \t]*\S{4,}/i),
};

function isBuiltinKey(key: string | null): key is BuiltinKey {
  return key !== null && (BUILTIN_KEYS as readonly string[]).includes(key);
}

// ---------- the other kinds of rule ----------

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Each word or phrase, ignoring case, not inside a longer word. */
function findKeywords(text: string, keywords: string[]): Range[] {
  const parts = keywords.filter((keyword) => keyword.length > 0).map(escapeRegExp);
  if (parts.length === 0) return [];
  return matchesOf(text, new RegExp(`(?<![\\p{L}\\p{N}])(?:${parts.join("|")})(?![\\p{L}\\p{N}])`, "iu"));
}

/** A custom pattern. A pattern that doesn't compile finds nothing rather than
 * throwing, so one bad rule can't stop the others being checked. */
function findPattern(text: string, pattern: string): Range[] {
  try {
    return matchesOf(text, new RegExp(pattern));
  } catch {
    return [];
  }
}

/** Where one rule matches in `text`. */
export function findRule(text: string, rule: ScanRule): Range[] {
  if (rule.kind === "builtin") {
    return isBuiltinKey(rule.builtin_key) ? BUILTIN_FINDERS[rule.builtin_key](text) : [];
  }
  if (rule.kind === "keywords") return findKeywords(text, rule.keywords ?? []);
  return rule.pattern ? findPattern(text, rule.pattern) : [];
}

/**
 * Checks `text` against the rules, for a tool cleared for data up to
 * `toolMax` (null for a tool nobody has approved). Rules that don't apply to
 * that tool are skipped. Returns the rules that matched, strictest action
 * first, so the first hit is the one to act on.
 */
export function scan(text: string, rules: ScanRule[], toolMax: Classification | null): RuleHit[] {
  const subject = text.length > MAX_SCAN_LENGTH ? text.slice(0, MAX_SCAN_LENGTH) : text;
  const hits: RuleHit[] = [];
  for (const rule of rules) {
    if (!ruleApplies(rule, toolMax)) continue;
    const ranges = findRule(subject, rule);
    if (ranges.length > 0) hits.push({ rule, ranges });
  }
  return hits.sort((a, b) => ACTION_RANK[b.rule.action] - ACTION_RANK[a.rule.action]);
}

/** A match with its middle hidden, for showing in the tester without
 * printing a real card number back onto the screen. */
export function mask(match: string): string {
  if (match.length <= 4) return "•".repeat(match.length);
  return match.slice(0, 2) + "•".repeat(match.length - 4) + match.slice(-2);
}
