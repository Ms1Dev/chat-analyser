FRONTEND_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "htmx_trigger",
            "description": (
                'Fire an HTMX action by name. Available triggers: '
                '"swap-to-map" — Switch the left panel to the map view; '
                '"swap-to-notes" — Switch the left panel back to the note list'
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger": {"type": "string", "description": "One of: swap-to-map, swap-to-notes"},
                },
                "required": ["trigger"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_console",
            "description": "Open the LLM console panel so the user can see log output. Use close_console to hide it.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_console",
            "description": "Close the LLM console panel.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log",
            "description": "Output a short message to the developer console panel in the UI. Use this to report completed actions and their outcomes — not as a replacement for calling action tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to display in the console"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refresh_note_list",
            "description": "Reload the note list from the server so the UI reflects the latest data. Call this after any add or delete.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
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
    {
        "type": "function",
        "function": {
            "name": "drop_pin",
            "description": "Drop a marker on the map at a given location with an optional label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat":   {"type": "number", "description": "Latitude"},
                    "lng":   {"type": "number", "description": "Longitude"},
                    "label": {"type": "string", "description": "Popup label shown on the marker (optional)"},
                },
                "required": ["lat", "lng"],
            },
        },
    },
]

FRONTEND_TOOL_NAMES = {t["function"]["name"] for t in FRONTEND_TOOLS}
