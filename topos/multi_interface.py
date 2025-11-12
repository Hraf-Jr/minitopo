from core.topo import Topo, TopoConfig, TopoParameter
import logging


class MultiInterfaceTopo(Topo):
    NAME = "MultiIf"

    def __init__(self, topo_builder, parameterFile):
        logging.info("Initializing MultiInterfaceTopo...")
        super(MultiInterfaceTopo, self).__init__(topo_builder, parameterFile)
        self.client = self.add_client()
        self.server = self.add_server()
        self.router = self.add_router()
        self.c2r_links = []
        self.r2s_links = []

        # Add client - router links
        for l in self.get_client_to_router_links():
            self.c2r_links.append(self.add_bottleneck_link(self.client, self.router, link_characteristics=l))

        # Special case: if there is no specified link between router and server, directly connect them!
        if len(self.get_router_to_server_links()) > 0:
            for l in self.get_router_to_server_links():
                self.r2s_links.append(self.add_bottleneck_link(self.router, self.server, link_characteristics=l))
        else:
            self.add_link(self.router, self.server)
            

    def get_client_to_router_links(self):
        return [l for l in self.topo_parameter.link_characteristics if l.link_type == "c2r"]

    def get_router_to_server_links(self):
        return [l for l in self.topo_parameter.link_characteristics if l.link_type == "r2s"]

    def __str__(self):
        s = "Simple multiple interface topology \n"
        i = 0
        nc = len(self.get_client_to_router_links())
        ns = len(self.get_router_to_server_links())
        m = max(nc, ns)
        skipped = 0
        for i in range(0, m):
            if i == m // 2:
                if m % 2 == 0:
                    s = s + "c                r                s\n"
                    s = s + " \-sw---bl---sw-/ \-sw---bl---sw-/\n"
                else:
                    s = s + "c--sw---bl---sw--r--sw---bl---sw--s\n"
            else:
                if i < m // 2:
                    if (nc == m and ns + skipped == m) or (ns == m and nc + skipped == m):
                        s = s + " /-sw---bl---sw-\ /-sw---bl---sw-\ \n"
                    elif nc == m:
                        s = s + " /-sw---bl---sw-\ \n"
                        skipped += 1
                    else:
                        s = s + "                  /-sw---bl---sw-\ \n"
                        skipped += 1
                else:
                    if (nc == m and ns + skipped == m) or (ns == m and nc + skipped == m):
                        s = s + " \-sw---bl---sw-/ \-sw---bl---sw-/ \n"
                    elif nc == m:
                        s = s + " \-sw---bl---sw-/ \n"
                        skipped += 1
                    else:
                        s = s + "                  \-sw---bl---sw-/ \n"
                        skipped += 1
        
        return s


