import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { QrCode } from "../components/QrCode";

const LINK = "otpauth://totp/AI%20Governance%20Platform:ada%40example.com?secret=ABCDEFGH";

describe("QrCode", () => {
  it("is an image with a text label for anyone who can't see it", () => {
    render(<QrCode value={LINK} label="QR code for your authenticator app" />);

    expect(screen.getByRole("img", { name: "QR code for your authenticator app" })).toBeInTheDocument();
  });

  it("draws a square grid with the standard four-square quiet zone", () => {
    const { container } = render(<QrCode value={LINK} label="code" />);

    const svg = container.querySelector("svg") as SVGSVGElement;
    const [, , width, height] = (svg.getAttribute("viewBox") ?? "").split(" ").map(Number);
    // A QR code is (17 + 4 * version) squares across; the quiet zone adds 4 on each side.
    expect((width - 8 - 17) % 4).toBe(0);
    expect(width).toBe(height);
  });

  it("is always dark on light, whatever the theme", () => {
    const { container } = render(<QrCode value={LINK} label="code" />);

    expect(container.querySelector("rect")).toHaveAttribute("fill", "#ffffff");
    expect(container.querySelector("path")).toHaveAttribute("fill", "#000000");
  });

  it("starts with the finder pattern's corner square, which is always dark", () => {
    const { container } = render(<QrCode value={LINK} label="code" />);

    expect(container.querySelector("path")?.getAttribute("d")).toMatch(/^M0 0h1v1h-1z/);
  });

  it("encodes different values differently, and the same value the same way", () => {
    const first = render(<QrCode value={LINK} label="a" />);
    const again = render(<QrCode value={LINK} label="b" />);
    const other = render(<QrCode value={`${LINK}X`} label="c" />);

    const d = (container: HTMLElement) => container.querySelector("path")?.getAttribute("d");
    expect(d(first.container)).toBe(d(again.container));
    expect(d(first.container)).not.toBe(d(other.container));
  });

  it("puts nothing in the page but shapes: no scripts, images or links", () => {
    const { container } = render(<QrCode value={LINK} label="code" />);

    expect(container.querySelector("script, img, a, foreignObject")).toBeNull();
    expect(container.innerHTML).not.toContain("ABCDEFGH");
  });
});
