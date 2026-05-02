"""
Smoke-test mem0 memory add/search to verify score ordering.

Usage (inside Docker):
    docker compose exec web uv run manage.py test_memory

What it does:
  1. Adds two memories for a throw-away user: one about Rust, one about tea.
  2. Searches with a Rust-related query.
  3. Prints scores — Rust memory should score HIGHER than tea memory.
  4. Deletes both memories from mem0 when done.
"""

from django.core.management.base import BaseCommand

from apps.ai.memory import memory

USER_ID = "test_memory_cmd_user"

RUST_CONVO = [
    {"role": "user", "content": "I've been learning Rust for three months now."},
    {"role": "assistant", "content": "That's great! Rust's ownership model takes time to internalise but it's worth it."},
]

TEA_CONVO = [
    {"role": "user", "content": "I drink green tea every morning, I hate coffee."},
    {"role": "assistant", "content": "Noted! You're a green tea person."},
]

QUERY = "Is Rust a good programming language to learn?"


class Command(BaseCommand):
    help = "Smoke-test mem0 memory scoring (requires real DB + OpenAI key)"

    def handle(self, *args, **options):
        self.stdout.write("Adding test memories…")
        memory.add(RUST_CONVO, user_id=USER_ID)
        memory.add(TEA_CONVO, user_id=USER_ID)

        self.stdout.write(f'\nSearching: "{QUERY}"')
        self.stdout.write("(threshold=0, showing all results so nothing is hidden)\n")

        results = memory.search(QUERY, filters={"user_id": USER_ID}, threshold=0)
        rows = results.get("results", [])

        if not rows:
            self.stdout.write(self.style.WARNING("No memories returned."))
        else:
            for r in rows:
                marker = "RUST" if "rust" in r["memory"].lower() else "tea "
                self.stdout.write(f"  [{marker}] score={r['score']:.4f}  {r['memory']}")

            rust_scores = [r["score"] for r in rows if "rust" in r["memory"].lower()]
            tea_scores  = [r["score"] for r in rows if "rust" not in r["memory"].lower()]

            self.stdout.write("")
            if rust_scores and tea_scores:
                if max(rust_scores) > max(tea_scores):
                    self.stdout.write(self.style.SUCCESS("PASS — Rust scores higher than tea"))
                else:
                    self.stdout.write(self.style.ERROR("FAIL — tea scores higher than Rust (scores still inverted)"))
            elif rust_scores:
                top = max(rust_scores)
                # If patch is broken, scores are raw distances (~0.3-0.4 for Rust).
                # If patch works, scores are similarities (~0.6-0.8 for Rust).
                if top > 0.55:
                    self.stdout.write(self.style.SUCCESS(f"PASS — Rust score {top:.4f} is in similarity range (patch working)"))
                else:
                    self.stdout.write(self.style.ERROR(f"FAIL — Rust score {top:.4f} looks like raw distance, not similarity (patch not working)"))
            else:
                self.stdout.write(self.style.WARNING("No Rust memory stored — mem0 LLM discarded it, cannot evaluate"))

        self.stdout.write("\nCleaning up test memories…")
        all_mems = memory.get_all(filters={"user_id": USER_ID})
        for m in all_mems.get("results", []):
            memory.delete(m["id"])
        self.stdout.write("Done.")