class MultiInterfaceConfig(TopoConfig):
    NAME = "MultiIf"

    def __init__(self, topo, param):
        super(MultiInterfaceConfig, self).__init__(topo, param)

    def configure_routing(self):
       print("\n=== CONFIGURE ROUTING (MultiInterfaceConfig) ===")

       # routes côté client (une table par lien c2r)
       for i, _ in enumerate(self.topo.c2r_links):
           print(f"[CLIENT] table={i} ip={self.get_client_ip(i)} subnet={self.get_client_subnet(i)} via {self.get_router_ip_to_client_switch(i)}")
           cmd = self.add_table_route_command(self.get_client_ip(i), i)
           print(f"[Client] $ {cmd}")
           self.topo.command_to(self.client, cmd)

           cmd = self.add_link_scope_route_command(self.get_client_subnet(i), self.get_client_interface(0, i), i)
           print(f"[Client] $ {cmd}")
           self.topo.command_to(self.client, cmd)

           cmd = self.add_table_default_route_command(self.get_router_ip_to_client_switch(i), i)
           print(f"[Client] $ {cmd}")
           self.topo.command_to(self.client, cmd)

       # routes côté serveur (une table par lien r2s)
       for i, _ in enumerate(self.topo.r2s_links):
           print(f"[SERVER] table={i} ip={self.get_server_ip(i)} subnet={self.get_server_subnet(i)} via {self.get_router_ip_to_server_switch(i)}")
           cmd = self.add_table_route_command(self.get_server_ip(i), i)
           print(f"[Server] $ {cmd}")
           self.topo.command_to(self.server, cmd)

           cmd = self.add_link_scope_route_command(self.get_server_subnet(i), self.get_server_interface(0, i), i)
           print(f"[Server] $ {cmd}")
           self.topo.command_to(self.server, cmd)

           cmd = self.add_table_default_route_command(self.get_router_ip_to_server_switch(i), i)
           print(f"[Server] $ {cmd}")
           self.topo.command_to(self.server, cmd)

       # routes par défaut
       cmd = self.add_global_default_route_command(self.get_router_ip_to_client_switch(0), self.get_client_interface(0, 0))
       print(f"[Client DEFAULT] $ {cmd}")
       self.topo.command_to(self.client, cmd)

       cmd = self.add_simple_default_route_command(self.get_router_ip_to_server_switch(0))
       print(f"[Server DEFAULT] $ {cmd}")
       self.topo.command_to(self.server, cmd)

       # Snapshot des routes résultantes
       print("\n[STATE] routes résultantes")
       print("[Client]\n", self.topo.command_to(self.client, "ip rule; echo; ip route show table main; echo; for i in $(seq 0 4); do ip route show table $i; done"))
       print("[Server]\n", self.topo.command_to(self.server, "ip rule; echo; ip route show table main; echo; for i in $(seq 0 4); do ip route show table $i; done"))


    def configure_interfaces(self):
       logging.info("=== CONFIGURE INTERFACES (MultiInterfaceConfig) ===")
       super(MultiInterfaceConfig, self).configure_interfaces()
       self.client = self.topo.get_client(0)
       self.server = self.topo.get_server(0)
       self.router = self.topo.get_router(0)
       print("[DEBUG] rightSubnet (param) =", repr(self.param.get("rightSubnet")))
       print("[DEBUG] rightSubnet (topo_parameter) =", repr(getattr(self.topo.topo_parameter, "get", lambda *_: None)("rightSubnet")))
       netmask = "255.255.255.0"

       # Affiche les préfixes lus
       print(f"[INFO] leftSubnet={self.param.get('leftSubnet')}  rightSubnet={self.param.get('rightSubnet')}")

       # --- C2R : Client <-> Router ---
       for i, _ in enumerate(self.topo.c2r_links):
           cli_if  = self.get_client_interface(0, i)
           cli_ip  = self.get_client_ip(i)
           rtr_if  = self.get_router_interface_to_client_switch(i)
           rtr_ip  = self.get_router_ip_to_client_switch(i)

           print(f"[C2R#{i}] {cli_if}={cli_ip}/24  <->  {rtr_if}={rtr_ip}/24")

           cmd = self.interface_up_command(cli_if, cli_ip, netmask)
           print(f"[Client] $ {cmd}")
           self.topo.command_to(self.client, cmd)

           client_interface_mac = self.client.intf(cli_if).MAC()
           cmd = f"arp -s {cli_ip} {client_interface_mac}"
           print(f"[Router] $ {cmd}")
           self.topo.command_to(self.router, cmd)

       for i, _ in enumerate(self.topo.c2r_links):
           rtr_if = self.get_router_interface_to_client_switch(i)
           rtr_ip = self.get_router_ip_to_client_switch(i)
           cmd = self.interface_up_command(rtr_if, rtr_ip, netmask)
           print(f"[Router] $ {cmd}")
           self.topo.command_to(self.router, cmd)

           router_interface_mac = self.router.intf(rtr_if).MAC()
           cmd = f"arp -s {rtr_ip} {router_interface_mac}"
           print(f"[Client] $ {cmd}")
           self.topo.command_to(self.client, cmd)

       # --- R2S : Router <-> Server ---
       if len(self.topo.r2s_links) == 0:
           s_if = self.get_server_interface(0, 0)
           s_ip = self.get_server_ip(0)
           r_if = self.get_router_interface_to_server_switch(0)
           r_ip = self.get_router_ip_to_server_switch(0)

           print(f"[R2S(auto)] {r_if}={r_ip}/24  <->  {s_if}={s_ip}/24")
           self.topo.command_to(self.router, f"ip -4 addr flush dev {r_if}")
           self.topo.command_to(self.server, f"ip -4 addr flush dev {s_if}")
           cmd = self.interface_up_command(r_if, r_ip, netmask)
           print(f"[Router] $ {cmd}")
           self.topo.command_to(self.router, cmd)

           router_interface_mac = self.router.intf(r_if).MAC()
           cmd = f"arp -s {r_ip} {router_interface_mac}"
           print(f"[Server] $ {cmd}")
           self.topo.command_to(self.server, cmd)

           cmd = self.interface_up_command(s_if, s_ip, netmask)
           print(f"[Server] $ {cmd}")
           self.topo.command_to(self.server, cmd)

           server_interface_mac = self.server.intf(s_if).MAC()
           cmd = f"arp -s {s_ip} {server_interface_mac}"
           print(f"[Router] $ {cmd}")
           self.topo.command_to(self.router, cmd)

       else:
          for i, _ in enumerate(self.topo.r2s_links):
               s_if = self.get_server_interface(0, i)
               s_ip = self.get_server_ip(i)
               r_if = self.get_router_interface_to_server_switch(i)
               r_ip = self.get_router_ip_to_server_switch(i)

               print(f"[R2S#{i}] {r_if}={r_ip}/24  <->  {s_if}={s_ip}/24")
               
               print(f"[Router] $ ip -4 addr flush dev {r_if}")
               self.topo.command_to(self.router, f"ip -4 addr flush dev {r_if}")
               print(f"[Server] $ ip -4 addr flush dev {s_if}")
               self.topo.command_to(self.server, f"ip -4 addr flush dev {s_if}")
               cmd = self.interface_up_command(r_if, r_ip, netmask)
               print(f"[Router] $ {cmd}")
               self.topo.command_to(self.router, cmd)

               router_interface_mac = self.router.intf(r_if).MAC()
               cmd = f"arp -s {r_ip} {router_interface_mac}"
               print(f"[Server] $ {cmd}")
               self.topo.command_to(self.server, cmd)

               cmd = self.interface_up_command(s_if, s_ip, netmask)
               print(f"[Server] $ {cmd}")
               self.topo.command_to(self.server, cmd)

               server_interface_mac = self.server.intf(s_if).MAC()
               cmd = f"arp -s {s_ip} {server_interface_mac}"
               print(f"[Router] $ {cmd}")
               self.topo.command_to(self.router, cmd)

       # Snapshot rapide des IPs réellement posées
       print("\n[STATE] ip -br -4 addr")
       print("[Client]\n", self.topo.command_to(self.client, "ip -br -4 addr"))
       print("[Router]\n", self.topo.command_to(self.router, "ip -br -4 addr"))
       print("[Server]\n", self.topo.command_to(self.server, "ip -br -4 addr"))


    def get_client_ip(self, interface_index):
        # ex: leftSubnet: "10.0." -> "10.0.<idx>.1"
        return f"{self.param.get('leftSubnet')}{interface_index}.1"

    def get_client_subnet(self, interface_index):
        # ex: "10.0.<idx>.0/24"
        return f"{self.param.get('leftSubnet')}{interface_index}.0/24"

    def get_router_ip_to_client_switch(self, switch_index):
        # ex: "10.0.<idx>.2"
        return f"{self.param.get('leftSubnet')}{switch_index}.2"

    def get_router_ip_to_server_switch(self, switch_index):
        # ex: rightSubnet: "10.1." -> "10.1.<idx>.2"
        return f"{self.param.get('rightSubnet')}{switch_index}.2"

    def get_server_ip(self, interface_index=0):
        # ex: "10.1.<idx>.1"  (=> Server_0 = 10.1.0.1 si idx=0)
        return f"{self.param.get('rightSubnet')}{interface_index}.1"

    def get_server_subnet(self, interface_index):
        # ex: "10.1.<idx>.0/24"
        return f"{self.param.get('rightSubnet')}{interface_index}.0/24"

    def client_interface_count(self):
        return max(len(self.topo.c2r_links), 1)

    def server_interface_count(self):
        return max(len(self.topo.r2s_links), 1)

    def get_router_interface_to_server_switch(self, switch_index):
        return self.get_router_interface_to_client_switch(len(self.topo.c2r_links) + switch_index)

    def get_client_interface(self, client_index, interface_index):
        return "{}-eth{}".format(self.topo.get_client_name(client_index), interface_index)

    def get_router_interface_to_client_switch(self, interface_index):
        return "{}-eth{}".format(self.topo.get_router_name(0), interface_index)

    def get_server_interface(self, server_index, interface_index):
        return "{}-eth{}".format(self.topo.get_server_name(server_index), interface_index)
