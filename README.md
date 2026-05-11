# Chat Analyser

A chat app with persistent memory where you can see and adjust how the context window gets divided between chat history, summaries, and memories from past conversations. Supports Anthropic and OpenAI models. Memory is stored in [Qdrant](https://qdrant.tech/) via [mem0](https://mem0.ai/).

## Requirements

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [just](https://github.com/casey/just) (optional but handy)
- An OpenAI API key (required regardless of which chat model you use, mem0 uses it for embeddings)
- An Anthropic API key (only if using Claude models)

## Installation

Copy the example env file and fill it in:

```bash
cp .env.example .env
```

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=some-long-random-string
```

Then start everything:

```bash
docker compose up
```

Or with `just`:

```bash
just dev
```

`just dev` starts Docker detached and runs the Tailwind watcher in the foreground. Migrations run automatically on startup.

The app will be at [http://localhost:8000](http://localhost:8000).

## Usage

Create an account, then configure an agent before starting a conversation. The agent is where you set the model, system prompt, and the context budget fractions.

The fractions divide up the effective context window between:

| Fraction | What it controls |
|---|---|
| `chat_history_fraction` | Recent message history |
| `summarised_history_fraction` | mem0 summaries of older history |
| `relevant_chat_history_fraction` | Semantically relevant messages from earlier in the conversation |
| `memory_fraction` | Memories retrieved from other conversations |
| `rag_fraction` | Retrieved documents |

If chat history exceeds its budget the app falls back to summaries and semantic search, which is where tuning these actually matters.

Each response has a details panel showing which memories were fetched, any tool calls, the model's thinking (Claude only), and the exact system prompt and message list that went into the request.

## Common tasks

```bash
just test
just makemigrations
just migrate
just manage <command>
```

Without `just`:

```bash
docker compose run --rm web uv run manage.py <command>
```
