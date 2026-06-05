"""画像バイナリのマジックバイト判定。

クライアント申告の MIME を信頼せず、実バイトの先頭シグネチャから形式を判定して
なりすましを防ぐために使う。完全な妥当性検証ではなく、先頭シグネチャの一致のみを見る。
"""

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"


def detect_image_mime(data: bytes) -> str | None:
    """先頭バイトから image/jpeg・image/png・image/webp を判定。判定不能なら None。"""
    if data.startswith(_PNG_SIGNATURE):
        return "image/png"
    if data.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    # WebP は RIFF コンテナ: "RIFF"<4byte size>"WEBP"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
