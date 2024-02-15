#!/usr/bin/env python3
# ------------------------------------------------------
#
#	manageGandiZone.py - An imeplementation for the Gandi
#   DNS registrar/host (Excluding other Gandi-services).
#
#   Focused on registrar operations, with some DNS zone
#   management functions also included
#
#	            Written: James Varoutsos
#	    Date: 10-Jan-2023        Version: 1.0
#
#	    1.0 - Migration + major refactor
#
#   - action: list | query | register
#       The action to be executed
#   - zone: The zone to peform the action on
#   - key: Explicit API-key reference
#       (Tool will auto-search for gandi.key in ~/)
#
#	Lint score: 7.92/10
#
# ------------------------------------------------------

# Standard libraries
import os
import sys
import json
import argparse
import requests

from datetime import datetime, timedelta, timezone

class manageGandiZone:

    # Display theme colors
    rst = "\033[0m"           # Color reset
    cdn = "\033[38;5;012m"    # Domain
    end = "\033[38;5;010m"    # enabled
    dsd = "\033[38;5;009m"    # disabled
    cdt = "\033[38;5;045m"    # Created date
    cxp = "\033[38;5;196m"    # Expiried date
    ctg = "\033[38;5;202m"    # Domain tags
    expg = "\033[38;5;118m"   # Domain expiry good
    expd = {
        14: "\033[38;5;202m",
        21: "\033[38;5;208m",
        42: "\033[38;5;214m",
        60: "\033[38;5;220m",
        90: "\033[38;5;228m",
    }                         # Expiry date range

    # Presets
    debug_mode = False
    output_type = "text"
    date_format="%Y-%m-%dT%H:%M:%S%z"
    gandiEndpoint = "https://api.gandi.net/v5"
    api_headers = {"Content-Type": "application/json"}
    api_method = "GET"
    api_params = {}
    api_body = {}

    def __init__(self, api_key, output, debug=False):

        if debug:
            self.debug_mode = True

        # Find & set API key
        if not api_key:
            api_key=self.find_api_token()
            if not api_key:
                print("No API key set or found - Exiting")
                sys.exit(2)
        self.print_debug("API key set as" + api_key)
        self.api_headers["Authorization"]="Apikey " + api_key

        if output:
            self.output_type = output

    # Actionable functions
    def list_zone(self, dns_zone):
        self.gandiEndpoint+="/domain/domains"
        if not dns_zone:
            self.print_debug("No zone selected - Displaying all owned zones")
        else:
            self.print_debug("Filtering results based on pattern " + dns_zone)
            self.api_params["fqdn"]=dns_zone
        gandi_reply = requests.request(self.api_method, self.gandiEndpoint, \
            headers=self.api_headers, params=self.api_params)
        if self.output_type == "text":
            # Status information
            print(gandi_reply.json())
            for zone in gandi_reply.json():
                # Display zone status icon
                self.show_status_icon(zone['status'])
                # Basic information
                sys.stdout.write(self.cdn + zone['fqdn'] + self.rst + " :: " + zone['owner'])
                sys.stdout.write(" - Created: " + self.cdt + zone['dates']['created_at'] + self.rst)
                # Expiry
                sys.stdout.write(" - Expires: ")
                self.format_datetime_expiry(zone['dates']['registry_ends_at'])
                # Tags
                if zone['tags']:
                    sys.stdout.write(" :: [" + self.ctg)
                    for tag in zone['tags']:
                        sys.stdout.write(tag + " ")
                    sys.stdout.write("\b" + self.rst +"]")
                sys.stdout.write("\n")
        elif self.output_type == "json":
            print(json.dumps(gandi_reply.json(), indent=4))
        return 1

    def query_zone_availability(self, dns_zone):
        self.gandiEndpoint+="/domain/check"
        if not dns_zone:
            print("Error: No zone provided")
            return 0
        self.print_debug("Checking availability of zone " + dns_zone)
        self.api_params["name"]=dns_zone
        gandi_reply = requests.request(self.api_method, self.gandiEndpoint, \
                headers=self.api_headers, params=self.api_params)

        if self.output_type == "text":
            print(gandi_reply.json())
            for zone in gandi_reply.json()[0]:
                print(zone['grid'])
                # if zone["products"]["status"] == "available":
                #     sys.stdout.write("✅ " + self.end + "Available" + self.rst + " :: " + dns_zone)
                #     sys.stdout.write(" :: Price: " + self.cdn + "$" + zone["prices"]["price_after_taxes"] + "\n")
                
        elif self.output_type == "json":
            print(json.dumps(gandi_reply.json(), indent=4))
        return 1

    def query_zone_information(self, dns_zone):
        if not dns_zone:
            print("Error: No zone provided")
            return 0
        self.gandiEndpoint+="/domain/domains/" + dns_zone
        self.print_debug("Querying information about zone " + dns_zone)
        self.api_params["name"]=dns_zone
        gandi_reply = requests.request(self.api_method, self.gandiEndpoint, \
                headers=self.api_headers, params=self.api_params)

        if self.output_type == "text":
            zone = gandi_reply.json()
            # Display zone status icon
            self.show_status_icon(zone['status'])
            # Basic information
            sys.stdout.write(f"\033[38;5;012m%s\033[0m :: Owner: %s" \
                % (zone['fqdn'],zone['sharing_space']['name']))
            # Tags
            if zone['tags']:
                sys.stdout.write(" :: Tags: [\033[38;5;202m")
                for tag in zone['tags']:
                    sys.stdout.write(tag + " ")
                sys.stdout.write("\b\033[0m]")
            # Nameservers
            if zone['nameservers']:
                sys.stdout.write(" :: Nameservers: [")
                for ns in zone['nameservers']:
                    sys.stdout.write("\033[38;5;202m" + ns + "\033[0m, ")
                sys.stdout.write("\b\b]")
            sys.stdout.write("\n")
            # Dates
            sys.stdout.write("Dates ::\n")
            sys.stdout.write(f"\tCreated: {zone['dates']['created_at']}\n")
            sys.stdout.write(f"\tUpdated: {zone['dates']['updated_at']}\n")
            # Expires
            sys.stdout.write("\tExpires: ")
            self.format_datetime_expiry(zone['dates']['registry_ends_at'])
            sys.stdout.write("\n")

            # DNSSEC
            if "dnssec" in zone['services']:
                sys.stdout.write("DNSSEC :: 🔒 \033[38;5;010mEnabled\033[0m\n")
            else:
                sys.stdout.write("DNSSEC :: 🔓 \033[38;5;009mDisabled\033[0m\n")

            # Autorenew
            if zone['autorenew']['enabled']:
                sys.stdout.write("Auto-Renew :: ✅ \033[38;5;010mYes\033[0m\n")
            else:
                sys.stdout.write("Auto-Renew :: ⛔ \033[38;5;009mNo\033[0m\n")
        elif self.output_type == "json":
            print(json.dumps(gandi_reply.json(), indent=4))
        return 1

    def register_zone(self, dns_zone):
        self.gandiEndpoint+="/domain/domains"
        self.api_method="POST"
        # Registration defaults
        self.api_headers["Dry-Run"]="1"
        self.api_body["fqdn"]=dns_zone
        self.api_body["duration"]=1
        if not dns_zone:
            print("Error: No zone provided")
            return 0
        owner_conf = self.load_ownership_template()
        if not owner_conf:
            print("No configuration data loaded")
            exit()
        req_details=[ "type", "country", "given", "family", "email", "streetaddr" ]
        for field in req_details:
            if not owner_conf[field]:
                print("Missing required ownership attribute ("+field+") :: Exiting")
                return ""
        self.api_body["owner"]=owner_conf
        gandi_reply = requests.request(self.api_method, self.gandiEndpoint, \
                headers=self.api_headers, data=json.dumps(self.api_body))
        self.validate_response(gandi_reply)
        print(json.dumps(gandi_reply.json(), indent=4))

        return 1

    # Utility functions
    def find_api_token(self):
        gDirs=["~/.secrets/","~/.api/","~/"]        # Common directories
        gfnames=["gandi","gandi.key","gandi.api"]   # Gandi filenames
        found_path=""

        for filename in gfnames:
            for directory in gDirs:
                if os.path.exists(os.path.expanduser(directory+filename)):
                    found_path=os.path.expanduser(directory+filename)

        if not found_path:
            return ""
        else:
            self.print_debug("Found Gandi API key in path: " + found_path)
            with open(found_path,"r") as api_file:
                return api_file.read()[:-1]     # Need to remove the final file newline

    def load_ownership_template(self):
        hmDir=os.path.expanduser("~")
        if os.path.exists(hmDir+"gandi_owner.conf"):
            found_path=hmDir+"gandi_owner.conf"
        elif os.path.exists(hmDir+"/.config/gandi_owner.conf"):
            found_path=hmDir+"/.config/gandi_owner.conf"
        else:
            print("No ownership template found :: Creating one")
            self.generate_ownership_template()
            return ""

        if found_path:
            with open(found_path, "r") as owners_json:
                # Remove commented lines
                uncom_json = "".join(line for line in owners_json if not line.startswith('//'))
                owners_json = json.loads(uncom_json)
            return owners_json

    def generate_ownership_template(self):
        gandi_owners_url="https://api.gandi.net/docs/domains/#post-v5-domain-domains"

        req_ownership_fields = {
            "type": "individual",
            "country": "US|UK|AU",
            "zip": "<postcode>",
            "given": "<given name here>",
            "family": "<family name here>",
            "email": "<your email here>",
            "phone": "<your phone number>",
            "streetaddr": "<your address here>",
            "city": "<your city>",
        }

        with open(os.path.expanduser("~")+"/.config/gandi_owner.conf","w") as template_file:
            template_file.write(
                "// Below is the minimum required ownership data for domain registration\n"+
                "// Further information around the required fields: "+gandi_owners_url+"\n"+
                json.dumps(req_ownership_fields, indent=4)+
                "\n"
            )
            print("Ownership template file created under ~/.config/gandi_owner.conf")
        return ""

    def validate_response(self, req_response):
        if req_response.status_code != requests.codes.ok:
            print("Request failed (HTTP Status: "+req_response.status_code+" - "\
                +req_response.reason+")")
            sys.exit(100)
        elif "error" in req_response.json()['status']:
            print("Response returned error: ")
            for error in req_response.json()['errors']:
                print("Missing attribute ["+error['name']+"]")
                if error['description']:
                    print(error['description'])
            sys.exit(int(req_response.json()['status']))
        else:
            return 1

    def show_status_icon(self, status):
        if "clientTransferProhibited" in status:
            sys.stdout.write("🔑 ")
        elif "clientHold" in status:
            sys.stdout.write("❌ ")
        elif "pendingTransfer" in status:
            sys.stdout.write("➡️ ")
        elif not status:
            sys.stdout.write("❓ ")
        else:
            sys.stdout.write("🔵 ")

    def format_datetime_expiry(self, exp_datetime):
        # Make formatting consistent + convert possible str to datetime object
        exp_datetime = datetime.strptime(exp_datetime, self.date_format)
        currentime = datetime.now(timezone.utc)

        # Set expiry colors
        ttyClr = self.expg
        for expTest in self.expd:
            if (exp_datetime - currentime) < timedelta(days = expTest):
                ttyClr = self.expd[expTest]

        sys.stdout.write("%s%s\033[0m" % (ttyClr, exp_datetime))

    def print_debug(self, msg):
        if msg and self.debug_mode:
            sys.stdout.write(msg + "\n")


