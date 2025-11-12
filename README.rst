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

- ``target/release/quiche-server``
- ``target/release/quiche-client``

Example: Running a QUIC Experiment
=============================================

This section describes a complete example showing how to establish
a **SP QUIC** connection using this framework.

1. Launch the topology
----------------------

Start a multi-interface topology (in our case ``topo_2``) **without any experiment**
to access the Mininet CLI:

.. code-block:: console

   sudo python3 runner.py -t config/topo/topo_2

This opens the interactive Mininet CLI with the nodes already connected
(client, router, server).

---

2. Start the QUIC server
------------------------

On the server node, run the ``quiche`` server binary with the appropriate
certificate and key:

.. code-block:: console

   Server_0 bash -lc 'nohup /home/achraf/quiche/target/release/quiche-server \
      --cert /home/achraf/quiche/certs/cert.pem \
      --key /home/achraf/quiche/certs/key.pem \
      --listen 0.0.0.0:4433 \
      --root /home/achraf/quiche/quiche/examples \
      > /tmp/qserver.log 2>&1 &'

This launches the QUIC server listening on UDP port **4433**.

---

3. Start the clients (forced IP binding)
---------------------------------------

From the client node, start **two clients simultaneously**.
Each one is hardcoded to use a different source IP address,
to force two distinct QUIC paths.

.. code-block:: console

   Client_0 bash -lc 'LOCAL_BIND=10.0.0.1 /home/achraf/quiche/target/release/quiche-client \
      https://10.1.0.1:4433/ --no-verify & \
      LOCAL_BIND=10.0.1.1 /home/achraf/quiche/target/release/quiche-client \
      https://10.1.0.1:4433/ --no-verify & wait'

If everything works, the clients should output:

.. code-block:: none

   Bonjour, vous êtes bien connecté au serveur QUIC multipath

This confirms both paths successfully connect to the same QUIC server.

---

4. Capture traffic on the router
--------------------------------

On the router node, start a packet capture to observe both flows:

.. code-block:: console

   Router_0 tcpdump -ni any udp port 4433 -c 40 -vvv > /tmp/capture.log 2>&1 &

This will capture 40 packets of QUIC traffic on port 4433
from all interfaces.

---

YAML Support (New)
==================

The runner now supports **YAML configuration files** for defining topologies and experiments,
in addition to the legacy ``.para`` format.

This new format improves readability, structure, and automation.

Legacy vs YAML Example
----------------------

**Legacy format (``topo_2``):**

.. code-block:: text

   leftSubnet:10.0
   rightSubnet:10.1
   path_c2r_0:100,20,4
   path_c2r_1:1,20,4
   path_r2s_0:10,20,10
   topoType:MultIf

**YAML format (``topo_2.yaml``):**

.. code-block:: yaml

   version: 1
   topology:
     type: MultiIf
     subnets:
       left: 10.0
       right: 10.1

     paths:
       - link_type: c2r
         id: 0
         delay_ms: 100
         queue_pkts: 20
         bw_mbit: 4

       - link_type: c2r
         id: 1
         delay_ms: 1
         queue_pkts: 20
         bw_mbit: 4

       - link_type: r2s
         id: 0
         delay_ms: 10
         queue_pkts: 20
         bw_mbit: 10


Runner Update
-------------

The ``runner.py`` script has been updated to automatically detect and parse YAML files
using the ``--topo_param_file`` option.

Example command:

.. code-block:: console

   sudo python3 runner.py -t config/topo/topo_2.yaml

When a YAML file is provided:

- The runner loads network parameters via the ``yaml`` Python module.
- The configuration format mirrors the structure of the legacy ``.para`` files.
- Backward compatibility with existing ``.para`` files is preserved.


