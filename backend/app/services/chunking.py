from __future__ import annotations


def split_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if chunk_size < 100:
        raise ValueError("文本块大小不能小于 100")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("重叠长度必须小于文本块大小")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        target_end = min(start + chunk_size, length)
        end = target_end
        if target_end < length:
            search_start = start + int(chunk_size * 0.55)
            newline = normalized.rfind("\n", search_start, target_end)
            sentence = max(
                normalized.rfind("。", search_start, target_end),
                normalized.rfind("！", search_start, target_end),
                normalized.rfind("？", search_start, target_end),
                normalized.rfind(".", search_start, target_end),
            )
            boundary = max(newline, sentence)
            if boundary > start:
                end = boundary + 1

        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(start + 1, end - overlap)
    return chunks
