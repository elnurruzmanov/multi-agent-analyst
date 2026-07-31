"""F6 — Code agent: generated Python runs in a sandboxed subprocess.

Safety: separate process, 5s timeout, no network imports allowed (basic
denylist), output capped. Defense point: never exec() in-process.
"""

import os
import subprocess
import sys
import tempfile

import config

DENY = ("import os", "import sys", "subprocess", "socket", "requests",
        "urllib", "http", "shutil", "pathlib", "open(", "eval(", "exec(",
        "__import__", "importlib")


def run(question: str) -> str:
    code = config.extract_code(config.llm(
        f"Write minimal python code (print the result) to answer: {question}. Return only code."
    )).removeprefix("python").strip()
    if any(d in code for d in DENY):
        return f"REJECTED unsafe code:\n{code}"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        out = subprocess.run([sys.executable, "-I", path], capture_output=True,
                             text=True, timeout=5)
        result = (out.stdout or out.stderr)[:1000]
    except subprocess.TimeoutExpired:
        result = "TIMEOUT (5s)"
    finally:
        os.unlink(path)
    return f"Code:\n{code}\nOutput:\n{result}"


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "what is 17% of 340?"))
