import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import path from "path";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

const ALLOWED_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
]);
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

const MIME_TO_EXT: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
  "image/gif": "gif",
};

export async function POST(request: NextRequest) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const formData = await request.formData();
  const file = formData.get("file");

  if (!(file instanceof File)) {
    return NextResponse.json(
      { error: "ファイルが見つかりません" },
      { status: 400 },
    );
  }

  if (!ALLOWED_MIME_TYPES.has(file.type)) {
    return NextResponse.json(
      { error: "JPEG, PNG, WebP, GIF のみアップロード可能です" },
      { status: 400 },
    );
  }

  if (file.size > MAX_FILE_SIZE) {
    return NextResponse.json(
      { error: "ファイルサイズは5MB以下にしてください" },
      { status: 400 },
    );
  }

  const ext = MIME_TO_EXT[file.type];

  // Sanitize userId to prevent path traversal (alphanumeric, hyphen, underscore only)
  const safeUserId = session.user.id.replace(/[^a-zA-Z0-9_-]/g, "");
  if (!safeUserId) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }

  // Fixed filename per user — overwrites previous avatar, preventing unbounded disk growth
  const filename = `${safeUserId}.${ext}`;
  const avatarsDir = path.join(process.cwd(), "public", "avatars");
  const filePath = path.join(avatarsDir, filename);

  // Guard: ensure resolved path stays inside avatarsDir (defense-in-depth)
  if (!filePath.startsWith(avatarsDir + path.sep)) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }

  await mkdir(avatarsDir, { recursive: true });

  const buffer = Buffer.from(await file.arrayBuffer());
  await writeFile(filePath, buffer);

  return NextResponse.json({ url: `/avatars/${filename}` });
}
