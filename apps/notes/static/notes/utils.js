// ── CSRF ────────────────────────────────────────────
export const CSRF = document.querySelector('[name=csrfmiddlewaretoken]')?.value ?? '';

export function api(url, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
  };
  if (body !== null) opts.body = JSON.stringify(body);
  return fetch(url, opts).then(r => r.json());
}

// ── Helpers ─────────────────────────────────────────
export function esc(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
