import os
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

# Stub out apps.ai.memory before it is imported by the providers.
# memory.py connects to pgvector and an embedding model at import time;
# individual tests that care about memory behaviour patch it further.
_mock_memory_module = MagicMock()
sys.modules.setdefault("apps.ai.memory", _mock_memory_module)

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import TestCase  # noqa: E402

from apps.ai.models import Conversation, Message, Thought, ToolUse  # noqa: E402
from apps.ai.providers.anthropic import AnthropicProvider  # noqa: E402
from apps.ai.providers.openai import OpenAIProvider  # noqa: E402

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user_and_conversation():
    user = User.objects.create_user(username="testuser", password="pw")
    convo = Conversation.objects.create(user=user, title="Test")
    return user, convo


def text_event(text):
    e = MagicMock()
    e.type = "content_block_delta"
    e.delta.type = "text_delta"
    e.delta.text = text
    return e


def thinking_event(text):
    e = MagicMock()
    e.type = "content_block_delta"
    e.delta.type = "thinking_delta"
    e.delta.thinking = text
    return e


def block_stop_event():
    e = MagicMock()
    e.type = "content_block_stop"
    return e


def final_message(stop_reason="end_turn", content=None):
    msg = MagicMock()
    msg.stop_reason = stop_reason
    msg.content = content or []
    return msg


def tool_use_block(tool_id, name, input_data):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data
    return block


@contextmanager
def anthropic_stream(events, stop_reason="end_turn", content=None):
    stream = MagicMock()
    stream.__iter__ = lambda _: iter(events)
    stream.get_final_message.return_value = final_message(stop_reason, content)
    yield stream


def make_anthropic_client(calls):
    """calls: list of (events, stop_reason, content) tuples, one per API call."""
    client = MagicMock()
    client.messages.stream.side_effect = [
        anthropic_stream(events, stop_reason, content)
        for events, stop_reason, content in calls
    ]
    return client


# ---------------------------------------------------------------------------
# AnthropicProvider tests
# ---------------------------------------------------------------------------

