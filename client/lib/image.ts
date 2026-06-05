export const MAX_IMAGES_PER_MESSAGE = 4;
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const ALLOWED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
] as const;

// detail=high 相当の解像度。OpenAI は high-detail で長辺 2048px に内部リサイズするため、
// これ以上は送ってもトークンを無駄にするだけ。送信前にクライアントで縮小する。
const MAX_DIMENSION = 2048;

export type AllowedImageType = (typeof ALLOWED_IMAGE_TYPES)[number];

export interface PreparedImage {
  mime_type: AllowedImageType;
  data: string; // base64（data URL プレフィックスは含めない）
}

export function isAllowedImageType(type: string): type is AllowedImageType {
  return (ALLOWED_IMAGE_TYPES as readonly string[]).includes(type);
}

export function validateImageFile(file: File): string | null {
  if (!isAllowedImageType(file.type)) {
    return "JPEG・PNG・WebP のみ添付できます";
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return "画像は5MB以下にしてください";
  }
  return null;
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("画像の読み込みに失敗しました"));
    img.src = src;
  });
}

function scaledSize(width: number, height: number): { w: number; h: number } {
  const longest = Math.max(width, height);
  if (longest <= MAX_DIMENSION) return { w: width, h: height };
  const ratio = MAX_DIMENSION / longest;
  return { w: Math.round(width * ratio), h: Math.round(height * ratio) };
}

async function downscale(
  file: File,
  mimeType: AllowedImageType,
): Promise<Blob> {
  const objectUrl = URL.createObjectURL(file);
  try {
    const img = await loadImage(objectUrl);
    const { w, h } = scaledSize(img.naturalWidth, img.naturalHeight);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("画像の変換に失敗しました");
    ctx.drawImage(img, 0, 0, w, h);
    return await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (blob) =>
          blob ? resolve(blob) : reject(new Error("画像の変換に失敗しました")),
        mimeType,
      );
    });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("画像の変換に失敗しました"));
        return;
      }
      resolve(result.split(",", 2)[1] ?? "");
    };
    reader.onerror = () => reject(new Error("画像の変換に失敗しました"));
    reader.readAsDataURL(blob);
  });
}

export async function prepareImage(file: File): Promise<PreparedImage> {
  const error = validateImageFile(file);
  if (error) throw new Error(error);

  const mimeType = file.type as AllowedImageType;
  const blob = await downscale(file, mimeType);
  const data = await blobToBase64(blob);
  return { mime_type: mimeType, data };
}
