#!/usr/bin/env python3
# ------------------------------------------------------
#
#	manageDesecZone.py - An API-endpoint for the DeSEC
#   (desec.io) DNS hosting service that allows a
#   number of common management tasks to be executed
#
#	            Written: James Varoutsos
#	    Date: 03-Aug-2022        Version: 1.0
#
#	    1.0 - Migration + major refactor
#
#   - action: list | add-zone | del-zone | add-record | del-record
#           The action to be executed
#   - zone: The zone to perform the action on
#   - key: API key used to authenticate the action
#   - template: A JSON file containing the record(s) to be
#           added or removed from the zone
#
#	Lint score: 7.55/10
#
# ------------------------------------------------------

# Standard libraries
import os
import sys
import json
import argparse

# In case for some reason requests isn't installed
try:
    import requests
except ModuleNotFoundError:
    sys.stderr.write("Error: Requests module not available (Run: pip3 install requests)\n")
    exit(100)

class manageDesecZone:

    # Theme colors
    cdn = ""    # Domain
    ccd = ""    # Created date
    cud = ""    # Updated date
    cty = ""    # Record type

    # Presets
    output_type = "text"
    date_format = ""
    desec_endpoint = "https://desec.io/api/v1"
    api_headers = {"Content-Type": "application/json"}
    template_token = "<<DOMAIN>>"
    api_params = {}
    api_body = {}

    # Actions


    def __init__(self, action, dns_zone, api_key=False, json_template=False, output=False):

        valid_actions = {
            "add-zone": self.add_zone,
            "list-zone": self.list_zone,
            "delete-zone": self.delete_zone,
            "add-record": self.add_record,
            "list-record": self.list_record,
            "delete-record": self.delete_record
        }

        if output:
            self.output_type = output
        print("Outputting results as " + self.output_type)

        # Find & set API key
        if not api_key:
            api_key=self.find_api_token()
            if not api_key:
                print("No API key set or found - Exiting")
                exit()
        print("API key set as" + api_key)
        self.api_headers["Authorization"]="token " + api_key

        try:
            if "list-record" == action:
                if not valid_actions[action](dns_zone):
                    print("Operation failed")
            elif "add-record" == action or "delete-record" == action:
                if not json_template:
                    print("No template file provided")
                if not valid_actions[action](dns_zone, json_template):
                    print("Operation failed")
            elif "list-zone" == action:
                if not valid_actions[action]():
                    print("Operation failed")
            else:
                if not valid_actions[action](dns_zone):
                    print("Operation failed")
        except KeyError:
            sys.stderr.write("Unknown action '" + action + "'\n")
            sys.exit(1)

    #   Zone functions
    def add_zone(self, zone):
        self.desec_endpoint+="/domains/"
        self.api_body['name'] = zone

        print("Adding new zone " + zone)

        req_add_zone = requests.post(self.desec_endpoint, \
        headers=self.api_headers, data=json.dumps(self.api_body))

        if self.validate_response(req_add_zone, 201, "adding zone " + zone):
            return 1

    def list_zone(self):
        self.desec_endpoint+="/domains/"
        print("Listing available zones ")

        req_list_zone = requests.get(self.desec_endpoint, headers=self.api_headers)

        if not self.validate_response(req_list_zone, 200, "listing zones"):
            return 0

        if self.output_type == "text":
            for resp_zone in req_list_zone.json():
                sys.stdout.write(
                    resp_zone["name"] + " :: TTL: " + str(resp_zone["minimum_ttl"]) +
                    " :: Created: " + resp_zone["created"] + " :: Updated: " +
                    resp_zone["touched"] + "\n")
        else:
            print(json.dumps(req_list_zone.json(), indent=4))

        return 1

    def delete_zone(self, zone):
        self.desec_endpoint+="/domains/"+zone
        print("Deleting zone " + zone)

        req_del_zone = requests.delete(self.desec_endpoint, headers=self.api_headers)

        if self.validate_response(req_del_zone, 204, "removed zone " + zone):
            return 1

    #   Resource-record functions
    def add_record(self, zone, template_file):
        self.desec_endpoint+="/domains/"+zone+"/rrsets/"
        records = self.open_template_file(template_file)
        if not records:
            print("No valid record data provided")
            return 0

        for rr in records:
            rr['records'].replace(self.template_token, zone)

        req_add_rrs = requests.post(self.desec_endpoint, headers=self.api_headers, \
            data=json.dumps(records))

        if self.validate_response(req_add_rrs, 201, "added records for " + zone):
            return 1

    # TODO Add filter support
    def list_record(self, zone):
        self.desec_endpoint+="/domains/"+zone+"/rrsets/"

        req_list_rrs = requests.get(self.desec_endpoint, headers=self.api_headers)

        if not self.validate_response(req_list_rrs, 200, "list records of " + zone):
            return 0

        if self.output_type == "text":
            for rr in req_list_rrs.json():
                sys.stdout.write(
                    rr["name"] + " :: Type: " + rr["type"] + " :: TTL: " + str(rr["ttl"]) + \
                        "\nDates:\n\tCreated: " + rr["created"] + "\n\tUpdated: " \
                        + rr["touched"] + "\nValues:\n")
                for record in rr["records"]:
                    sys.stdout.write("\t" + record + "\n")
        else:
            print(json.dumps(req_list_rrs.json(), indent=4))

        return 1

    def delete_record(self, zone, template_file):
        self.desec_endpoint+="/domains/"+zone+"/rrsets/"
        records = self.open_template_file(template_file)
        if not records:
            print("No valid record data provided")
            return 0

        for resource_record in records:
            resource_record["records"]=[]

        req_del_rrs = requests.patch(self.desec_endpoint, headers=self.api_headers, \
            data=json.dumps(records))

        if self.validate_response(req_del_rrs, 200, "delete records of " + zone):
            return 1

    # Utility functions
    def find_api_token(self):
        dsDirs=["~/.secrets/","~/.api/","~/"]        # Common directories
        dsfnames=["desec","desec.key","desec.api"]   # DeSEC filenames
        found_path=""

        for filename in dsfnames:
            for directory in dsDirs:
                if os.path.exists(os.path.expanduser(directory+filename)):
                    found_path=os.path.expanduser(directory+filename)

        if not found_path:
            return ""
        else:
            print("Found DeSEC API key in path: " + found_path)
            with open(found_path,"r") as api_file:
                return api_file.read()[:-1]     # Need to remove the final file newline

    def open_template_file(self, json_file_path):
        try:
            with open(json_file_path, "r") as template_fh:
                template_json = json.load(template_fh)
            return template_json
        except EnvironmentError:
            print("Unable to open '" + json_file_path + "' file path")

    def validate_response(self, api_resp, good_code, action_verb):
        if api_resp.status_code == good_code:
            print("API call for " + action_verb + " completed successfully")
            return 1
        else:
            sys.stderr.write(
                "API call for " + action_verb + " with failed code " +
                str(api_resp.status_code) + ".\n")
            sys.stdout.write(json.dumps(api_resp.json(), indent=4) + "\n")
            return 0

# Below is CLI only - Check namespace to confirm whether running standalone
if __name__ == "__main__":
    # CLI ONLY :: Parameter handling
    MDZ_ARGV = argparse.ArgumentParser( \
        description="Python implementation for DeSEC's API")

    MDZ_ARGV.add_argument('action', help="The action to be executed")
    MDZ_ARGV.add_argument('zone', help="The DNS zone perform the action on", nargs='?')
    MDZ_ARGV.add_argument('--key', '-k', help='API key used to authenticate the action')
    MDZ_ARGV.add_argument('--template', '-t', help='JSON template of DNS records to action')
    MDZ_ARGV.add_argument('--json', '-j', help='Return results in JSON', dest="ofmt", \
        action="store_const", const="json")

    MDZ_ARGV = MDZ_ARGV.parse_args()
    MDZ_OBJ = manageDesecZone(MDZ_ARGV.action, MDZ_ARGV.zone, MDZ_ARGV.key, \
        MDZ_ARGV.template, MDZ_ARGV.ofmt)