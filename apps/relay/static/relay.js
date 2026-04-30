export class Relay {
  constructor() {
    this._handlers = new Map()
    this._channel = new BroadcastChannel('relay')
  }

  // Built-in: handle htmx_trigger tool calls dispatched from the server
  registerHtmxTriggers() {
    return this.on('htmx_trigger', ({ trigger }) => {
      document.querySelector(`[data-trigger="${trigger}"]`)?.dispatchEvent(new Event(trigger))
    })
  }

  // Register a handler for a named tool call
  on(name, fn) {
    this._handlers.set(name, fn)
    return this
  }

  // Open the SSE connection
  connect() {
    this._startSSE()
    return this
  }

  // ─────────────────────────────────────────────────────
  //
  // Overcoming the issue that some browsers have of only allowing 6 concurrent SSE connections
  // by using navigator.locks to ensure only one tab holds the SSE connection and broadcasting to
  // other tabs via BroadcastChannel.
  //
  // ─────────────────────────────────────────────────────
  _startSSE() {
    // navigator.locks ensures only one tab holds the SSE connection
    navigator.locks.request('relay_lock', () => {
      const es = new EventSource('/relay/events/')
      let release
      const held = new Promise((resolve) => { release = resolve })

      es.addEventListener('tool_call', (event) => {
        const data = JSON.parse(event.data)
        // Dispatch locally — BroadcastChannel doesn't deliver to the sender
        this._dispatch(data)
        // Notify other tabs
        this._channel.postMessage(data)
      })

      es.onerror = () => {
        es.close()
        // Release the lock before retrying. Without this, the tab holds the
        // lock forever while also queuing a new request for it, deadlocking
        // all other tabs that try to open.
        release()
        setTimeout(() => this._startSSE(), 3000)
      }

      // Close the SSE connection on unload so the server frees the thread immediately.
      // The browser releases the lock naturally when the tab is gone.
      window.addEventListener('beforeunload', () => es.close())

      return held
    })

    // Other tabs receive via BroadcastChannel
    this._channel.onmessage = ({ data }) => this._dispatch(data)
  }

  _dispatch({ tool, args }) {
    this._handlers.get(tool)?.(args)
  }
}
