import socket, json, tkinter as tk
from pathlib import Path
import private_set_intersection.python as psi
from matching import profile_token
from net_utils import send_msg, recv_msg

def run_match():
    profile = json.loads(Path("sample_investor.json").read_text())
    items = profile_token(profile)
    server = psi.server.CreateWithNewKey(False)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as lis:
        lis.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lis.bind(("0.0.0.0", 5000)); lis.listen(1)
        print("Listening on 0.0.0.0:5000 ...")
        conn, _ = lis.accept()
        with conn:
            client_count = int.from_bytes(recv_msg(conn), "big")
            setup = server.CreateSetupMessage(1e-9, client_count, items, psi.DataStructure.BLOOM_FILTER)
            send_msg(conn, setup.SerializeToString())
            req = psi.Request(); req.ParseFromString(recv_msg(conn))
            resp = server.ProcessRequest(req)
            send_msg(conn, resp.SerializeToString())

    return profile

def wait_consent_and_reveal(my_agree: bool, profile: dict, result_label, btn_frame):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as lis2:
        lis2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lis2.bind(("0.0.0.0", 5001)); lis2.listen(1)
        conn2, _ = lis2.accept()
        with conn2:
            founder_agree = recv_msg(conn2) == b"1"
            send_msg(conn2, b"1" if my_agree else b"0")

    btn_frame.pack_forget()
    if my_agree and founder_agree:
        text = "\n".join(f"{k}: {v}" for k, v in profile.items())
        result_label.config(text=f"✅ REVEALED\n\n{text}", fg="#1a7f37")
    else:
        result_label.config(text="❌ Reveal declined.\nNothing shared.", fg="#b91c1c")

def main():
    profile = run_match()
    matched = True  # run_match only returns on success path; refine below

    root = tk.Tk()
    root.title("Rahsia — Investor")
    root.geometry("420x320")

    status = tk.Label(root, text="✅ MATCH FOUND", font=("Arial", 20, "bold"), fg="#1a7f37")
    status.pack(pady=30)

    result_label = tk.Label(root, text="", font=("Arial", 12), justify="left")
    result_label.pack(pady=10)

    btn_frame = tk.Frame(root)
    def on_agree():
        wait_consent_and_reveal(True, profile, result_label, btn_frame)
    def on_disagree():
        wait_consent_and_reveal(False, profile, result_label, btn_frame)

    tk.Button(btn_frame, text="Agree", width=12, bg="#1a7f37", fg="white", command=on_agree).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Disagree", width=12, bg="#b91c1c", fg="white", command=on_disagree).pack(side="left", padx=10)
    btn_frame.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()