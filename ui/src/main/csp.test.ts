import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const readCsp = (): string => {
  const html = readFileSync("src/renderer/index.html", "utf8");
  const match = html.match(/http-equiv="Content-Security-Policy"\s+content="([^"]+)"/);
  if (match === null) {
    throw new Error("Missing CSP meta tag.");
  }
  return match[1];
};

describe("renderer CSP", () => {
  it("keeps the ticket-0002 shell policy and only adds loopback API/media sources", () => {
    expect(readCsp().split("; ")).toEqual([
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self'",
      "img-src 'self' data: http://127.0.0.1:*",
      "connect-src 'self' ws: http://127.0.0.1:*",
    ]);
  });
});
