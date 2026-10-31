import socket, json, sys, tkinter as tk
from pathlib import Path
import private_set_intersection.python as psi
from matching import profile_token
from net_utils import send_msg, recv_msg

def run_match(host):
    profile = json.loads(Path("sample_founder.json").read_text())
    items = profile_token(profile)
    client = psi.client.CreateWithNewKey(False)

    with socket.create_connection((host, 5000)) as sock:
        send_msg(sock, len(items).to_bytes(4, "big"))
        setup = psi.ServerSetup(); setup.ParseFromString(recv_msg(sock))
        req = client.CreateRequest(items)
        send_msg(sock, req.SerializeToString())
        resp = psi.Response(); resp.ParseFromString(recv_msg(sock))
        size = client.GetIntersectionSize(setup, resp)

    return profile, size > 0

def do_consent_and_reveal(host, my_agree, profile, result_label, btn_frame):
    with socket.create_connection((host, 5001)) as sock2:
        send_msg(sock2, b"1" if my_agree else b"0")
        inv_agree = recv_msg(sock2) == b"1"

    btn_frame.pack_forget()
    if my_agree and inv_agree:
        text = "\n".join(f"{k}: {v}" for k, v in profile.items())
        result_label.config(text=f"✅ REVEALED\n\n{text}", fg="#1a7f37")
    else:
        result_label.config(text="❌ Reveal declined.\nNothing shared.", fg="#b91c1c")

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    profile, matched = run_match(host)

    root = tk.Tk()
    root.title("Rahsia — Founder")
    root.geometry("420x320")

    if not matched:
        tk.Label(root, text="❌ NO MATCH", font=("Arial", 20, "bold"), fg="#b91c1c").pack(pady=30)
        tk.Label(root, text="No additional data shared.", font=("Arial", 12)).pack()
        root.mainloop()
        return

    tk.Label(root, text="✅ MATCH FOUND", font=("Arial", 20, "bold"), fg="#1a7f37").pack(pady=30)
    result_label = tk.Label(root, text="", font=("Arial", 12), justify="left")
    result_label.pack(pady=10)

    btn_frame = tk.Frame(root)
    tk.Button(btn_frame, text="Agree", width=12, bg="#1a7f37", fg="white",
              command=lambda: do_consent_and_reveal(host, True, profile, result_label, btn_frame)).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Disagree", width=12, bg="#b91c1c", fg="white",
              command=lambda: do_consent_and_reveal(host, False, profile, result_label, btn_frame)).pack(side="left", padx=10)
    btn_frame.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()