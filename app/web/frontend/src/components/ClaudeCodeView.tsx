import TerminalView from './TerminalView'

// An interactive Claude Code session scoped to the repo (PTY over /claude).
// Reuses the xterm terminal view verbatim — only the WS path differs.
export default function ClaudeCodeView() {
  return <TerminalView path="/claude" />
}
