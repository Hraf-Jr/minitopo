# Mininet Runner – Multi-path Experiment Framework (Step-by-Step Guide)

This repository provides a **Python runner** built on **Mininet** to easily launch
network topologies with **multiple paths** and run **custom experiments**
between hosts (e.g., TCP, UDP, QUIC, or others).

> **Default command:**
> ```bash
> sudo python3 runner.py -t <topo_file> -x <xp_file>
> ```
> *(the old `./mpPerf` command is deprecated)*

---

## 0) Goal of this mini-tutorial

The framework can be used for many network experiments.  
In this tutorial, we’ll specifically demonstrate **how to set up a Multipath QUIC
connection** between a client and a server through a router, capture the traffic,
and prepare data for **fingerprinting**.

---

## 1) System requirements

- Ubuntu / WSL with `sudo` privileges  
- Python ≥ 3.8  
- Mininet, `iproute2`, `ethtool`, `tcpdump`, and `tshark` (Wireshark CLI)

Quick install:
```bash
sudo apt-get update
sudo apt-get install -y mininet iproute2 ethtool tcpdump tshark python3-pip
