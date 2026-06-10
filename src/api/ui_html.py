"""
FastAPI 内嵌的聊天 UI 页面。
访问 http://127.0.0.1:8765/ 即可使用。
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DocAgent</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;height:100vh;display:flex;flex-direction:column}
header{background:#1e293b;padding:14px 20px;border-bottom:1px solid #334155;display:flex;align-items:center;gap:10px}
header h1{font-size:18px;color:#38bdf8}
.status{font-size:12px;padding:4px 10px;border-radius:4px;margin-left:auto}
.status.on{background:#065f46;color:#6ee7b7}
.status.off{background:#7f1d1d;color:#fca5a5}
.chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
.msg{max-width:80%;padding:10px 14px;border-radius:10px;font-size:14px;line-height:1.6}
.msg.user{background:#1e40af;align-self:flex-end}
.msg.bot{background:#1e293b;align-self:flex-start;border:1px solid #334155}
.input{padding:12px 20px;background:#1e293b;border-top:1px solid #334155;display:flex;gap:8px}
.input input{flex:1;padding:10px 14px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;font-size:14px;outline:none}
.input input:focus{border-color:#38bdf8}
.input button{padding:10px 20px;background:#38bdf8;border:none;border-radius:8px;color:#0f172a;font-weight:600;cursor:pointer}
.input button:disabled{opacity:0.5}
.think{color:#64748b;font-style:italic}
.examples{display:flex;gap:8px;padding:8px 20px;background:#1e293b;border-bottom:1px solid #334155;flex-wrap:wrap}
.examples button{background:#0f172a;border:1px solid #334155;color:#94a3b8;padding:6px 12px;border-radius:6px;font-size:12px;cursor:pointer}
.examples button:hover{border-color:#38bdf8;color:#e2e8f0}
</style>
</head>
<body>

<header>
  <h1>📄 DocAgent</h1>
  <span id="st" class="status off">检查中...</span>
</header>

<div class="examples">
  <button onclick="ask('你好')">👋 打招呼</button>
  <button onclick="ask('什么是Transformer？')">🔍 检索</button>
  <button onclick="ask('对比A和B的区别')">📑 对比</button>
  <button onclick="ask('检查合规风险')">✅ 合规</button>
</div>

<div class="chat" id="chat">
  <div class="msg bot">👋 你好！我是 DocAgent，你的企业文档智能助手。</div>
</div>

<div class="input">
  <input id="inp" placeholder="输入问题..." onkeydown="if(event.key=='Enter')send()">
  <button id="btn" onclick="send()">发送</button>
</div>

<script>
(function(){
  var btn=document.getElementById('btn'), inp=document.getElementById('inp'), chat=document.getElementById('chat'), st=document.getElementById('st');
  
  function addMsg(r, h) { var d=document.createElement('div'); d.className='msg '+r; d.innerHTML=h; chat.appendChild(d); d.scrollIntoView({behavior:'smooth'}); }
  
  // 连接检查
  try {
    var x = new XMLHttpRequest();
    x.open('GET', '/api/health', true);
    x.onload = function() { if(x.status==200) { var d=JSON.parse(x.responseText); st.className='status on'; st.textContent='✅ 已连接 ('+d.collection_size+' 条)'; } };
    x.onerror = function() { st.textContent='❌ 未连接'; };
    x.send();
  } catch(e) { st.textContent='❌ 未连接'; }

  function send() {
    var msg=inp.value.trim(); if(!msg) return;
    inp.value=''; btn.disabled=true; btn.textContent='...';
    addMsg('user', msg);
    var tid='t'+Date.now(); var td=document.createElement('div'); td.className='msg bot'; td.id=tid; td.innerHTML='<span class="think">思考中...</span>'; chat.appendChild(td);
    var x=new XMLHttpRequest();
    x.open('POST', '/api/chat', true);
    x.setRequestHeader('Content-Type','application/json');
    x.onload = function() {
      var e=document.getElementById(tid); if(e) e.remove();
      if(x.status==200) {
        var d=JSON.parse(x.responseText);
        var h=''; if(d.intent) h+='<span style="font-size:11px;color:#64748b">🎯 '+d.intent+'</span><br>';
        h+=d.answer;
        if(d.sources&&d.sources.length>0) h+='<br><span style="font-size:11px;color:#38bdf8">📚 '+d.sources.length+' 个来源</span>';
        addMsg('bot', h);
      } else addMsg('bot', '❌ API 错误: '+x.status);
      btn.disabled=false; btn.textContent='发送';
    };
    x.onerror = function() { var e=document.getElementById(tid); if(e) e.remove(); addMsg('bot','❌ 请求失败'); btn.disabled=false; btn.textContent='发送'; };
    x.send(JSON.stringify({query:msg, thread_id:'web'}));
  }
  
  btn.onclick=send; inp.onkeydown=function(e){if(e.key=='Enter')send()};
  window.ask=function(q){inp.value=q;send()};
})();

  // Trace 显示
  var traceContainer = document.getElementById('trace-container');
  var traceCount = document.getElementById('trace-count');
  
  function loadTrace() {
    var x = new XMLHttpRequest();
    x.open('GET', '/api/trace/latest', true);
    x.onload = function() {
      if (x.status === 200) {
        var data = JSON.parse(x.responseText);
        if (data.lines && data.lines.length > 0) {
          traceContainer.innerHTML = data.lines.map(function(l) {
            var color = '#a7f3d0';
            if (l.indexOf('ERROR') > -1) color = '#fca5a5';
            else if (l.indexOf('END') > -1) color = '#64748b';
            return '<div style="color:' + color + '">' + escHtml(l) + '</div>';
          }).join('');
          traceCount.textContent = data.lines.length + ' 条';
        }
      }
    };
    x.send();
  }
  
  function escHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }
  
  // 在 send 成功后刷新 trace
  var origSend = send;
  send = function() {
    origSend();
    setTimeout(loadTrace, 2000);
  };
  
  // 页面加载时也拉一次
  setTimeout(loadTrace, 1000);

</script>

  <!-- Trace 日志 -->
  <div style="max-width:800px;margin:20px auto;background:#1e293b;border-radius:8px;padding:16px;border:1px solid #334155;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <span style="color:#94a3b8;font-size:13px;font-weight:bold;">🔍 Trace 日志</span>
      <span id="trace-count" style="color:#64748b;font-size:11px;">0 条</span>
    </div>
    <div id="trace-container" style="font-family:monospace;font-size:12px;color:#a7f3d0;max-height:200px;overflow-y:auto;background:#0f172a;border-radius:4px;padding:8px;line-height:1.6;">
      <div style="color:#64748b;">等待请求...</div>
    </div>
  </div>

</body>
</html>"""