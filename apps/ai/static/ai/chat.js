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
  if (!list) return;
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
  data.messages.forEach(m => appendMessage(m.role, m.content, m));
}

function newConversation() {
  currentConversationId = null;
  document.getElementById('chat-messages').innerHTML = '';
  renderConversations();
  document.getElementById('chat-input').focus();
}

// ── Chat ─────────────────────────────────────────────
function makeCollapsible(label, items, renderItem) {
  const el = document.createElement('details');
  el.className = 'meta-block';
  const summary = document.createElement('summary');
  summary.textContent = `${label} (${items.length})`;
  el.appendChild(summary);
  items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'meta-row';
    row.textContent = renderItem(item);
    el.appendChild(row);
  });
  return el;
}

function appendMessage(role, text, meta = {}) {
  const wrap = document.createElement('div');
  wrap.className = `message-wrap ${role}`;

  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.textContent = text;
  wrap.appendChild(div);
  document.getElementById('chat-messages').appendChild(wrap);

  if (role === 'user') {
    const { memories = [], thoughts = [], tool_uses = [] } = meta;
    if (memories.length)
      wrap.appendChild(makeCollapsible('Memories', memories,
        m => `${m.data.memory}\n${m.data.score}\n${m.data.created_at}`));
    if (thoughts.length)
      wrap.appendChild(makeCollapsible('Thoughts', thoughts,
        t => t.content));
    if (tool_uses.length)
      wrap.appendChild(makeCollapsible('Tool calls', tool_uses,
        t => `${t.tool_name}(${JSON.stringify(t.input_data)}) → ${JSON.stringify(t.result)}`));
  }

  scrollChat();
  return div;
}

function scrollChat() {
  const msgs = document.getElementById('chat-messages');
  msgs.scrollTop = msgs.scrollHeight;
}

// async function sendMessage() {
//   const input = document.getElementById('chat-input');
//   const btn = document.getElementById('send-btn');
//   const message = input.value.trim();
//   if (!message || btn.disabled) return;

//   input.value = '';
//   btn.disabled = true;

//   appendMessage('user', message);

//   const thinkingEl = document.createElement('details');
//   thinkingEl.className = 'thinking-block';
//   thinkingEl.open = true;
//   thinkingEl.innerHTML = '<summary>Thinking…</summary><div class="thinking-content"></div>';
//   document.getElementById('chat-messages').appendChild(thinkingEl);
//   const thinkingContent = thinkingEl.querySelector('.thinking-content');

//   const assistantDiv = appendMessage('assistant', '');

//   try {
//     const body = { message };
//     if (currentConversationId) body.conversation_id = currentConversationId;

//     const response = await fetch('/chat/', {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
//       body: JSON.stringify(body),
//     });

//     const reader = response.body.getReader();
//     const decoder = new TextDecoder();
//     let buffer = '';
//     let textStarted = false;

//     while (true) {
//       const { done, value } = await reader.read();
//       if (done) break;
//       buffer += decoder.decode(value, { stream: true });
//       const lines = buffer.split('\n');
//       buffer = lines.pop();

//       for (const line of lines) {
//         if (!line.startsWith('data: ')) continue;
//         const payload = line.slice(6);
//         if (payload === '[DONE]') break;
//         try {
//           const data = JSON.parse(payload);
//           if (data.conversation_id) currentConversationId = data.conversation_id;
//           if (data.thinking) {
//             thinkingContent.textContent += data.thinking;
//             scrollChat();
//           }
//           if (data.text) {
//             if (!textStarted) {
//               textStarted = true;
//               thinkingEl.open = false;
//               thinkingEl.querySelector('summary').textContent = 'Thinking';
//             }
//             assistantDiv.textContent += data.text;
//             scrollChat();
//           }
//         } catch (e) { console.warn('SSE parse error:', e); }
//       }
//     }

//     if (!thinkingContent.textContent) thinkingEl.remove();
//   } catch (err) {
//     assistantDiv.textContent = 'Error: ' + err.message;
//   }

//   btn.disabled = false;
//   input.focus();
//   await loadConversations();
// }

// ── Init ─────────────────────────────────────────────
document.getElementById('new-convo-btn').addEventListener('click', newConversation);

loadConversations();
