"""In-memory encoding and newline experiment; no filesystem access."""
from io import BytesIO, TextIOWrapper

if __name__ == "__main__":
    raw = "泵\r\nA\n".encode("utf-8")
    print("bytes:", raw.hex(" "))
    print("decoded:", ascii(raw.decode("utf-8")))
    for newline in (None, ""):
        with TextIOWrapper(BytesIO(raw), encoding="utf-8", newline=newline) as stream:
            print(repr(newline), ascii(stream.read()))
    try:
        raw.decode("ascii")
    except UnicodeDecodeError as error:
        print("ASCII:", type(error).__name__)
