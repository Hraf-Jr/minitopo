from core.experiment import RandomFileExperiment, RandomFileParameter, ExperimentParameter
import os

class QuicheParameter(RandomFileParameter):
    PORT = "quicPort"
    CERT_PATH = "quicCertPath"
    NO_VERIFY = "quicNoVerify"

    def __init__(self, experiment_parameter_filename):
        super(QuicheParameter, self).__init__(experiment_parameter_filename)
        self.default_parameters.update({
            QuicheParameter.PORT: "6121",
            QuicheParameter.CERT_PATH: "/home/achraf/quiche/certs",
            QuicheParameter.NO_VERIFY: "1",
        })

class QuicheHTTP3(RandomFileExperiment):
    NAME = "quic1"
    PARAMETER_CLASS = QuicheParameter

    SERVER_BIN = "/home/achraf/quiche/target/release/quiche-server"
    CLIENT_BIN = "/home/achraf/quiche/target/release/quiche-client"
    SERVER_LOG = "/tmp/quic_server.log"
    CLIENT_LOG = "/tmp/quic_client.log"

    def __init__(self, experiment_parameter_filename, topo, topo_config):
        super(QuicheHTTP3, self).__init__(experiment_parameter_filename, topo, topo_config)

    def load_parameters(self):
        super(QuicheHTTP3, self).load_parameters()
        self.port = self.experiment_parameter.get(QuicheParameter.PORT)
        self.cert_path = self.experiment_parameter.get(QuicheParameter.CERT_PATH)
        self.no_verify = self.experiment_parameter.get(QuicheParameter.NO_VERIFY)

    def prepare(self):
        super(QuicheHTTP3, self).prepare()
        self.topo.command_to(self.topo_config.server, "rm -f " + QuicheHTTP3.SERVER_LOG)
        self.topo.command_to(self.topo_config.client, "rm -f " + QuicheHTTP3.CLIENT_LOG)
        # place le contenu servi
        self.topo.command_to(self.topo_config.server, "echo hello quiche > /tmp/test.txt")
        # copie des certs dans un chemin sûr du namespace server
        self.topo.command_to(self.topo_config.server, "mkdir -p /tmp/certs && cp -f " +
                             os.path.join(self.cert_path, "*") + " /tmp/certs/ || true")

    def _server_cmd(self):
        # utilise les certs copiés dans /tmp/certs
        cert = "/tmp/certs/cert.pem"
        key = "/tmp/certs/key.pem"
        return (QuicheHTTP3.SERVER_BIN
                + " --listen 0.0.0.0:" + self.port
                + " --root /tmp --cert " + cert
                + " --key " + key
                + " &> " + QuicheHTTP3.SERVER_LOG + " &")

    def _client_cmd(self, server_ip):
        url = "https://" + server_ip + ":" + self.port + "/test.txt"
        args = " --no-verify" if str(self.no_verify) == "1" else ""
        return QuicheHTTP3.CLIENT_BIN + " " + url + args + " &> " + QuicheHTTP3.CLIENT_LOG

    def run(self):
        # démarrage serveur
        self.topo.command_to(self.topo_config.server, self._server_cmd())

        # diagnostic de démarrage (affiche erreur immédiate si ça plante)
        diag = (QuicheHTTP3.SERVER_BIN + " --listen 0.0.0.0:" + self.port
                + " --root /tmp --cert /tmp/certs/cert.pem --key /tmp/certs/key.pem")
        self.topo.command_to(self.topo_config.server, "timeout 3s " + diag + " 2>&1 | head -n 80 | cat || true")

        # vérifs serveur + logs
        self.topo.command_to(self.topo_config.server, "ps -ef | grep -i quiche-server | grep -v grep | cat")
        self.topo.command_to(self.topo_config.server, "ss -lunp | grep :" + self.port + " | cat")
        self.topo.command_to(self.topo_config.server, "head -n 80 " + QuicheHTTP3.SERVER_LOG + " | cat")

        # petite pause
        self.topo.command_to(self.topo_config.client, "sleep 1")

        # client
        server_ip = self.topo_config.get_server_ip()
        self.topo.command_to(self.topo_config.client, self._client_cmd(server_ip))
        self.topo.command_to(self.topo_config.client, "head -n 80 " + QuicheHTTP3.CLIENT_LOG + " | cat")

        # rapatrier les logs dans le répertoire hôte (si présent)
        self.topo.command_to(self.topo_config.server, "test -f /tmp/quic_server.log && cat /tmp/quic_server.log | tee -a logs/quic_server.ns.log >/dev/null || true")
        self.topo.command_to(self.topo_config.client, "test -f /tmp/quic_client.log && cat /tmp/quic_client.log | tee -a logs/quic_client.ns.log >/dev/null || true")

        # cleanup
        self.topo.command_to(self.topo_config.server, "pkill -f quiche-server || true")
