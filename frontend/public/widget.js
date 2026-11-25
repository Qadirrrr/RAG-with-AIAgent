/* RAG Agent embeddable chat widget. No dependencies.
   Usage: <script src="https://YOUR_API/widget.js" data-agent-key="KEY" data-api-url="https://YOUR_API"></script>
   Calls POST {apiUrl}/api/public/chat with header X-Agent-Key.
   Appearance (title, welcome message, color, position, icon) is loaded from
   GET {apiUrl}/api/public/widget-config; if that fails, built-in defaults
   are used so existing embeds never break. */
(function () {
  var script = document.currentScript;
  var agentKey = script && script.getAttribute('data-agent-key');
  var apiUrl = (script && script.getAttribute('data-api-url')) || '';
  if (!agentKey) { console.error('[RAG Agent] data-agent-key is required.'); return; }
  apiUrl = apiUrl.replace(/\/$/, '');

  var config = {
    title: 'AI Assistant',
    welcomeMessage: 'Hello! How can I help you?',
    color: '#0F766E',
    position: 'right',
    icon: 'chat',
    iconUrl: ''
  };

  var CHAT_ICON = '<svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" aria-hidden="true"><path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/></svg>';
  var ROBOT_ICON = '<svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M20 10V8a3 3 0 0 0-3-3h-2.6A2.4 2.4 0 0 0 12 3a2.4 2.4 0 0 0-2.4 2H7a3 3 0 0 0-3 3v2a3 3 0 0 0-2 3v4a3 3 0 0 0 3 3h14a3 3 0 0 0 3-3v-4a3 3 0 0 0-2-3zM7.35 14.2a1.45 1.45 0 1 0 2.9 0 1.45 1.45 0 1 0-2.9 0zM13.75 14.2a1.45 1.45 0 1 0 2.9 0 1.45 1.45 0 1 0-2.9 0z"/></svg>';

  var open = false;
  var messages = [{ role: 'assistant', content: config.welcomeMessage }];

  var css = [
    '#rag-widget-btn{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#0F766E;color:#fff;border:none;cursor:pointer;font-size:24px;z-index:9999;box-shadow:0 8px 24px rgba(15,118,110,.4);padding:0;overflow:hidden;display:flex;align-items:center;justify-content:center}',
    '#rag-widget-btn img{width:100%;height:100%;object-fit:cover;display:block}',
    '#rag-widget-panel{position:fixed;bottom:88px;right:20px;width:340px;max-width:calc(100vw - 40px);height:460px;max-height:calc(100vh - 120px);background:#fff;border:1px solid #e2e8f0;border-radius:16px;display:none;flex-direction:column;overflow:hidden;z-index:9999;box-shadow:0 16px 40px rgba(15,23,42,.2);font-family:Inter,system-ui,sans-serif}',
    '#rag-widget-panel.open{display:flex}',
    '#rag-widget-head{background:#0F766E;color:#fff;padding:14px 16px;font-weight:600;font-size:14px}',
    '#rag-widget-body{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px}',
    '.rag-msg{max-width:85%;padding:9px 12px;border-radius:12px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-break:break-word}',
    '.rag-msg.user{align-self:flex-end;background:#0F766E;color:#fff}',
    '.rag-msg.assistant{align-self:flex-start;background:#f1f5f9;color:#1e293b}',
    '#rag-widget-form{display:flex;gap:8px;padding:10px;border-top:1px solid #e2e8f0}',
    '#rag-widget-input{flex:1;border:1px solid #cbd5e1;border-radius:10px;padding:9px 12px;font-size:14px;outline:none}',
    '#rag-widget-send{background:#0F766E;color:#fff;border:none;border-radius:10px;padding:0 16px;cursor:pointer;font-weight:600}'
  ].join('\n');
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var btn = document.createElement('button');
  btn.id = 'rag-widget-btn';
  btn.setAttribute('aria-label', 'Open chat');
  document.body.appendChild(btn);

  var panel = document.createElement('div');
  panel.id = 'rag-widget-panel';
  panel.innerHTML = '<div id="rag-widget-head">AI Assistant</div><div id="rag-widget-body"></div>' +
    '<form id="rag-widget-form"><input id="rag-widget-input" placeholder="Type your message..." autocomplete="off"/><button id="rag-widget-send" type="submit">Send</button></form>';
  document.body.appendChild(panel);

  var head = panel.querySelector('#rag-widget-head');
  var sendBtn = panel.querySelector('#rag-widget-send');
  var body = panel.querySelector('#rag-widget-body');

  function hexToRgba(hex, alpha) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + alpha + ')';
  }

  function setLauncherIcon() {
    if (open) {
      btn.textContent = '✕';
      btn.style.fontSize = '20px';
      return;
    }
    btn.style.fontSize = '24px';
    if (config.icon === 'custom' && config.iconUrl) {
      btn.innerHTML = '';
      var img = document.createElement('img');
      img.src = config.iconUrl;
      img.alt = '';
      btn.appendChild(img);
    } else if (config.icon === 'robot') {
      btn.innerHTML = ROBOT_ICON;
    } else {
      btn.innerHTML = CHAT_ICON;
    }
  }

  function render() {
    body.innerHTML = '';
    messages.forEach(function (m) {
      var d = document.createElement('div');
      d.className = 'rag-msg ' + m.role;
      d.textContent = m.content;
      if (m.role === 'user') d.style.background = config.color;
      body.appendChild(d);
    });
    body.scrollTop = body.scrollHeight;
  }

  function applyConfig(data) {
    if (!data) return;
    if (data.title) config.title = data.title;
    if (data.welcome_message) config.welcomeMessage = data.welcome_message;
    if (/^#[0-9a-fA-F]{6}$/.test(data.color || '')) config.color = data.color;
    if (data.position === 'left' || data.position === 'right') config.position = data.position;
    if (data.icon === 'chat' || data.icon === 'robot' || data.icon === 'custom') config.icon = data.icon;
    config.iconUrl = data.icon_url || '';
    if (config.icon === 'custom' && !config.iconUrl) config.icon = 'chat';

    head.textContent = config.title;
    head.style.background = config.color;
    sendBtn.style.background = config.color;
    btn.style.background = config.color;
    btn.style.boxShadow = '0 8px 24px ' + hexToRgba(config.color, 0.4);
    if (config.position === 'left') {
      btn.style.left = '20px';
      btn.style.right = 'auto';
      panel.style.left = '20px';
      panel.style.right = 'auto';
    }
    // Replace the welcome message only while the session is untouched.
    if (messages.length === 1 && messages[0].role === 'assistant') {
      messages[0].content = config.welcomeMessage;
    }
    setLauncherIcon();
    render();
  }

  setLauncherIcon();
  render();

  fetch(apiUrl + '/api/public/widget-config', {
    headers: { 'X-Agent-Key': agentKey }
  })
    .then(function (r) {
      if (!r.ok) throw new Error('widget-config ' + r.status);
      return r.json();
    })
    .then(applyConfig)
    .catch(function () { /* Keep the built-in defaults. */ });

  btn.addEventListener('click', function () {
    open = !open;
    panel.classList.toggle('open', open);
    setLauncherIcon();
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
