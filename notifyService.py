#!/usr/bin/python3
# ------------------------------------------------------
#
#	notifyServices.py - Performs a series of notifications
#   across a number a different services/methods using a
#   pre-defined .conf file
#
#	            Written: James Varoutsos
#	    Date: 25-Jan-2022        Version: 1.0
#
#	    0.7 - Migration + major refactor
#
#   - conf: Configuration file to use
#   - dry_run: Perform a dry-run of the notifications
#   - initialize: generate a blank .conf file with all
#       supported methods included
#
#   TODOS:
#       - Create Discord method JSON templating
#
#	Lint score: 7.99/10 (25-Jan-22)
#
# ------------------------------------------------------

# Standard libraries
import sys
import configparser
import argparse
import smtplib
import requests

from email.message import EmailMessage

class notifyServices:
    def __init__(self, notif_contents, notif_file='notifyServices.conf', init_conf=False, dry_run=False):

        if notif_contents:
            try:
                contents_file = open(notif_contents, "r")
            except OSError:
                print("Unable to open the message file")
            notif_contents = contents_file.read()
            print("msg read from file: " + notif_contents)
        elif sys.stdin:
            # Stops empty/blank commands from hanging waiting on user-input
            if not sys.stdin.isatty():
                notif_contents = sys.stdin.read()
                print("stin at runtime: " + notif_contents)

        if init_conf:
            if self.initialize_configuration(notif_file):
                sys.exit(0)
            else:
                sys.exit(1)

        if not notif_contents:
            print("Empty message")
            sys.exit(2)

        try:
            conf_handle = open(notif_file, "r")
        except OSError:
            print("Unable to open existing configuration '" + notif_file + "'")
            sys.exit(2)
        cnf_objs = self.parse_notification_config(conf_handle)

        # This is the dynamically-calling brain of this thing, don't fuck with it
        for method in cnf_objs.sections():
            fcmd = "notify_" + method.lower()   # Function Method
            func_method = getattr(self, fcmd)
            if hasattr(self, fcmd) and callable(func_method):
                # Le meat'n'potatos
                print("Calling method " + fcmd)
                if func_method(dict(cnf_objs.items(method)), notif_contents):
                    print(method.lower() + " notification ran successfully")
                else:
                    print(method.lower() + " notification did not run correctly")

        conf_handle.close()

    @classmethod
    def initialize_configuration(cls, conf_filepath):
        try:
            conf_handle = open(conf_filepath, "w")
        except OSError:
            print("Unable to create blank configuration file")
            return False

        print("Building a blank configuration file")
        conf_handle.writelines("[Email]\nmail_host =\nrecipients =\nsender =\nsubject =")
        conf_handle.writelines("#Optional\ntemplate = \ntoken =\n")
        conf_handle.writelines("\n[Discord]\nwebhook_id =\nwebhook_token =\ntemplate_json =\ntemplate_token =\n")
        conf_handle.writelines("\n[File]\nfile_path =\n")

        print("Blank configuration file (" + conf_filepath + ") generated successfully")
        return True

    @classmethod
    def parse_notification_config(cls, conf_file_handle):
        print("Parsing notification service configuration")

        conf_file = configparser.ConfigParser()
        conf_file.read_file(conf_file_handle)

        print("Methods to use in this notification ")
        print(conf_file.sections())

        return conf_file

    @classmethod
    def validate_required_params(cls, req_param_list, sect_dict):
        for req_param in req_param_list:
            if req_param not in sect_dict.keys():
                print("Param " + req_param + " not found")
                return False
            elif not sect_dict[req_param]:
                print("Param " + req_param + " is empty")
                return False
        return True


    @classmethod
    def notify_email(cls, opt_dict, msg):
        print("Running email notification...")
        if not cls.validate_required_params(['mail_host', 'recipients', 'sender'], opt_dict):
            print("Required values not provided, exiting")
            return False
        elif not msg:
            print("Empty message provided")
            return False

        notif_email = EmailMessage()

        notif_email['From'] = opt_dict['sender']
        notif_email['To'] = opt_dict['recipients']

        if 'subject' not in opt_dict:
            print("Warning, no subject included in config - Will likely get blocked")
        else:
            notif_email['Subject'] = opt_dict['subject']

        notif_email.set_content(msg)

        if 'template' in opt_dict:
            # Set the find/replace token for the template file
            cont_token = '<<content>>'
            if 'token' in opt_dict:
                cont_token = opt_dict['token']

            print("Template file '" + opt_dict['template'] + "' & token '" + cont_token + "' used")

            try:
                tmpl_file = open(opt_dict['template'], "r")
            except OSError:
                print("Unable to open template file (" + opt_dict['template'] + ")")
                return False
            eml_content_html = tmpl_file.read()
            eml_content_html = eml_content_html.replace(cont_token, msg)
            notif_email.add_alternative(eml_content_html, subtype="html")

        # Wrap some detection logic around this [TBD]
        conn_details = opt_dict['mail_host'].split(":")

        print("Connecting to mail server '" + conn_details[0] + "' on port '" + conn_details[1] +"'")
        email_sndr = smtplib.SMTP(conn_details[0], int(conn_details[1]))

        if 'username' in opt_dict and 'password' in opt_dict:
            try:
                email_sndr.login(opt_dict['username'], opt_dict['password'])
            except (SMTPHeloError, SMTPAuthenticationError):
                print("Unable to log into remote mail server to send message")
                return False

        email_sndr.send_message(notif_email)
        email_sndr.quit()
        return True


    @classmethod
    def notify_discord(cls, opt_dict, msg):
        print("Running Discord notification...")
        discord_base_url = "https://discord.com/api/webhooks/"

        if not cls.validate_required_params(['webhook_id', 'webhook_token'], opt_dict):
            print("Required values not provided, exiting")
            return False
        elif not msg:
            print("Empty message provided")
            return False

        webhook_url = discord_base_url + opt_dict['webhook_id'] + "/" + opt_dict['webhook_token']
        # req_headers = { 'Content-Type': 'application/json' }
        req_body = {'content': msg}

        wh_request = requests.post(webhook_url, json=req_body)

        if wh_request.status_code != requests.codes.ok:
            print("Discord notification failure (" + wh_request.status_code + ")")
            print(wh_request.text)
            return False

        return True

    @classmethod
    def notify_file(cls, opt_dict, msg):
        print("File notification")

        if not cls.validate_required_params(["file_path"], opt_dict):
            print("Required values not provided, exiting")
            return False
        elif not msg:
            print("Empty message provided")
            return False

        try:
            file_notif_handle = open(opt_dict["file_path"], "a")
        except OSError:
            print("Unable to create or open '" + opt_dict["file_path"] + "' for writing")
            sys.exit(1)

        file_notif_handle.write(msg + "\n")
        file_notif_handle.close()

NSV_ARGC = argparse.ArgumentParser(description="Perform an automated notification across services")

NSV_ARGC.add_argument('--file', '-f', default='notifyServices.conf', \
    help="Configuration file + methods to notifiy with")
NSV_ARGC.add_argument('--contents', '-c', \
    help="Notify using file contents instead of stdin")
NSV_ARGC.add_argument('--initialize', default=False, action='store_true', \
    help='Initize a blank configuration to use')
NSV_ARGC.add_argument('--dry_run', default=False, \
    help='Perform a notification dry-run')

NSV_ARGV = NSV_ARGC.parse_args()
NSV_OBJ = notifyServices(NSV_ARGV.contents, NSV_ARGV.file, NSV_ARGV.initialize, NSV_ARGV.dry_run)
