import { describe, it, expect } from "vitest";
import {
  isAllowedImageType,
  validateImageFile,
  MAX_IMAGE_BYTES,
} from "@/lib/image";

function makeFile(type: string, size: number): File {
  const file = new File(["x"], "test", { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

describe("isAllowedImageType", () => {
  it("accepts jpeg, png, webp", () => {
    expect(isAllowedImageType("image/jpeg")).toBe(true);
    expect(isAllowedImageType("image/png")).toBe(true);
    expect(isAllowedImageType("image/webp")).toBe(true);
  });

  it("rejects gif and non-images", () => {
    expect(isAllowedImageType("image/gif")).toBe(false);
    expect(isAllowedImageType("application/pdf")).toBe(false);
  });
});

describe("validateImageFile", () => {
  it("returns null for a valid image", () => {
    expect(validateImageFile(makeFile("image/png", 1024))).toBeNull();
  });

  it("rejects unsupported type", () => {
    expect(validateImageFile(makeFile("image/gif", 1024))).toMatch(
      /JPEG・PNG・WebP/,
    );
  });

  it("rejects oversized image", () => {
    expect(
      validateImageFile(makeFile("image/png", MAX_IMAGE_BYTES + 1)),
    ).toMatch(/5MB/);
  });
});
