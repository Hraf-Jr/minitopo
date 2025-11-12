from core.experiment import RandomFileExperiment, RandomFileParameter, ExperimentParameter
from topos.multi_interface_multi_client import MultiInterfaceMultiClientConfig
import os


class QUICParameter(RandomFileParameter):
    MULTIPATH = "quicMultipath"
    IMPL = "quicImpl"
    PORT = "quicPort"
    CERT_PATH = "quicCertPath"
    NO_VERIFY = "quicNoVerify"

    def __init__(self, experiment_parameter_filename):
        super(QUICParameter, self).__init__(experiment_parameter_filename)
        self.default_parameters.update({
            QUICParameter.MULTIPATH: "0",
            QUICParameter.IMPL: "quic-go",
            QUICParameter.PORT: "6121",
            QUICParameter.CERT_PATH: "/home/achraf/quiche/certs",
            QUICParameter.NO_VERIFY: "1",
        })


class QUIC(RandomFileExperiment):
    NAME = "quic"
    PARAMETER_CLASS = QUICParameter

    GO_BIN = "/usr/local/go/bin/go"
    WGET = "/home/achraf/git/wget/src/wget"
    SERVER_LOG = "/tmp/quic_server.log"
    CLIENT_LOG = "/tmp/quic_client.log"
    CLIENT_GO_FILE = "/home/achraf/go/src/github.com/lucas-clemente/quic-go/example/client_benchmarker_cached/main.go"
    SERVER_GO_FILE = "/home/achraf/go/src/github.com/lucas-clemente/quic-go/example/main.go"
    CERTPATH = "/home/achraf/go/src/github.com/lucas-clemente/quic-go/example/"
    PING_OUTPUT = "ping.log"

    QUICHE_SERVER = "/home/achraf/quiche/target/release/quiche-server"
    QUICHE_CLIENT = "/home/achraf/quiche/target/release/quiche-client"

    def __init__(self, experiment_parameter_filename, topo, topo_config):
        super(QUIC, self).__init__(experiment_parameter_filename, topo, topo_config)

    def ping(self):
        self.topo.command_to(self.topo_config.client, "rm " + QUIC.PING_OUTPUT)
        count = self.experiment_parameter.get(ExperimentParameter.PING_COUNT)
        for i in range(0, self.topo_config.client_interface_count()):
            cmd = self.ping_command(
                self.topo_config.get_client_ip(i),
                self.topo_config.get_server_ip(),
                n=count
            )
            self.topo.command_to(self.topo_config.client, cmd)

    def ping_command(self, fromIP, toIP, n=5):
        s = "ping -c " + str(n) + " -I " + fromIP + " " + toIP + " >> " + QUIC.PING_OUTPUT
        print(s)
        return s

    def load_parameters(self):
        super(QUIC, self).load_parameters()
        self.multipath = self.experiment_parameter.get(QUICParameter.MULTIPATH)
        self.impl = self.experiment_parameter.get(QUICParameter.IMPL)
        self.port = self.experiment_parameter.get(QUICParameter.PORT)
        self.cert_path = self.experiment_parameter.get(QUICParameter.CERT_PATH)
        self.no_verify = self.experiment_parameter.get(QUICParameter.NO_VERIFY)

    def prepare(self):
        super(QUIC, self).prepare()
        self.topo.command_to(self.topo_config.client, "rm " + QUIC.CLIENT_LOG)
        self.topo.command_to(self.topo_config.server, "rm " + QUIC.SERVER_LOG)
        # Fichier servi par le serveur HTTP/3 (quiche)
        self.topo.command_to(self.topo_config.server, "echo hello quiche > /tmp/test.txt")

    def getQUICServerCmd(self):
        if self.impl == "quiche":
            server_bin = os.path.expanduser(QUIC.QUICHE_SERVER)
            cert = os.path.join(os.path.expanduser(self.cert_path), "cert.pem")
            key = os.path.join(os.path.expanduser(self.cert_path), "key.pem")
            cmd = server_bin + " --listen 0.0.0.0:" + self.port + \
                  " --root /tmp --cert " + cert + " --key " + key + " &> " + QUIC.SERVER_LOG + " &"
            print(cmd)
            return cmd
        s = QUIC.GO_BIN + " run " + QUIC.SERVER_GO_FILE + " -www . -certpath " + self.cert_path + \
            " -bind 0.0.0.0:" + self.port + " &> " + QUIC.SERVER_LOG + " &"
        print(s)
        return s

    def getQUICClientCmd(self):
        server_ip = self.topo_config.get_server_ip()
        if self.impl == "quiche":
            client_bin = os.path.expanduser(QUIC.QUICHE_CLIENT)
            url = "https://" + server_ip + ":" + self.port + "/test.txt"
            args = " --no-verify" if self.no_verify == "1" else ""
            cmd = client_bin + " " + url + args + " &> " + QUIC.CLIENT_LOG
            print(cmd)
            return cmd
        s = QUIC.GO_BIN + " run " + QUIC.CLIENT_GO_FILE
        if int(self.multipath) > 0:
            s += " -m"
        s += " https://" + server_ip + ":" + self.port + "/random &>" + QUIC.CLIENT_LOG
        print(s)
        return s

    def getCongServerCmd(self, congID):
        s = "python " + os.path.dirname(os.path.abspath(__file__)) + \
            "/../utils/https_server.py &> https_server" + str(congID) + ".log &"
        print(s)
        return s

    def getCongClientCmd(self, congID):
        s = "(time " + QUIC.WGET + " https://" + self.topo_config.getCongServerIP(congID) + \
            "/" + self.file + " --no-check-certificate --disable-mptcp) &> https_client" + str(congID) + ".log &"
        print(s)
        return s

    def clean(self):
        super(QUIC, self).clean()

    def run(self):
        cmd = self.getQUICServerCmd()
        self.topo.command_to(self.topo_config.server, "netstat -sn > netstat_server_before")
        self.topo.command_to(self.topo_config.server, cmd)
        # Vérifs serveur
        self.topo.command_to(self.topo_config.server, "ps -ef | grep -i quiche-server | grep -v grep | cat")
        self.topo.command_to(self.topo_config.server, "ss -lunp | grep :" + self.port + " | cat")
        self.topo.command_to(self.topo_config.server, "sleep 1; echo 'exit:' $?; head -n 60 quic_server.log | cat")

        if isinstance(self.topo_config, MultiInterfaceMultiClientConfig):
            i = 0
            for cs in self.topo_config.cong_servers:
                cmd = self.getCongServerCmd(i)
                self.topo.command_to(cs, cmd)
                i = i + 1

        self.topo.command_to(self.topo_config.client, "sleep 2")

        self.topo.command_to(self.topo_config.client, "netstat -sn > netstat_client_before")
        if isinstance(self.topo_config, MultiInterfaceMultiClientConfig):
            i = 0
            for cc in self.topo_config.cong_clients:
                cmd = self.getCongClientCmd(i)
                self.topo.command_to(cc, cmd)
                i = i + 1

        cmd = self.getQUICClientCmd()
        self.topo.command_to(self.topo_config.client, cmd)
        self.topo.command_to(self.topo_config.server, "netstat -sn > netstat_server_after")
        self.topo.command_to(self.topo_config.client, "netstat -sn > netstat_client_after")

        if isinstance(self.topo_config, MultiInterfaceMultiClientConfig):
            for cc in self.topo_config.cong_clients:
                self.topo.command_to(cc, "while pkill -f wget -0; do sleep 0.5; done")

        # Arrêt propre des serveurs
        self.topo.command_to(self.topo_config.server, "pkill -f " + QUIC.SERVER_GO_FILE)
        self.topo.command_to(self.topo_config.server, "pkill -f quiche-server || true")

        if isinstance(self.topo_config, MultiInterfaceMultiClientConfig):
            for cs in self.topo_config.cong_servers:
                self.topo.command_to(cs, "pkill -f https_server.py")

        self.topo.command_to(self.topo_config.client, "sleep 2")
        self.topo.command_to(self.topo_config.client, "rm -r /tmp/go-build*")
        self.topo.command_to(self.topo_config.client, "rm cache_*")
