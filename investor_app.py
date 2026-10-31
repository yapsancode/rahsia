import socket, json, sys, threading
from flask import Flask, request, jsonify, render_template_string
import private_set_intersection.python as psi
from matching import profile_token
from net_utils import send_msg, recv_msg
import requests

app = Flask(__name__)
PROFILE = json.loads(open("sample_investor.json").read())
FOUNDER_IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
state = {"status": "idle", "matched": False}

def run_match():
    items = profile_token(PROFILE, "provider")
    client = psi.client.CreateWithNewKey(False)
    with socket.create_connection((FOUNDER_IP, 5000)) as sock:
        send_msg(sock, len(items).to_bytes(4, "big"))
        setup = psi.ServerSetup(); setup.ParseFromString(recv_msg(sock))
        req = client.CreateRequest(items)
        send_msg(sock, req.SerializeToString())
        resp = psi.Response(); resp.ParseFromString(recv_msg(sock))
        size = client.GetIntersectionSize(setup, resp)
    state["matched"] = size > 0
    state["status"] = "matched" if state["matched"] else "no_match"

def send_consent(my_agree: bool):
    with socket.create_connection((FOUNDER_IP, 5001)) as sock:
        msg = f"{1 if state['matched'] else 0},{1 if my_agree else 0}"
        send_msg(sock, msg.encode())
        founder_agree = recv_msg(sock) == b"1"
    if my_agree and founder_agree:
        state["status"] = "revealed"
        state["revealed"] = PROFILE
    else:
        state["status"] = "declined"

@app.route("/")
def home():
    return render_template_string(INVESTOR_HTML, profile=PROFILE)

@app.route("/find_match", methods=["POST"])
def find_match():
    threading.Thread(target=run_match, daemon=True).start()
    return jsonify(ok=True)

@app.route("/status")
def status():
    return jsonify(state)

@app.route("/agree", methods=["POST"])
def agree():
    threading.Thread(target=send_consent, args=(request.json.get("agree", False),), daemon=True).start()
    return jsonify(ok=True)

@app.route("/ask", methods=["POST"])
def ask():
    q = request.json.get("question", "")
    try:
        r = requests.post(f"http://{FOUNDER_IP}:5050/ask_relay", json={"question": q, "who": "investor"}, timeout=30)
        return jsonify(answer=r.json()["answer"])
    except Exception as e:
        return jsonify(answer=f"[relay failed: {e}]")

def register_self():
    try:
        requests.post(f"http://{FOUNDER_IP}:5050/register", json=PROFILE, timeout=5)
    except Exception:
        pass

INVESTOR_HTML = """
<h2>Investor Dashboard</h2>
<pre>{{ profile }}</pre>
<button onclick="findMatch()">Find Match</button>
<p>Status: <b id="status">idle</b></p>
<div id="actions"></div>
<h3>Ask Gemma</h3>
<input id="q" style="width:300px"><button onclick="ask()">Ask</button>
<p id="answer"></p>
<script>
function findMatch(){ fetch('/find_match',{method:'POST'}); }
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
function agree(v){ fetch('/agree',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agree:v})}); }
function ask(){
  let q=document.getElementById('q').value;
  fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})})
   .then(r=>r.json()).then(d=>document.getElementById('answer').innerText=d.answer);
}
setInterval(poll,1500); poll();
</script>
"""

if __name__ == "__main__":
    register_self()
    app.run(host="0.0.0.0", port=5051, threaded=True)