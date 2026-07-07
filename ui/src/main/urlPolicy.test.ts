import { describe, expect, it } from "vitest";
import { isSafeExternalUrl } from "./urlPolicy";

describe("isSafeExternalUrl", () => {
  it.each(["http://example.com", "https://example.com/path?x=1"])(
    "allows %s",
    (url) => {
      expect(isSafeExternalUrl(url)).toBe(true);
    },
  );

  it.each(["file:///C:/tmp/report.txt", "javascript:alert(1)", "app://settings", "", "https://"])(
    "rejects %s",
    (url) => {
      expect(isSafeExternalUrl(url)).toBe(false);
    },
  );
});
