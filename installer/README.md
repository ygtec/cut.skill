# cut-skill Installer

> One-command installer for [cut.skill](https://github.com/ygtec/cut.skill) — unified video editing control skill for AI agents.

## Quick Start

### Option 1: curl one-liner (no Node.js required)

```bash
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash
```

Install to a specific agent:

```bash
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --agent claude
```

Install to all 6 agents:

```bash
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --all
```

### Option 2: npx (requires Node.js 18+)

After publishing to npm:

```bash
npx cut-skill install --all
```

Or run directly from GitHub (no npm publish needed):

```bash
npx github:ygtec/cut.skill/installer install --all
```

### Option 3: clone & run

```bash
git clone https://github.com/ygtec/cut.skill.git
cd cut.skill/installer
node cli.mjs install --all --source ..
```

## Commands

```bash
cut-skill install [options]    # Install to agents
cut-skill uninstall [options]  # Remove from agents
cut-skill list                 # Show installed locations
cut-skill update               # Update to latest version
cut-skill detect               # Detect installed agent tools
```

## Install Options

| Option | Description |
|---|---|
| `--agent <name>` | Target agent (comma-separated). One of: `codex`, `claude`, `opencode`, `kimi`, `qwen`, `glm` |
| `--all` | Install to all 6 supported agents |
| `--user` | Install to user-level directory (default) |
| `--project` | Install to current project directory |
| `--source <path>` | Use local repo path instead of downloading |
| `--repo <github>` | Custom GitHub repo (default: `ygtec/cut.skill`) |
| `--ref <git-ref>` | Custom branch/tag (default: `main`) |
| `--force` | Overwrite existing installation |

## Supported Agents

| Agent | User-level path | Project-level path | Config file |
|---|---|---|---|
| Codex CLI | `~/.codex/skills/cut/` | `./skills/cut/` | — |
| Claude Code | `~/.claude/skills/cut/` | `./.claude/skills/cut/` | — |
| OpenCode | `~/.opencode/skills/cut/` | `./.opencode/skills/cut/` | — |
| Kimi Code | `~/.kimi/skills/cut/` | — | `~/.kimi/skills.yaml` |
| Qwen Code | `~/.qwen/skills/cut/` | — | `~/.qwen/skills.json` |
| GLM Code | `~/.glm/skills/cut/` | `./skills/cut/` | — |

## Examples

### Auto-detect and install

```bash
cut-skill install
# Detects installed agent tools and installs to all of them
```

### Install to specific agents

```bash
cut-skill install --agent claude,codex
```

### Install to all 6 agents (force)

```bash
cut-skill install --all --force
```

### Install to current project

```bash
cd my-project
cut-skill install --agent claude --project
# Creates .claude/skills/cut/ in current directory
```

### Offline install (no network)

```bash
# Pre-download the repo
git clone https://github.com/ygtec/cut.skill.git /tmp/cut.skill

# Install from local path
cut-skill install --all --source /tmp/cut.skill
```

### List installations

```bash
cut-skill list
```

Output:
```
cut.skill 安装位置：

  ✓ Codex CLI       [user] /home/user/.codex/skills/cut
  ✓ Claude Code     [user] /home/user/.claude/skills/cut
  ✓ GLM Code        [user] /home/user/.glm/skills/cut
```

### Uninstall

```bash
cut-skill uninstall --agent claude
cut-skill uninstall --all
```

### Update

```bash
cut-skill update
# Re-downloads and reinstalls to all previously installed locations
```

## How It Works

1. **Download**: `git clone` (preferred) or HTTPS zip download
2. **Detect**: Check which agent tools are installed (`codex`, `claude`, etc.)
3. **Install**: Copy skill files to each agent's skill directory
4. **Configure**: For Kimi/Qwen, update their config files (`skills.yaml` / `skills.json`)
5. **Verify**: Check `SKILL.md` exists in each target directory

## Publish to npm (for maintainers)

```bash
cd installer
npm login
npm publish
```

After publishing, users can run:

```bash
npx cut-skill install --all
```

## Files

```
installer/
├── package.json       # npm package definition
├── cli.mjs            # Node.js CLI entry (main)
├── install.sh         # Bash one-liner installer (fallback)
├── src/
│   ├── agents.mjs     # Agent detection & installation logic
│   ├── download.mjs   # GitHub download (git + HTTPS)
│   └── colors.mjs     # Terminal colors (no dependencies)
└── README.md          # This file
```

## License

MIT
