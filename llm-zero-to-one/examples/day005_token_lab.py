"""Toy greedy tokenization with two declared vocabularies. Not a real LLM tokenizer."""


def encode(text, vocabulary):
    pieces, ids, offset = [], [], 0
    candidates = sorted(vocabulary, key=lambda piece: (-len(piece), piece))
    while offset < len(text):
        piece = next((p for p in candidates if text.startswith(p, offset)), None)
        if piece is None:
            raise ValueError(f"No vocabulary coverage at character offset {offset}")
        pieces.append(piece)
        ids.append(vocabulary[piece])
        offset += len(piece)
    return pieces, ids


def main():
    text = "面包8.50元"
    characters = {p: i for i, p in enumerate(["面", "包", "8", ".", "5", "0", "元"])}
    merged = {"面包": 17, "8.50": 43, "元": 64}
    print("unicode_codepoints:", len(text))
    print("utf8_bytes:", len(text.encode("utf-8")))
    for label, vocabulary in [("characters", characters), ("merged", merged)]:
        pieces, ids = encode(text, vocabulary)
        print(f"{label}_pieces:", pieces)
        print(f"{label}_ids:", ids)
        print(f"{label}_count:", len(ids))
        print(f"{label}_roundtrip:", "".join(pieces) == text)


if __name__ == "__main__":
    main()
