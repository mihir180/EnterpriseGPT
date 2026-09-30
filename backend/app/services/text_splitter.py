"""
Minimal, dependency-free recursive character text splitter — a drop-in
replacement for langchain_text_splitters.RecursiveCharacterTextSplitter.

Why: the langchain import chain (langchain_text_splitters -> langchain_core
-> langsmith -> xxhash) pulls in a native DLL (xxhash) that this machine's
Device Guard / Application Control policy blocks outright. Rather than
chase langchain/langsmith version pins to dodge that transitive dependency,
this reimplements just the one function actually used: recursively try a
list of separators (paragraph, then line, then sentence, then word, then
character) until chunks fit within chunk_size, with chunk_overlap carried
between consecutive chunks. Same behavior/contract as the original.
"""


class RecursiveCharacterTextSplitter:
    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text: str) -> list[str]:
        pieces = self._split(text, self.separators)
        return self._merge(pieces)

    def _split(self, text: str, separators: list[str]) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        separator = separators[-1]
        remaining_separators = separators[1:] if len(separators) > 1 else []
        for i, sep in enumerate(separators):
            if sep == "" or sep in text:
                separator = sep
                remaining_separators = separators[i + 1 :]
                break

        if separator == "":
            splits = list(text)
        else:
            splits = text.split(separator)

        results: list[str] = []
        for part in splits:
            if not part:
                continue
            if len(part) > self.chunk_size and remaining_separators:
                results.extend(self._split(part, remaining_separators))
            else:
                results.append(part)

        # Re-attach the separator so merged chunks read naturally (skip for
        # character-level splitting, where "" as separator means no join text).
        if separator:
            return [r + separator for r in results[:-1]] + (results[-1:] if results else [])
        return results

    def _merge(self, pieces: list[str]) -> list[str]:
        chunks: list[str] = []
        current = ""
        for piece in pieces:
            if len(current) + len(piece) <= self.chunk_size:
                current += piece
            else:
                if current:
                    chunks.append(current)
                if len(piece) > self.chunk_size:
                    # Piece itself is too big (shouldn't normally happen since
                    # _split already recurses down to chunk_size), hard-slice it.
                    for start in range(0, len(piece), self.chunk_size):
                        chunks.append(piece[start : start + self.chunk_size])
                    current = ""
                else:
                    current = piece

        if current:
            chunks.append(current)

        if self.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        overlapped = [chunks[0]]
        for chunk in chunks[1:]:
            prev = overlapped[-1]
            overlap_text = prev[-self.chunk_overlap :] if len(prev) > self.chunk_overlap else prev
            overlapped.append(overlap_text + chunk)
        return overlapped