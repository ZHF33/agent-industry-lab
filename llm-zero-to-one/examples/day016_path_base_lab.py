"""Pure lexical path composition. Does not access the filesystem."""
from pathlib import PurePosixPath

if __name__ == "__main__":
    relative = PurePosixPath("inputs/sample.json")
    bases = [PurePosixPath("/demo/project-a"), PurePosixPath("/demo/project-b")]
    for base in bases:
        print(base / relative)
    absolute = PurePosixPath("/demo/shared/sample.json")
    print("absolute:", absolute.is_absolute())
    print("join absolute:", bases[0] / absolute)
    print("same relative text:", str(relative))
