#!/usr/bin/python3
import logging
import os
import subprocess
import tempfile
import traceback
from pathlib import Path

import yaml
from mininet.clean import cleanup
from mininet.cli import CLI
from core.experiment import Experiment, ExperimentParameter
from core.topo import Topo, TopoParameter
from experiments import EXPERIMENTS
from mininet_builder import MininetBuilder
from topos import TOPO_CONFIGS, TOPOS


def get_git_revision_short_hash():
    # Because we might run Minitopo from elsewhere.
    curr_dir = os.getcwd()
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(ROOT_DIR)
    ret = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"]
    ).decode("unicode_escape").strip()
    os.chdir(curr_dir)
    return ret


def _is_yaml(path: str) -> bool:
    return Path(path).suffix.lower() in {".yaml", ".yml"}


def _yaml_topo_to_legacy_tmpfile(yaml_path: str) -> str:
    with open(yaml_path, "r") as f:
        y = yaml.safe_load(f)

    t = y["topology"]
    left = str(t["subnets"]["left"])
    right = str(t["subnets"]["right"])
    topo_type = str(t["type"])

    lines = [f"leftSubnet:{left}", f"rightSubnet:{right}"]

    for idx, p in enumerate(t.get("paths", [])):
        delay = p["delay_ms"]
        queue = p.get("queue_pkts", 100)
        bw = p["bw_mbit"]
        triplet = f"{delay},{queue},{bw}"

        if "link_type" in p and "id" in p:
            key = f"path_{p['link_type']}_{p['id']}"
        else:
            name = str(p.get("name", f"c2r_{idx}"))  # legacy fallback
            key = f"path_{name}"

        lines.append(f"{key}:{triplet}")

    lines.append(f"topoType:{topo_type}")

    tmp = tempfile.NamedTemporaryFile(
        prefix="mtopo_topo_", suffix=".para", delete=False, mode="w"
    )
    tmp.write("\n".join(lines) + "\n")
    tmp.flush()
    tmp.close()
    return tmp.name


class Runner(object):
    """
    Run an experiment described by `experiment_parameter_file` in the topology
    described by `topo_parameter_file` in the network environment built by
    `builder_type`.
    All the operations are done when calling the constructor.
    """

    def __init__(self, builder_type, topo_parameter_file, experiment_parameter_file):
        logging.info("Minitopo version {}".format(get_git_revision_short_hash()))
        self._tmp_files = []

        #Charger/convertir le fichier topo
        topo_param_path = topo_parameter_file
        if _is_yaml(topo_param_path):
            topo_param_path = _yaml_topo_to_legacy_tmpfile(topo_param_path)
            self._tmp_files.append(topo_param_path)
            logging.info(
                f"Converted YAML topo -> legacy: {topo_parameter_file} -> {topo_param_path}"
            )

        #initialiser self.topo_parameter
        self.topo_parameter = TopoParameter(topo_param_path)

        #Builder + Topo + Config
        self.set_builder(builder_type)
        self.apply_topo()
        self.apply_topo_config()

        # 3) Démarrer le réseau
        self.start_topo()
        if experiment_parameter_file:
           self.run_experiment(experiment_parameter_file)
           self.stop_topo()
        else:
           # Pas d’XP -> on ouvre la CLI et on ne stoppe qu’à la sortie
           self.open_cli()
           self.stop_topo()
        #Lancer l'expérience si fournie (sinon on garde la CLI Mininet)
        if experiment_parameter_file:
            self.run_experiment(experiment_parameter_file)
            # Si une expérience est lancée, on peut arrêter ensuite
            self.stop_topo()

    def __del__(self):
        # Meilleure chance de nettoyage des tmp si le process se termine "proprement"
        self._cleanup_tmp_files()

    def _cleanup_tmp_files(self):
        for p in self._tmp_files:
            try:
                os.unlink(p)
            except Exception:
                pass
        self._tmp_files.clear()

    def set_builder(self, builder_type):
        """Currently the only builder type supported is Mininet..."""
        if builder_type == Topo.MININET_BUILDER:
            self.topo_builder = MininetBuilder()
        else:
            raise Exception("I can not find the builder {}".format(builder_type))

    def apply_topo(self):
        """Matches the name of the topo and find the corresponding Topo class."""
        t = self.topo_parameter.get(Topo.TOPO_ATTR)
        if t in TOPOS:
            self.topo = TOPOS[t](self.topo_builder, self.topo_parameter)
        else:
            raise Exception("Unknown topo: {}".format(t))
        logging.info("Using topo {}".format(self.topo))

    def apply_topo_config(self):
        """Match the name of the topo and find the corresponding TopoConfig class."""
        t = self.topo_parameter.get(Topo.TOPO_ATTR)
        if t in TOPO_CONFIGS:
            self.topo_config = TOPO_CONFIGS[t](self.topo, self.topo_parameter)
        else:
            raise Exception("Unknown topo config: {}".format(t))
        logging.info("Using topo config {}".format(self.topo_config))

    def start_topo(self):
        """Initialize the topology with its configuration"""
        self.topo.start_network()
        self.topo_config.configure_network()

    def run_experiment(self, experiment_parameter_file):
        """Match the name of the experiment and launch it"""
        xp = ExperimentParameter(experiment_parameter_file).get(
            ExperimentParameter.XP_TYPE
        )
        if xp in EXPERIMENTS:
            exp = EXPERIMENTS[xp](experiment_parameter_file, self.topo, self.topo_config)
            exp.classic_run()
        else:
            raise Exception("Unknown experiment {}".format(xp))

    def open_cli(self):
       
        net = getattr(self.topo_builder, "net", None)

        # fallback au cas où certains Topo exposent .net
        if net is None:
            net = getattr(self.topo, "net", None)

        if net is None:
            raise AttributeError(
                "Impossible de trouver l'instance Mininet 'net' "
                "(builder/topo). As-tu bien appelé start_network() ?"
            )

        logging.info("Opening Mininet CLI (tape 'exit' pour quitter).")
        CLI(net)

    def stop_topo(self):
        """Stop the topology"""
        try:
            self.topo.stop_network()
        finally:
            self._cleanup_tmp_files()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Minitopo, a wrapper of Mininet to run multipath experiments"
    )
    parser.add_argument(
        "--topo_param_file", "-t", required=True, help="path to the topo parameter file"
    )
    parser.add_argument(
        "--experiment_param_file",
        "-x",
        help="path to the experiment parameter file (optional)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)-15s [%(levelname)s] %(name)s:%(funcName)s: %(message)s",
        force=True,
    )

    try:
        Runner(Topo.MININET_BUILDER, args.topo_param_file, args.experiment_param_file)
    except Exception as e:
        logging.fatal("A fatal error occurred: %s", e)
        traceback.print_exc()
    finally:
        logging.info("cleanup mininet")
        cleanup()
