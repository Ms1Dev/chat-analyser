FRONTEND_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "htmx_trigger",
            "description": (
                'Fire an HTMX action by name. Available triggers: '
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger": {"type": "string", "description": "One of: "},
                },
                "required": ["trigger"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_dark_mode",
            "description": "Enable or disable dark mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dark": {"type": "boolean", "description": "True to enable dark mode, false to disable"},
                },
                "required": ["dark"],
            },
        },
    },
]

FRONTEND_TOOL_NAMES = {t["function"]["name"] for t in FRONTEND_TOOLS}
