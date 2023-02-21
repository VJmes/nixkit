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

    # Theme colors
    cdn = ""    # Domain
    cdt = ""    # Date
    c90 = ""    # 90-day expiry date
    c60 = ""    # 90-day expiry date
    c30 = ""    # 90-day expiry date
    cxp = ""    # Expiried date
    ctg = ""    # Domain tags
    cse = ""    # DNSSEC enabled
    csd = ""    # DNSSEC disabled

    # Presets
    output_type = "text"
    date_format = ""
    gandiEndpoint = "https://api.gandi.net/v5"
    api_headers = {"Content-Type": "application/json"}
    api_method = "GET"
    api_params = {}
    api_body = {}

    def __init__(self, action, dns_zone, api_key, output):

        valid_actions = {
            "list": self.list_zone,
            "info": self.query_zone_information,
            "query": self.query_zone_availability,
            "register": self.register_zone
        }

        # Find & set API key
        if not api_key:
            api_key=self.find_api_token()
            if not api_key:
                print("No API key set or found - Exiting")
                exit()
        print("API key set as" + api_key)
        self.api_headers["Authorization"]="Apikey " + api_key

        # TODO Fix this!
        if output:
            self.output_type = output

        try:
            if not valid_actions[action](dns_zone):
                print("Operation failed")
        except KeyError:
            sys.stderr.write("Unknown action '" + action + "'\n")
            sys.exit(1)

    # Actionable functions
    def list_zone(self, dns_zone):
        self.gandiEndpoint+="/domain/domains"
        if not dns_zone:
            print("No zone selected - Displaying all owned zones")
        else:
            print("Filtering results based on pattern " + dns_zone)
            self.api_params["fqdn"]=dns_zone
        gandi_reply = requests.request(self.api_method, self.gandiEndpoint, \
            headers=self.api_headers, params=self.api_params)
        if self.output_type == "text":
            # Status information
            for zone in gandi_reply.json():
                if "clientTransferProhibited" in zone['status']:
                   sys.stdout.write(f"🔒 ")
                elif "clientHold" in zone['status']:
                    sys.stdout.write(f"❌ ")
                elif "pendingTransfer" in zone['status']:
                    sys.stdout.write(f"➡️ ")
                elif not zone['status']:
                    sys.stdout.write(f"❓ ")
                else:
                    sys.stdout.write(f"🔵 ")
                # Basic information
                sys.stdout.write(f"\033[38;5;012m%s\033[0m :: %s - Created: \033[38;5;045m%s\033[0m" \
                    % (zone['fqdn'],zone['owner'],zone['dates']['created_at']))
                # Expiry
                dtFormat="%Y-%m-%dT%H:%M:%S%z"
                sys.stdout.write(" - Expires: ")
                expireDatetime=datetime.strptime(zone['dates']['registry_ends_at'],dtFormat)
                if (expireDatetime - datetime.now(timezone.utc)) < timedelta(days = 90):
                    sys.stdout.write("\033[38;5;228m%s\033[0m" \
                        % zone['dates']['registry_ends_at'])
                elif (expireDatetime - datetime.now(timezone.utc)) < timedelta(days = 60):
                    sys.stdout.write("\033[38;5;215m%s\033[0m" \
                        % zone['dates']['registry_ends_at'])
                elif (expireDatetime - datetime.now(timezone.utc)) < timedelta(days = 30):
                    sys.stdout.write("\033[38;5;196m%s\033[0m" \
                        % zone['dates']['registry_ends_at'])
                else:
                    sys.stdout.write("\033[38;5;118m%s\033[0m" \
                        % zone['dates']['registry_ends_at'])
                # Tags
                if zone['tags']:
                    sys.stdout.write(f" :: [\033[38;5;202m")
                    for tag in zone['tags']:
                        sys.stdout.write(f"%s " % (tag))
                    sys.stdout.write(f"\b\033[0m]")
                sys.stdout.write("\n")
        elif self.output_type == "json":
            print(json.dumps(gandi_reply.json(), indent=4))
        return 1

    def query_zone_availability(self, dns_zone):
        self.gandiEndpoint+="/domain/check"
        if not dns_zone:
            print("Error: No zone provided")
            return 0
        print("Querying details for zone " + dns_zone)
        self.api_params["name"]=dns_zone
        gandi_reply = requests.request(self.api_method, self.gandiEndpoint, \
                headers=self.api_headers, params=self.api_params)

        if self.output_type == "text":
            for zone in gandi_reply.json():
                print(zone)
        elif self.output_type == "json":
            print(json.dumps(gandi_reply.json(), indent=4))
        return 1

    def query_zone_information(self, dns_zone):
        print(dns_zone)
        if not dns_zone:
            print("Error: No zone provided")
            return 0
        self.gandiEndpoint+="/domain/domains/" + dns_zone
        print("Querying information about zone " + dns_zone)
        self.api_params["name"]=dns_zone
        gandi_reply = requests.request(self.api_method, self.gandiEndpoint, \
                headers=self.api_headers, params=self.api_params)

        if self.output_type == "text":
            zone = gandi_reply.json()
            # Zone status
            if "clientTransferProhibited" in zone['status']:
                sys.stdout.write(f"🔒 ")
            elif "clientHold" in zone['status']:
                sys.stdout.write(f"❌ ")
            elif "pendingTransfer" in zone['status']:
                sys.stdout.write(f"➡️ ")
            elif not zone['status']:
                sys.stdout.write(f"❓ ")
            else:
                sys.stdout.write(f"🔵 ")
            # Basic information
            sys.stdout.write(f"\033[38;5;012m%s\033[0m :: Owner: %s" \
                % (zone['fqdn'],zone['sharing_space']['name']))
            # Tags
            if zone['tags']:
                sys.stdout.write(f" :: Tags: [\033[38;5;202m")
                for tag in zone['tags']:
                    sys.stdout.write(f"%s " % (tag))
                sys.stdout.write(f"\b\033[0m]")
            # Nameservers
            if zone['nameservers']:
                sys.stdout.write(f" :: Nameservers: [")
                for ns in zone['nameservers']:
                    sys.stdout.write(f"\033[38;5;202m%s\033[0m, " % (ns))
                sys.stdout.write(f"\b\b]")
            sys.stdout.write("\n")
            # Dates
            sys.stdout.write("Dates ::\n")
            sys.stdout.write(f"\tCreated: %s\n" % zone['dates']['created_at'])
            sys.stdout.write(f"\tUpdated: %s\n" % zone['dates']['updated_at'])
            # Expires

            dtFormat="%Y-%m-%dT%H:%M:%S%z"
            sys.stdout.write("\tExpires: ")
            expireDatetime=datetime.strptime(zone['dates']['registry_ends_at'],dtFormat)
            if (expireDatetime - datetime.now(timezone.utc)) < timedelta(days = 90):
                sys.stdout.write("\033[38;5;228m%s\033[0m" \
                    % zone['dates']['registry_ends_at'])
            elif (expireDatetime - datetime.now(timezone.utc)) < timedelta(days = 60):
                sys.stdout.write("\033[38;5;215m%s\033[0m" \
                    % zone['dates']['registry_ends_at'])
            elif (expireDatetime - datetime.now(timezone.utc)) < timedelta(days = 30):
                sys.stdout.write("\033[38;5;196m%s\033[0m" \
                    % zone['dates']['registry_ends_at'])
            else:
                sys.stdout.write("\033[38;5;118m%s\033[0m" \
                    % zone['dates']['registry_ends_at'])
            # sys.stdout.write(" (%s days)\n" % expireDatetime.day)
            sys.stdout.write("\n")

            # DNSSEC
            if "dnssec" in zone['services']:
                sys.stdout.write("DNSSEC :: 🔒 \033[38;5;010mEnabled\033[0m\n")
            else:
                sys.stdout.write("DNSSEC :: 🔓 \033[38;5;009Disabled\033[0m\n")
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
            print("Found Gandi API key in path: " + found_path)
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
            exit()
        elif "error" in req_response.json()['status']:
            print("Response returned error: ")
            for error in req_response.json()['errors']:
                print("Missing attribute ["+error['name']+"]")
                if error['description']:
                    print(error['description'])
            exit()
        else:
            return 1


# Below is CLI only - Check namespace to confirm whether running standalone
if __name__ == "__main__":
    # CLI ONLY :: Parameter handling
    MGZ_ARGV = argparse.ArgumentParser( \
        description="A Python CLI & callable object for interfacing with the Gandi DNS API")

    MGZ_ARGV.add_argument('action', help="Available actions: [list | info | query | register]")
    MGZ_ARGV.add_argument('zone', help="The DNS zone perform the action on", nargs='?')
    MGZ_ARGV.add_argument('--json', '-j', help='Return results in JSON', dest="ofmt", \
        action="store_const", const="json")
    MGZ_ARGV.add_argument('--key', '-k', help='An explicit API key to use')

    MGZ_ARGV = MGZ_ARGV.parse_args()
    MGZ_OBJ = manageGandiZone(MGZ_ARGV.action, MGZ_ARGV.zone, MGZ_ARGV.key, MGZ_ARGV.ofmt)
