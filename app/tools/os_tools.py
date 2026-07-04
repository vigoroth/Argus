import subprocess
from pathlib import Path
from langchain_core.tools import tool


@tool
def read_file(path: str) -> str:
    """Read and return the full text content of a file."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {e}"
    

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating it if it does not exist.
    Use this to save output, create new files, or overwrite existing ones.
    """

    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing file {path}: {e}"
    

@tool
def list_dir(path :str) -> str:
    """List files and directories at the given path.
    Use this to explore what files exist before reading or writing.
    """
    try:
        entries = sorted(Path(path).iterdir())
        lines = []
        for e in entries:
            kind = "DIR" if e.is_dir() else "FILE"
            lines.append(f"{kind:4} {e.name}")
        return "\n".join(lines) if lines else f"No entries in {path}"
    except Exception as e:
        return f"Error listing directory {path}: {e}"

@tool
def run_shell(command: str) -> str:
    """Run a shell command and return its stdout and stderr.
    Use for tasks like counting lines, searching files, or running scripts.
    NEVER run destructive commands like rm -rf.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 30 seconds"
    except Exception as e:
        return f"ERROR: {e}"

# Single list the agent loop imports — add new tools here later
OS_TOOLS = [read_file, write_file, list_dir, run_shell]     