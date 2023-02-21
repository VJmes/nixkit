#!/usr/bin/env python3
# ------------------------------------------------------
#
#	enrollWgClient.py - Handles the enrollment of Wireguard
#   clients by adding the peer information into the server
#   .conf and
#
#	            Written: James Varoutsos
#	    Date: 25-Sep-2021        Version: 1.0
#
#	    1.0 - Migration + minor refactor
#
#   - client_id: Unique identifier for client
#   - wg_dir: Wireguard working directory
#   - wg_server_conf: server .conf file to update
#   - wg_hostport: The hostname:port for clients to
#       connect to
#
#	Lint score: 8.77/10
#
# ------------------------------------------------------
#

# Standard libraries
import io
import os
import sys
import configparser
import subprocess
import ipaddress
import argparse

# For multi_dict
from collections import OrderedDict

# For QR code output
try:
    import qrcode
    qr_module = True
except ModuleNotFoundError:
    sys.stderr.write("Warning: QRcode module not found on system (Run: pip3 install qrcode)\n")
    qr_module = False

# Multi dictionary :: The ability to set multie same-key items uniquely!
# To fix --> Insert a check to see whether the key already exist, and if not, leave unnamed
class multi_dict(OrderedDict):
    uniq = 0

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            self.uniq+=1
            key += str(self.uniq)
        OrderedDict.__setitem__(self, key, value)

class enrollWireguardClient:
    # Defaults
    wg_ifname="wg0"
    wg_path="/etc/wireguard/"+wg_ifname+".conf"
    wg_cname=""

    # Client configuration dictionaries
    wg_client_peer_conf = {}
    wg_client_intf_conf = {}

    # Server peer configuration dictionary
    wg_server_peer_conf = {}

    # Initializer (Duh)
    @classmethod
    def __init__(self, client_name, wg_server=False, wg_conf_path=False, wg_client_port=51820):

        # Check client name has been provided
        if not client_name:
            sys.stderr.write("No client identifier set")
            sys.exit(1)
        else:
            self.wg_cname = client_name
            print(self.wg_cname)

        # Assume kernel-land and check for root
        if os.geteuid():
            sys.stderr.write("Enrollment needs to be run as root")
            sys.exit(2)

        # Check whether custom .conf file set, is in fact a file and set it
        if not wg_conf_path:
            sys.stdout.write("Using default /etc/wireguard/wg0.conf\n")
        else:
            self.wg_path = wg_conf_path

        if not os.path.isfile(self.wg_path):
            sys.stderr.write("Wireguard .conf '" + self.wg_path + "' is not readable\n")
            sys.exit(1)

        if not wg_server:
            sys.stdout.write("No server address provided - Attempting to query manually\n")
            wg_server=self.discover_wan_address()
            if not wg_server:
                sys.stderr.write("Server address unable to be queried\n")
                sys.exit(5)

        # Open wireguard server configuration - Load into configParse
        try:
            with open(self.wg_path,"r") as wg_conf_file:
                wg_conf = configparser.ConfigParser(defaults=None, dict_type=multi_dict, strict=False)
                wg_conf.read_file(wg_conf_file)
        except EnvironmentError:
            sys.stderr.write("Unable to open Wireguard server conf (" + self.wg_path + ")\n")
            sys.exit(5)

        print(wg_conf.sections())

        # If no port is provided - grab it from the conf
        if not wg_client_port:
            # Since multi_dict relabels EVERY section, [Interface] became [Interface1]
            wg_serv_port = wg_conf.get("Interface1","ListenPort")
            sys.stdout.write("No port specificed :: using ListenPort from WG server conf.\n")
        elif 1024 < wg_client_port < 65536:
            wg_serv_port=wg_client_port
        else:
            print(type(wg_client_port))
            sys.stderr.write("Invalid port provided '" + str(wg_client_port) + "'\n")
            sys.exit(4)

        # Generate the client's peer configuration
        self.wg_client_peer_conf["PublicKey"] = self.query_interface_pubkey()
        self.wg_client_peer_conf["Endpoint"] = wg_server + ":" + str(wg_serv_port)
        self.wg_client_peer_conf["AllowedIPs"] = "0.0.0.0/0"
        # TODO :: Add option for PersistentKeepalive

        # Allocate the new peer's IP address & port from the server configuration
        client_addr = self.generate_client_addr(wg_conf) + "/32"
        self.wg_client_intf_conf["Address"] = client_addr
        self.wg_server_peer_conf["AllowedIPs"] = client_addr

        # TODO :: Add option to specify the DNS on client interface

        # Generate a new keypair for the peer
        client_privkey = self.generate_client_privkey()
        self.wg_client_intf_conf["PrivateKey"] = client_privkey
        self.wg_server_peer_conf["PublicKey"] = self.generate_client_pubkey(client_privkey)

        # Don't know why - But I like the ListenPort being on the bottom
        self.wg_client_intf_conf["ListenPort"] = wg_serv_port

    # Generate a public key for the peer derived from the interface's private key
    @classmethod
    def discover_wan_address(cls):
        checkUrl="https://api.my-ip.io/ip"
        wan_addr = subprocess.run(["curl", "-s", checkUrl], capture_output=True, text=True)
        if ipaddress.ip_address(wan_addr.stdout):
            return wan_addr.stdout
        return 0

    @classmethod
    def query_interface_pubkey(cls):
        pubkey = subprocess.run(["wg","show",cls.wg_ifname,"public-key"], capture_output=True, text=True)
        if pubkey:
            return pubkey.stdout
        return 0

    # Pass the handle brah
    # (This is a mess) :: Checks all the AllowedIP peers to find the largest one,
    #   increments it by one and returns it
    @classmethod
    def generate_client_addr(cls, conf_handle):
        gw_addr = ipaddress.ip_network(conf_handle.get("Interface1","Address"),strict=False)
        largest_host = gw_addr.network_address
        for client in conf_handle.sections():
            # client_dict = client.options(client)
            if conf_handle.has_option(client, "AllowedIPs"):
                peer_addr = ipaddress.ip_network(conf_handle.get(client, "AllowedIPs")).network_address
                if (peer_addr in gw_addr) and (peer_addr > largest_host):
                    largest_host = peer_addr
        return str(largest_host+1)

    @classmethod
    def generate_client_privkey(cls):
        privkey = subprocess.run(["wg", "genkey"], check=True, capture_output=True, text=True)
        return privkey.stdout[:-1]  # Trim trailing newline

    @classmethod
    def generate_client_pubkey(cls, privkey):
        pubkey = subprocess.run(["wg", "pubkey"], input=privkey, check=True, capture_output=True, text=True)
        return pubkey.stdout[:-1]   # Trim trailing newline

    @classmethod
    def import_peer_conf(cls):
        print("Loading server [Peer] configuration into " + cls.wg_path)
        print(cls.wg_cname)
        server_peer_conf = "# " + cls.wg_cname + " :: Auto-generated peer\n[Peer]\n"
        for inf_key in cls.wg_server_peer_conf:
            server_peer_conf += inf_key + " = " + str(cls.wg_server_peer_conf[inf_key]) + "\n"

        server_peer_conf += "\n"    # Can have a final extra newline as a treat
        try:
            with open(cls.wg_path,"a") as wg_server_file:
                wg_server_file.write(server_peer_conf)
        except EnvironmentError:
            sys.stderr.write("Unable to open server conf file (" + cls.wg_path + ")\n")
            sys.exit(8)

    @classmethod
    def export_client_stdout(cls):
        print("Generating client configuration - Displaying as stdout")
        sys.stdout.write("# Auto-generated configuration\n[Interface]\n")
        cls.write_toml(cls.wg_client_intf_conf)

        sys.stdout.write("\n[Peer]\n")
        cls.write_toml(cls.wg_client_peer_conf)

    @classmethod
    def export_client_file(cls, file_path):
        client_conf_full = "# Auto-generated configuration\n[Interface]\n"
        print("Generating client configuration file - Path: " + file_path)

        client_conf_full = "# Auto-generated configuration\n[Interface]\n"
        for inf_key in cls.wg_client_intf_conf:
            client_conf_full += inf_key + " = " + str(cls.wg_client_intf_conf[inf_key]) + "\n"

        client_conf_full += "\n[Peer]\n"
        for inf_key in cls.wg_client_peer_conf:
            client_conf_full += inf_key + " = " + str(cls.wg_client_peer_conf[inf_key]) + "\n"

        try:
            with open(file_path,"w") as wg_client_file:
                wg_client_file.write(client_conf_full)
        except EnvironmentError:
            sys.stderr.write("Unable to open requested client file path (" + file_path + ")\n")
            sys.exit(6)

    @classmethod
    def export_client_qr_stdout(cls):
        print("Generating client configuration as scannable QR code")
        client_conf_full = "# Auto-generated configuration\n[Interface]\n"
        for inf_key in cls.wg_client_intf_conf:
            client_conf_full += inf_key + " = " + str(cls.wg_client_intf_conf[inf_key]) + "\n"

        client_conf_full += "\n[Peer]\n"
        for inf_key in cls.wg_client_peer_conf:
            client_conf_full += inf_key + " = " + str(cls.wg_client_peer_conf[inf_key]) + "\n"

        client_wg_qrcode = qrcode.QRCode()
        client_wg_qrcode.add_data(client_conf_full)
        wg_client_conf = io.StringIO()
        client_wg_qrcode.print_ascii(out=wg_client_conf)

        wg_client_conf.seek(0)
        sys.stdout.write(wg_client_conf.read())

    # TODO :: Make this use file handlers if passed
    @classmethod
    def write_toml(cls, dictionary):
        for option_key in dictionary:
            sys.stdout.write(str(option_key) + " = " + str(dictionary[option_key]) + "\n")