# Below is CLI only - Check namespace to confirm whether running standalone
if __name__ == "__main__":
    # CLI ONLY :: Parameter handling
    MGZ_ARGV = argparse.ArgumentParser( \
        description="A Python CLI & callable object for interfacing with the Gandi DNS API")

    MGZ_ARGV.add_argument('action', \
        help="Available actions: [list | info | query | register]")
    MGZ_ARGV.add_argument('zone', nargs='?', \
        help="The DNS zone perform the action on")
    MGZ_ARGV.add_argument('--json', '-j', dest="ofmt", action="store_const", const="json", \
        help='Return results in JSON')
    MGZ_ARGV.add_argument('--debug', '-d', action="store_const", const=True, \
        help='Show extra debugging output')
    MGZ_ARGV.add_argument('--key', '-k', \
        help='An explicit API key to use')

    MGZ_ARGV = MGZ_ARGV.parse_args()
    MGZ_OBJ = manageGandiZone(MGZ_ARGV.key, MGZ_ARGV.ofmt, MGZ_ARGV.debug)

    # CLI ONLY :: define CLI actions
    valid_actions = {
        "list": MGZ_OBJ.list_zone,              # 'zone' will be passed empty through here
        "info": MGZ_OBJ.query_zone_information,
        "query": MGZ_OBJ.query_zone_availability,
        "register": MGZ_OBJ.register_zone
    }

    # Check & execute a CLI action
    try:
        if not valid_actions[MGZ_ARGV.action](MGZ_ARGV.zone):
            print("Operation failed")
    except KeyError:
        sys.stderr.write("Unknown action '" + MGZ_ARGV.action + "'\n")
        sys.exit(1)