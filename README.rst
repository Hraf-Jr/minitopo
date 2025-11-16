What ?
======

This repository provides a **Python runner** built on `Mininet <http://mininet.org/>`_ 
to create and control simple network topologies with multiple paths.

It can be used for a wide range of networking experiments (TCP, UDP, QUIC, etc.).
In our case, we focus mainly on **QUIC** tests between two hosts.

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
   cargo build --release --bin quiche-server --bin quiche-client

After compilation, you can use the following binaries in your experiment files:

- ``target/release/quiche-server``
- ``target/release/quiche-client``

Example: Running a QUIC Experiment
=============================================

This section describes a complete example showing how to establish
a **Single Path QUIC** connection using this framework.

1. The topology
----------------------

Start a multi-interface topology (in our case ``topo_2.yaml``) **without any experiment**
to access the Mininet CLI:

This topology creates a simple 3-node setup composed of:

- a client host with two network interfaces (10.0.0.1 and 10.0.1.1),
- a router connecting both subnets (10.0.x.0/24),
- a server host reachable on the right subnet (10.1.0.1).

Each interface of the client is connected to the router with its own link characteristics
(delay, bandwidth, queue size). The server receives traffic coming from both paths through the router.


.. code-block:: console

   sudo python3 runner.py -t config/topo/topo_2

This opens the interactive Mininet CLI with the nodes already connected
(client, router, server).

---

Simple Example
--------------

To verify that the runner and topology are working correctly, you can start the
topology and interact with it using the Mininet CLI:

.. code-block:: console

   sudo python3 runner.py -t config/topo/topo_2.yaml

This starts the network with three nodes:

- ``Client_0`` (two interfaces)
- ``Router_0``
- ``Server_0``

Inside the Mininet CLI, you can run simple connectivity tests, for example:

.. code-block:: console

   mininet> Client_0 ping -c 3 Server_0

This confirms that the topology is functional without requiring a full QUIC
experiment. More advanced experiments (QUIC, congestion control, multipath, etc.)
should be handled in dedicated experiment files rather than inside the README.


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

The ``runner.py`` script automatically detects and parse YAML files


