import json

from apps.notes.models import Note

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Add a new note to the note list",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the note"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_note",
            "description": "Delete a note by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "The ID of the note to delete"},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "Return the current list of notes with their IDs and titles",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def execute_tool(name: str, arguments: dict) -> str:
    if name == "add_note":
        title = arguments.get("title", "").strip()
        if not title:
            return json.dumps({"error": "Title required"})
        max_order = Note.objects.order_by("-order").values_list("order", flat=True).first() or 0
        note = Note.objects.create(title=title, order=max_order + 1)
        return json.dumps({"id": note.id, "title": note.title, "order": note.order})

    if name == "delete_note":
        try:
            note = Note.objects.get(id=arguments.get("id"))
            note.delete()
            return json.dumps({"ok": True})
        except Note.DoesNotExist:
            return json.dumps({"error": "Not found"})

    if name == "list_notes":
        notes = list(Note.objects.values("id", "title", "order"))
        return json.dumps({"notes": notes})

    raise ValueError(f"Unknown tool: {name}")
