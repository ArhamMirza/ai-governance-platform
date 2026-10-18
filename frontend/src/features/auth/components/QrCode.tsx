import qrcode from "qrcode-generator";
import { useMemo } from "react";

interface QrCodeProps {
  /** What the code says: here, the `otpauth://` link for an authenticator app. */
  value: string;
  /** For people who can't see it. */
  label: string;
}

/** A QR code drawn as an inline SVG, so there is no image to load and nothing
 * leaves the page. Dark squares on a light ground in both themes: scanners
 * need the contrast, and a dark-mode inversion would not scan. */
export function QrCode({ value, label }: QrCodeProps) {
  const { size, path } = useMemo(() => {
    const code = qrcode(0, "M");
    code.addData(value);
    code.make();
    const count = code.getModuleCount();
    let squares = "";
    for (let row = 0; row < count; row += 1) {
      for (let column = 0; column < count; column += 1) {
        if (code.isDark(row, column)) squares += `M${column} ${row}h1v1h-1z`;
      }
    }
    return { size: count, path: squares };
  }, [value]);

  // A quiet zone of four squares around it, as the QR standard asks.
  const margin = 4;
  const side = size + margin * 2;

  return (
    <svg
      role="img"
      aria-label={label}
      viewBox={`0 0 ${side} ${side}`}
      width={192}
      height={192}
      shapeRendering="crispEdges"
      className="qr-code"
    >
      <rect width={side} height={side} fill="#ffffff" />
      <path transform={`translate(${margin} ${margin})`} d={path} fill="#000000" />
    </svg>
  );
}
