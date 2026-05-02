from datetime import datetime, timezone

TOOLS = [
    {
        "name": "get_current_timestamp",
        "description": "Returns the current UTC timestamp in ISO 8601 format.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }
]


def execute_tool(name: str, arguments: dict) -> str:
    if name == "get_current_timestamp":
        return datetime.now(timezone.utc).isoformat()
    raise ValueError(f"Unknown tool: {name}")
