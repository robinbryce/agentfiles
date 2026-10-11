# Local models

Local models are a **profile variant**, not a separate stack: the same
`CLAUDE_CONFIG_DIR`, plugins, rules and hooks apply; only the inference
endpoint changes.

## Claude Code + Ollama

Ollama ≥ 0.14 serves the Anthropic Messages API, so Claude Code runs against
it unchanged. The `claude-local` wrapper (written by bootstrap) sets:

```bash
ANTHROPIC_BASE_URL=http://localhost:11434
ANTHROPIC_AUTH_TOKEN=ollama        # any non-empty value
ANTHROPIC_API_KEY=                 # must be empty
ANTHROPIC_DEFAULT_SONNET_MODEL=$LOCAL_MODEL   # also OPUS and HAIKU tiers
```

Pick a model with tool calling (`qwen3-coder`, `gpt-oss:20b`) and give Ollama
enough context: `OLLAMA_CONTEXT_LENGTH=32768` or more; Claude Code needs at
least 32k. `ollama launch claude` is the one-command alternative.

Caveats: claude.ai skill and plugin sync is off when `ANTHROPIC_AUTH_TOKEN`
supplies the credential; Claude Code still makes a few non-inference calls to
Anthropic, so this is not air-gapped.

Use it from any profile: `cd ~/Dev/personal/home && claude-local` runs the
home profile locally.

## pi + Ollama

In `~/.pi-<profile>/models.json`:

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "models": [ { "id": "qwen3-coder" } ]
    }
  }
}
```

Then `/model` in pi, or `Ctrl+S` on it to make it the default for that
profile. A `pi-local` wrapper is not needed; the provider is just another
model in the picker.
