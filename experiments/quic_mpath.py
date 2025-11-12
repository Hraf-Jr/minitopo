import logging, traceback
from core.experiment import Experiment

class QuicMpath(Experiment):
    NAME = "quic_mpath"

    def run(self):
        print(">>> [quic_mpath] run() ENTER", flush=True)
        try:
            get = self.experiment_parameter.get

            server_ip    = get("serverIP")
            client_ip_a  = get("clientIPA")
            client_ip_b  = get("clientIPB")
            port         = int(get("port"))
            server_bin   = get("serverBin")
            client_bin   = get("clientBin")
            cert         = get("cert")
            key          = get("key")
            root         = get("root")
            cap_if1      = get("capIf1")
            cap_if2      = get("capIf2")
            cap_raw      = get("capCount")
            cap_count    = int(cap_raw) if cap_raw not in (None, "", "None") else 200

            print(f"[quic_mpath] params: srv={server_ip}:{port} cliA={client_ip_a} cliB={client_ip_b} cap_if=({cap_if1},{cap_if2}) cap_count={cap_count}", flush=True)

            # --- Sanity: binaires/certificats & interfaces côté r1 ---
            self.topo.command_to(self.topo_config.server, f"test -x {server_bin} && echo '[h2] serverBin OK' || echo '[h2] serverBin MISSING: {server_bin}'")
            self.topo.command_to(self.topo_config.client, f"test -x {client_bin} && echo '[h1] clientBin OK' || echo '[h1] clientBin MISSING: {client_bin}'")
            self.topo.command_to(self.topo_config.server, f"test -r {cert} && test -r {key} && echo '[h2] cert/key OK' || echo '[h2] cert/key MISSING'")
            self.topo.command_to(self.topo_config.router, "echo '[r1] ifaces:'; ip -o link | awk -F': ' '{print $2}' | xargs -n1 echo ' -' > /tmp/r1_ifaces.txt; cat /tmp/r1_ifaces.txt")
            self.topo.command_to(self.topo_config.router, "echo '[r1] tcpdump -D:'; tcpdump -D > /tmp/r1_tcpdumpD.txt 2>&1; tail -n +1 /tmp/r1_tcpdumpD.txt")

            # --- 1) serveur QUIC ---
            cmd_srv = f"nohup {server_bin} --cert {cert} --key {key} --listen 0.0.0.0:{port} --root {root} > /tmp/qserver.log 2>&1 &"
            print(f"[quic_mpath] h2$ {cmd_srv}", flush=True)
            self.topo.command_to(self.topo_config.server, cmd_srv)

            # --- 2) tcpdump avec logs d’erreurs ---
            cmd_cap1 = f"tcpdump -ni {cap_if1} udp port {port} -c {cap_count} -U -vvv -w /tmp/pathA.pcap 2> /tmp/tcpdumpA.err &"
            cmd_cap2 = f"tcpdump -ni {cap_if2} udp port {port} -c {cap_count} -U -vvv -w /tmp/pathB.pcap 2> /tmp/tcpdumpB.err &"
            print(f"[quic_mpath] r1$ {cmd_cap1}", flush=True)
            self.topo.command_to(self.topo_config.router, cmd_cap1)
            print(f"[quic_mpath] r1$ {cmd_cap2}", flush=True)
            self.topo.command_to(self.topo_config.router, cmd_cap2)

            # --- 3) clients (redirigés vers logs) ---
            cmd_cli1 = f"LOCAL_BIND={client_ip_a} {client_bin} https://{server_ip}:{port}/ --no-verify > /tmp/clientA.log 2>&1 &"
            cmd_cli2 = f"LOCAL_BIND={client_ip_b} {client_bin} https://{server_ip}:{port}/ --no-verify > /tmp/clientB.log 2>&1 &"
            print(f"[quic_mpath] h1$ {cmd_cli1}", flush=True)
            self.topo.command_to(self.topo_config.client, cmd_cli1)
            print(f"[quic_mpath] h1$ {cmd_cli2}", flush=True)
            self.topo.command_to(self.topo_config.client, cmd_cli2)

            # --- 4) attente + stop tcpdump ---
            print("[quic_mpath] sleeping 12s then stopping tcpdump…", flush=True)
            self.topo.command_to(self.topo_config.router, "sleep 12; pkill -f 'tcpdump -ni' || true")

            # --- 5) bilan fichiers ---
            self.topo.command_to(self.topo_config.router, "echo '[r1] pcaps:'; ls -lh /tmp/pathA.pcap /tmp/pathB.pcap || true; echo '[r1] tcpdump errs:'; tail -n +1 /tmp/tcpdumpA.err /tmp/tcpdumpB.err || true")
            self.topo.command_to(self.topo_config.client, "echo '[h1] client logs:'; tail -n +1 /tmp/clientA.log /tmp/clientB.log || true")
            self.topo.command_to(self.topo_config.server, "echo '[h2] qserver.log:'; tail -n 30 /tmp/qserver.log || true")

            print("[quic_mpath] run() EXIT", flush=True)

        except Exception as e:
            print("[quic_mpath] EXCEPTION:", e, flush=True)
            traceback.print_exc()
