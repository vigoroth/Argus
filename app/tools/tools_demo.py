
"""Module 2 demo: test each OS tool directly before wiring into the agent.

Run:  python -m app.tools.tools_demo
"""
from app.tools.os_tools import list_dir, read_file, run_shell, write_file


def main() -> None:
    # write a test file
    print(write_file.invoke(
        {"path": "/tmp/agent_test.txt", "content": "hello from the agent\nline 2\n"}
    ))

    # read it back
    print(read_file.invoke({"path": "/tmp/agent_test.txt"}))

    # list the tmp dir (just first 5 entries)
    listing = list_dir.invoke({"path": "/tmp"})
    print("\n".join(listing.splitlines()[:5]))

    # run a shell command
    print(run_shell.invoke({"command": "wc -l /tmp/agent_test.txt"}))


if __name__ == "__main__":
    main()