# Below is CLI only - Check namespace to confirm whether running standalone
if __name__ == "__main__":
    # CLI ONLY :: Parameter handling
    WGE_ARGC = argparse.ArgumentParser(description="Enroll a new peer into Wireguard")
    WGE_ARGC.add_argument('name', help='Uniquily identifable client name')
    WGE_ARGC.add_argument('--server', help='Server endpoint hostname/address')
    WGE_ARGC.add_argument('--conf', help="Wireguard conf path")
    WGE_ARGC.add_argument('--port', default=False, required=False, help='Set client port')
    WGE_ARGC.add_argument('--file', help='Export client configuration to file')
    WGE_ARGC.add_argument('--qr', help='Display as QR code', action="store_const", const=True)

    WGE_ARGC = WGE_ARGC.parse_args()
    WGE_OBJ = enrollWireguardClient(WGE_ARGC.name, WGE_ARGC.server, WGE_ARGC.conf, WGE_ARGC.port)

    # CLI ONLY :: Client configuration output handling
    if not WGE_ARGC.file:
        if not WGE_ARGC.qr:
            WGE_OBJ.export_client_stdout()          # [Default] Export to STDOUT
        else:
            if not qr_module:
                sys.stderr.write("Error: QRcode not loaded - Cannot generate output\n")
                sys.exit(10)
            else:
                WGE_OBJ.export_client_qr_stdout()   # Export as QR code (On CLI)
    else:
        WGE_OBJ.export_client_file(WGE_ARGC.file)   # Export to a file
    WGE_OBJ.import_peer_conf()  # TODO :: Ensure only runs if above is successful
