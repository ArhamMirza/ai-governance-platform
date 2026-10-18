/** What the server accepts as a password (app/core/password_policy.py). Only
 * the length is checked here, so a short one is caught before it is sent; the
 * rest -- common words, sequences, the person's own name -- comes back from
 * the server as a message to show. */
export const MIN_PASSWORD_LENGTH = 12;

export const PASSWORD_HINT = `At least ${MIN_PASSWORD_LENGTH} characters. A few unrelated words works well; avoid common words, keyboard runs and your own name.`;

export const PASSWORD_TOO_SHORT = `Password must be at least ${MIN_PASSWORD_LENGTH} characters`;
