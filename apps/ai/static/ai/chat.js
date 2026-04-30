import { api, CSRF } from './utils.js';

// ── Conversations ────────────────────────────────────
let conversations = [];
let currentConversationId = null;

async function loadConversations() {
  const data = await api('/chat/conversations/');
  conversations = data.conversations;
  renderConversations();
}

function renderConversations() {
  const list = document.getElementById('convos-list');
  list.innerHTML = '';
  conversations.forEach(c => {
    const item = document.createElement('div');
    item.className = 'convo-item' + (c.id === currentConversationId ? ' active' : '');
    item.dataset.id = c.id;
    item.textContent = c.title;
    item.title = c.title;
    item.onclick = () => selectConversation(c.id);
    list.appendChild(item);
  });
}

async function selectConversation(id) {
  currentConversationId = id;
  renderConversations();
  const data = await api(`/chat/conversations/${id}/messages/`);
  const msgs = document.getElementById('chat-messages');
  msgs.innerHTML = '';
  data.messages.forEach(m => appendMessage(m.role, m.content));
}

function newConversation() {
  currentConversationId = null;
  document.getElementById('chat-messages').innerHTML = '';
  renderConversations();
  document.getElementById('chat-input').focus();
}

// ── Chat ─────────────────────────────────────────────
function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.textContent = text;
  document.getElementById('chat-messages').appendChild(div);
  scrollChat();
  return div;
}

function scrollChat() {
  const msgs = document.getElementById('chat-messages');
  msgs.scrollTop = msgs.scrollHeight;
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const btn = document.getElementById('send-btn');
  const message = input.value.trim();
  if (!message || btn.disabled) return;

  input.value = '';
  btn.disabled = true;

  appendMessage('user', message);
  const assistantDiv = appendMessage('assistant', '');

  try {
    const body = { message };
    if (currentConversationId) body.conversation_id = currentConversationId;

    const response = await fetch('/chat/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(body),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') break;
        try {
          const data = JSON.parse(payload);
          if (data.conversation_id) currentConversationId = data.conversation_id;
          if (data.text) {
            assistantDiv.textContent += data.text;
            scrollChat();
          }
        } catch (e) { console.warn('SSE parse error:', e); }
      }
    }
  } catch (err) {
    assistantDiv.textContent = 'Error: ' + err.message;
  }

  btn.disabled = false;
  input.focus();
  await loadConversations();
}

// ── Init ─────────────────────────────────────────────
document.getElementById('chat-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
document.getElementById('send-btn').addEventListener('click', sendMessage);
document.getElementById('new-convo-btn').addEventListener('click', newConversation);

loadConversations();
