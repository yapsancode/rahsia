import socket, json, threading
from flask import Flask, request, jsonify, render_template_string
import private_set_intersection.python as psi
from matching import profile_token
from net_utils import send_msg, recv_msg
import requests

app = Flask(__name__)
PROFILE = json.loads(open("sample_founder.json").read())
state = {"status": "idle", "revealed": None}
registry = {"founder": PROFILE, "investor": None}
chat_log = []

LM_STUDIO_URL = "http://localhost:1235/v1/chat/completions"

def ask_gemma(question: str) -> str:
    try:
        r = requests.post(LM_STUDIO_URL, json={
            "model": "google/gemma-4-12b-qat", "messages": [{"role": "user", "content": question}]
        }, timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Gemma unavailable: {e}]"

def psi_server_loop():
    server = psi.server.CreateWithNewKey(False)
    items = profile_token(PROFILE, "seeker")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as lis:
        lis.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lis.bind(("0.0.0.0", 5000)); lis.listen(1)
        state["status"] = "listening"
        conn, _ = lis.accept()
        with conn:
            client_count = int.from_bytes(recv_msg(conn), "big")
            setup = server.CreateSetupMessage(1e-9, client_count, items, psi.DataStructure.BLOOM_FILTER)
            send_msg(conn, setup.SerializeToString())
            req = psi.Request(); req.ParseFromString(recv_msg(conn))
            resp = server.ProcessRequest(req)
            send_msg(conn, resp.SerializeToString())
            match_size = -1  # server can't learn size in this role; client reports back separately
    state["status"] = "matched_pending"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as lis2:
        lis2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lis2.bind(("0.0.0.0", 5001)); lis2.listen(1)
        conn2, _ = lis2.accept()
        with conn2:
            msg = recv_msg(conn2).decode()
            investor_matched, investor_agree = msg.split(",")
            investor_matched = investor_matched == "1"
            investor_agree = investor_agree == "1"
            state["status"] = "matched" if investor_matched else "no_match"
            if investor_matched:
                my_agree = state.get("my_agree", False)
                send_msg(conn2, (b"1" if my_agree else b"0"))
                if my_agree and investor_agree:
                    state["revealed"] = PROFILE
                    state["status"] = "revealed"
                else:
                    state["status"] = "declined"

@app.route("/")
def home():
    return render_template_string(FOUNDER_HTML, profile=PROFILE, state=state)

@app.route("/set_agree", methods=["POST"])
def set_agree():
    state["my_agree"] = request.json.get("agree", False)
    return jsonify(ok=True)

@app.route("/status")
def status():
    return jsonify(state)

@app.route("/register", methods=["POST"])
def register():
    registry["investor"] = request.json
    return jsonify(ok=True)

@app.route("/registry")
def get_registry():
    return jsonify(registry)

@app.route("/ask", methods=["POST"])
def ask():
    q = request.json.get("question", "")
    who = request.json.get("who", "founder")
    answer = ask_gemma(q)
    chat_log.append({"who": who, "q": q, "a": answer})
    return jsonify(answer=answer)

@app.route("/ask_relay", methods=["POST"])
def ask_relay():
    return ask()

@app.route("/chatlog")
def get_chatlog():
    return jsonify(chat_log)

@app.route("/admin")
def admin():
    return render_template_string(ADMIN_HTML)

FOUNDER_HTML = """
<h2>Founder Dashboard</h2>
<pre>{{ profile }}</pre>
<p>Status: <b id="status">{{ state.status }}</b></p>
<div id="actions"></div>
<h3>Ask Gemma</h3>
<input id="q" style="width:300px"><button onclick="ask()">Ask</button>
<p id="answer"></p>
<script>
function poll(){
  fetch('/status').then(r=>r.json()).then(s=>{
    document.getElementById('status').innerText = s.status;
    let a = document.getElementById('actions');
    if(s.status==='matched'){
      a.innerHTML = '<button onclick="agree(true)">Agree</button><button onclick="agree(false)">Disagree</button>';
    } else if(s.status==='revealed'){
      a.innerHTML = '<pre>'+JSON.stringify(s.revealed)+'</pre>';
    } else { a.innerHTML=''; }
  });
}
function agree(v){ fetch('/set_agree',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agree:v})}); }
function ask(){
  let q=document.getElementById('q').value;
  fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,who:'founder'})})
   .then(r=>r.json()).then(d=>document.getElementById('answer').innerText=d.answer);
}
setInterval(poll,1500); poll();
</script>
"""

ADMIN_HTML = """
<h2>Admin Dashboard</h2>
<div id="reg"></div>
<h3>Chat Log</h3>
<div id="log"></div>
<script>
function refresh(){
  fetch('/registry').then(r=>r.json()).then(d=>document.getElementById('reg').innerText=JSON.stringify(d,null,2));
  fetch('/chatlog').then(r=>r.json()).then(d=>{
    document.getElementById('log').innerHTML = d.map(e=>`<p><b>${e.who}:</b> ${e.q}<br><i>${e.a}</i></p>`).join('');
  });
}
setInterval(refresh,2000); refresh();
</script>
"""

if __name__ == "__main__":
    threading.Thread(target=psi_server_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5050, threaded=True)