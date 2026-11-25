/* RAG Agent embeddable chat widget. No dependencies.
   Usage: <script src="https://YOUR_API/widget.js" data-agent-key="KEY" data-api-url="https://YOUR_API"></script>
   Calls POST {apiUrl}/api/public/chat with header X-Agent-Key. */
(function () {
  var script = document.currentScript;
  var agentKey = script && script.getAttribute('data-agent-key');
  var apiUrl = (script && script.getAttribute('data-api-url')) || '';
  if (!agentKey) { console.error('[RAG Agent] data-agent-key is required.'); return; }
  apiUrl = apiUrl.replace(/\/$/, '');

  var open = false;
  var messages = [{ role: 'assistant', content: 'Hello! How can I help you today?' }];

  var css = [
    '#rag-widget-btn{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#4f46e5;color:#fff;border:none;cursor:pointer;font-size:24px;z-index:9999;box-shadow:0 8px 24px rgba(79,70,229,.4)}',
    '#rag-widget-panel{position:fixed;bottom:88px;right:20px;width:340px;max-width:calc(100vw - 40px);height:460px;max-height:calc(100vh - 120px);background:#fff;border:1px solid #e2e8f0;border-radius:16px;display:none;flex-direction:column;overflow:hidden;z-index:9999;box-shadow:0 16px 40px rgba(15,23,42,.2);font-family:system-ui,sans-serif}',
    '#rag-widget-panel.open{display:flex}',
    '#rag-widget-head{background:#4f46e5;color:#fff;padding:14px 16px;font-weight:600;font-size:14px}',
    '#rag-widget-body{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px}',
    '.rag-msg{max-width:85%;padding:9px 12px;border-radius:12px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-break:break-word}',
    '.rag-msg.user{align-self:flex-end;background:#4f46e5;color:#fff}',
    '.rag-msg.assistant{align-self:flex-start;background:#f1f5f9;color:#1e293b}',
    '#rag-widget-form{display:flex;gap:8px;padding:10px;border-top:1px solid #e2e8f0}',
    '#rag-widget-input{flex:1;border:1px solid #cbd5e1;border-radius:10px;padding:9px 12px;font-size:14px;outline:none}',
    '#rag-widget-send{background:#4f46e5;color:#fff;border:none;border-radius:10px;padding:0 16px;cursor:pointer;font-weight:600}'
  ].join('\n');
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var btn = document.createElement('button');
  btn.id = 'rag-widget-btn';
  btn.textContent = '💬';
  btn.setAttribute('aria-label', 'Open chat');
  document.body.appendChild(btn);

  var panel = document.createElement('div');
  panel.id = 'rag-widget-panel';
  panel.innerHTML = '<div id="rag-widget-head">AI Assistant</div><div id="rag-widget-body"></div>' +
    '<form id="rag-widget-form"><input id="rag-widget-input" placeholder="Type your message..." autocomplete="off"/><button id="rag-widget-send" type="submit">Send</button></form>';
  document.body.appendChild(panel);

  var body = panel.querySelector('#rag-widget-body');
  function render() {
    body.innerHTML = '';
    messages.forEach(function (m) {
      var d = document.createElement('div');
      d.className = 'rag-msg ' + m.role;
      d.textContent = m.content;
      body.appendChild(d);
    });
    body.scrollTop = body.scrollHeight;
  }
  render();

  btn.addEventListener('click', function () {
    open = !open;
    panel.classList.toggle('open', open);
    btn.textContent = open ? '✕' : '💬';
  });

  panel.querySelector('#rag-widget-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var input = panel.querySelector('#rag-widget-input');
    var text = input.value.trim();
    if (!text) return;
    input.value = '';
    messages.push({ role: 'user', content: text });
    messages.push({ role: 'assistant', content: 'Thinking...' });
    render();
    fetch(apiUrl + '/api/public/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Agent-Key': agentKey },
      body: JSON.stringify({ message: text })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        messages[messages.length - 1] = { role: 'assistant', content: data.response || data.answer || 'Sorry, I could not answer that.' };
        render();
      })
      .catch(function () {
        messages[messages.length - 1] = { role: 'assistant', content: 'Sorry, the agent is unavailable right now. Please try again later.' };
        render();
      });
  });
})();