class AnthropicProviderTextTest(TestCase):
    def _make_provider(self, client):
        with patch("apps.ai.providers.anthropic.anthropic.Anthropic", return_value=client), \
             patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.search.return_value = {"results": []}
            mock_mem.add.return_value = None
            _, convo = make_user_and_conversation()
            provider = AnthropicProvider("hello", conversation_id=convo.id)
            provider._mock_mem = mock_mem
        return provider

    def test_yields_text_chunks(self):
        client = make_anthropic_client([
            ([text_event("hi "), text_event("there")], "end_turn", []),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            chunks = list(provider.stream_response())
        self.assertEqual(chunks, [("text", "hi "), ("text", "there")])

    def test_persists_assistant_message(self):
        client = make_anthropic_client([
            ([text_event("hello!")], "end_turn", []),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        assistant_msg = Message.objects.filter(role="assistant").first()
        self.assertIsNotNone(assistant_msg)
        self.assertEqual(assistant_msg.content, "hello!")

    def test_records_thought(self):
        client = make_anthropic_client([
            ([thinking_event("step 1"), thinking_event(" step 2"), block_stop_event()], "end_turn", []),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        self.assertEqual(Thought.objects.count(), 1)
        self.assertEqual(Thought.objects.first().content, "step 1 step 2")

    def test_no_thought_record_without_thinking(self):
        client = make_anthropic_client([
            ([text_event("answer"), block_stop_event()], "end_turn", []),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        self.assertEqual(Thought.objects.count(), 0)

    def test_records_tool_use(self):
        tool_block = tool_use_block("tid1", "get_current_timestamp", {})
        first_content = [tool_block]
        client = make_anthropic_client([
            ([], "tool_use", first_content),
            ([text_event("done")], "end_turn", []),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        self.assertEqual(ToolUse.objects.count(), 1)
        tu = ToolUse.objects.first()
        self.assertEqual(tu.tool_name, "get_current_timestamp")
        self.assertEqual(tu.input_data, {})
        self.assertIsNotNone(tu.result)

    def test_tool_use_appends_result_to_messages(self):
        tool_block = tool_use_block("tid1", "get_current_timestamp", {})
        first_content = [tool_block]
        client = make_anthropic_client([
            ([], "tool_use", first_content),
            ([text_event("done")], "end_turn", []),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        # Two calls means the tool result was fed back
        self.assertEqual(client.messages.stream.call_count, 2)
        second_call_messages = client.messages.stream.call_args_list[1][1]["messages"]
        tool_result_messages = [
            m for m in second_call_messages
            if isinstance(m.get("content"), list)
            and m["content"][0].get("type") == "tool_result"
        ]
        self.assertEqual(len(tool_result_messages), 1)

    def test_updates_memory_after_response(self):
        client = make_anthropic_client([
            ([text_event("reply")], "end_turn", []),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        mock_mem.add.assert_called_once()
        call_args = mock_mem.add.call_args
        messages_arg = call_args[0][0]
        self.assertEqual(messages_arg[1]["content"], "reply")

    def test_get_tools_converts_parameters_to_input_schema(self):
        _, convo = make_user_and_conversation()
        with patch("apps.ai.providers.anthropic.anthropic.Anthropic"), \
             patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.search.return_value = {"results": []}
            provider = AnthropicProvider("hi", conversation_id=convo.id)
        tools = [{"name": "foo", "description": "bar", "parameters": {"type": "object"}}]
        result = provider._get_tools(tools)
        self.assertIn("input_schema", result[0])
        self.assertNotIn("parameters", result[0])
        self.assertEqual(result[0]["input_schema"], {"type": "object"})


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------

def openai_text_event(text):
    e = MagicMock()
    e.type = "response.output_text.delta"
    e.delta = text
    return e


def openai_thinking_delta(text):
    e = MagicMock()
    e.type = "response.reasoning_summary_text.delta"
    e.delta = text
    return e


def openai_thinking_done():
    e = MagicMock()
    e.type = "response.reasoning_summary_text.done"
    return e


def openai_final_response(output_items=None):
    resp = MagicMock()
    resp.output = output_items or []
    return resp


def openai_function_call_item(call_id, name, arguments_json):
    item = MagicMock()
    item.type = "function_call"
    item.id = f"id_{call_id}"
    item.call_id = call_id
    item.name = name
    item.arguments = arguments_json
    return item


def openai_text_output_item(text):
    item = MagicMock()
    item.type = "output_text"
    item.id = "oid1"
    item.text = text
    return item


@contextmanager
def openai_stream(events, final_response):
    stream = MagicMock()
    stream.__iter__ = lambda _: iter(events)
    stream.get_final_response.return_value = final_response
    yield stream


def make_openai_client(calls):
    """calls: list of (events, final_response) tuples."""
    client = MagicMock()
    client.responses.stream.side_effect = [
        openai_stream(events, resp) for events, resp in calls
    ]
    return client


# ---------------------------------------------------------------------------
# OpenAIProvider tests
# ---------------------------------------------------------------------------

class OpenAIProviderTextTest(TestCase):
    def _make_provider(self, client):
        with patch("apps.ai.providers.openai.OpenAI", return_value=client), \
             patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.search.return_value = {"results": []}
            mock_mem.add.return_value = None
            _, convo = make_user_and_conversation()
            provider = OpenAIProvider("hello", conversation_id=convo.id)
        return provider

    def test_yields_text_chunks(self):
        client = make_openai_client([
            ([openai_text_event("hi "), openai_text_event("there")],
             openai_final_response()),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            chunks = list(provider.stream_response())
        self.assertEqual(chunks, [("text", "hi "), ("text", "there")])

    def test_records_thought(self):
        client = make_openai_client([
            ([openai_thinking_delta("hmm"), openai_thinking_done()],
             openai_final_response()),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        self.assertEqual(Thought.objects.count(), 1)
        self.assertEqual(Thought.objects.first().content, "hmm")

    def test_no_thought_without_thinking(self):
        client = make_openai_client([
            ([openai_text_event("answer")], openai_final_response()),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        self.assertEqual(Thought.objects.count(), 0)

    def test_records_tool_use(self):
        tool_item = openai_function_call_item("cid1", "get_current_timestamp", "{}")
        client = make_openai_client([
            ([], openai_final_response([tool_item])),
            ([openai_text_event("done")], openai_final_response()),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        self.assertEqual(ToolUse.objects.count(), 1)
        tu = ToolUse.objects.first()
        self.assertEqual(tu.tool_name, "get_current_timestamp")
        self.assertEqual(tu.input_data, {})
        self.assertIsNotNone(tu.result)

    def test_tool_result_fed_back(self):
        tool_item = openai_function_call_item("cid1", "get_current_timestamp", "{}")
        client = make_openai_client([
            ([], openai_final_response([tool_item])),
            ([openai_text_event("done")], openai_final_response()),
        ])
        provider = self._make_provider(client)
        with patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.add.return_value = None
            list(provider.stream_response())
        self.assertEqual(client.responses.stream.call_count, 2)
        second_input = client.responses.stream.call_args_list[1][1]["input"]
        tool_outputs = [m for m in second_input if m.get("type") == "function_call_output"]
        self.assertEqual(len(tool_outputs), 1)
        self.assertEqual(tool_outputs[0]["call_id"], "cid1")

    def test_get_tools_adds_type_function_wrapper(self):
        _, convo = make_user_and_conversation()
        with patch("apps.ai.providers.openai.OpenAI"), \
             patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.search.return_value = {"results": []}
            provider = OpenAIProvider("hi", conversation_id=convo.id)
        tools = [{"name": "foo", "description": "bar", "parameters": {"type": "object"}}]
        result = provider._get_tools(tools)
        self.assertEqual(result[0]["type"], "function")
        self.assertEqual(result[0]["name"], "foo")
        self.assertIn("parameters", result[0])


# ---------------------------------------------------------------------------
# BaseProvider tests
# ---------------------------------------------------------------------------

class BaseProviderTest(TestCase):
    def _make_provider(self):
        with patch("apps.ai.providers.anthropic.anthropic.Anthropic"), \
             patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.search.return_value = {"results": []}
            _, convo = make_user_and_conversation()
            provider = AnthropicProvider("hello", conversation_id=convo.id)
        return provider

    def test_persists_user_message_on_init(self):
        _, convo = make_user_and_conversation()
        with patch("apps.ai.providers.anthropic.anthropic.Anthropic"), \
             patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.search.return_value = {"results": []}
            AnthropicProvider("test message", conversation_id=convo.id)
        msg = Message.objects.filter(role="user").first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.content, "test message")

    def test_get_history_returns_ordered_messages(self):
        provider = self._make_provider()
        Message.objects.create(
            conversation_id=provider.conversation_id, role="assistant", content="hi back"
        )
        history, _ = provider._get_history()
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    def test_get_context_records_memory_links(self):
        import uuid
        _, convo = make_user_and_conversation()
        mem_id = str(uuid.uuid4())
        with patch("apps.ai.providers.anthropic.anthropic.Anthropic"), \
             patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.search.return_value = {"results": [
                {"id": mem_id, "memory": "user likes Python", "hash": "abc", "score": 1.0}
            ]}
            provider = AnthropicProvider("hello", conversation_id=convo.id)
        from apps.ai.models import Memory
        self.assertEqual(Memory.objects.filter(message=provider.message).count(), 1)

    def test_system_prompt_includes_memory_context(self):
        import uuid
        _, convo = make_user_and_conversation()
        with patch("apps.ai.providers.anthropic.anthropic.Anthropic"), \
             patch("apps.ai.providers.base.memory") as mock_mem:
            mock_mem.search.return_value = {"results": [
                {"id": str(uuid.uuid4()), "memory": "user likes Python", "hash": "x", "score": 1.0}
            ]}
            provider = AnthropicProvider("hello", conversation_id=convo.id)
        self.assertIn("user likes Python", provider.system)
