What ?
======

This repository provides a **Python runner** built on `Mininet <http://mininet.org/>`_ 
to create and control simple network topologies with multiple paths.

It can be used for a wide range of networking experiments (TCP, UDP, QUIC, etc.).
In our case, we focus mainly on **Multipath QUIC** tests between two hosts.

Each experiment is defined by a *topology file* (``.para``) and an *experiment file* (``.xp``)
which describe the network parameters and the commands to execute on each node.

Requirements
============

To run the experiments, you need the following environment:

- **Operating system:** Ubuntu 20.04+ (or WSL2 with Ubuntu)
- **Python:** version 3.8 or newer
- **Mininet:** installed system-wide
- **System tools:** ``iproute2``, ``ethtool``, ``tcpdump``, and ``tshark`` (for packet capture)
- **Optional GUI:** Wireshark (to visualize pcap files)

Quick installation:

.. code-block:: console

   sudo apt-get update
   sudo apt-get install -y mininet iproute2 ethtool tcpdump tshark python3-pip

---

Optional – QUIC experiments (using *quiche*)
--------------------------------------------

If you plan to run **QUIC or Multipath QUIC** experiments, you will also need
the `quiche <https://github.com/cloudflare/quiche>`_ library.

Build the client and server binaries with:

.. code-block:: console

   git clone --recursive https://github.com/cloudflare/quiche.git
   cd quiche
   cargo build --release --bin http3-server --bin http3-client

After compilation, you can use the following binaries in your experiment files:

- ``target/release/http3-server``
- ``target/release/http3-client``

These will be executed automatically by ``runner.py`` when defined in the
corresponding ``.xp`` file.
