# Usr-Scripts

⚠️ **<u>Please Note:</u>** This repository is ungoing clean-up & simplification as a second-tranche of scripts are finally bought under repository management.

An assortment of Linux utilities built for specific needs over the years. This list is very much a work in progress and will be continually updated as old code is found, refactored & modernized (as needed) for inclusion here.

**Note:** None of the below is production-ready code, only making it available in the off chance someone else finds it useful

### notifyService.py

Implements a number of APIs for performing external notifications. Using a toml file as the configuration to define which services to use for a specific notification task

Honestly: This was mostly written as an email & Discord notification tool that requires further expansion

```
usage: notifyService.py [-h] [--file FILE] [--contents CONTENTS] 
	[--initialize] [--dry_run DRY_RUN]

Perform an automated notification across services

options:
  -h, --help            show this help message and exit
  --file FILE, -f FILE  Configuration file + methods to notifiy with
  --contents CONTENTS, -c CONTENTS
                        Notify using file contents instead of stdin
  --initialize          Initize a blank configuration to use
  --dry_run DRY_RUN     Perform a notification dry-run

```

### pullTelegrafConf.bsh

Pulls down a copy of a centrally managed Telegraf configuration from an InfluxDB instance and reloads the service. It does this by setting the service variables used by either **open-rc** or **systemd** (This may work in system V - I haven't tested it).

This is designed to be a quick, dirty and simple (QDS) tool to enroll new endpoints and keep existing endpoints updated by way of a cronjob.

#### Usage

```
usage: pullTelegrafConf.bsh [initial | initialize | first-run ]

Pull down a Telegraf agent configuration from a centrally managed InfluxDB instance. 

Options:
	initial
	initialize
	first-run		Takes INFLUX_URL and INFLUX_TOKEN and sets them as  						usable service variables for systemd or open-rc
```

# ./dns/ Utilities

### manageDesecZone.py

Manage & update DNS zones hosted by [**desec.io**]()

Note: A few examples are provided under `./dns/zone-templates`

```
usage: manageDesecZone.py [-h] [--key KEY] [--template TEMPLATE] [--json] action [zone]

Python implementation for DeSEC's API

positional arguments:
  action                The action to be executed
  zone                  The DNS zone perform the action on

options:
  -h, --help            show this help message and exit
  --key KEY, -k KEY     API key used to authenticate the action
  --template TEMPLATE, -t TEMPLATE
                        JSON template of DNS records to action
  --json, -j            Return results in JSON

```

#### Todo

- [ ] Validate & add checks for both importable & CLI operation (Currently only validated for CLI usage) 

### manageGandiZone.py

Perform numerous registrar actions for [**gandi.net**]()

```
usage: manageGandiZone.py [-h] [--json] [--key KEY] action [zone]

A Python CLI & callable object for interfacing with the Gandi DNS API

positional arguments:
  action             Available actions: [list | info | query | register]
  zone               The DNS zone perform the action on

options:
  -h, --help         show this help message and exit
  --json, -j         Return results in JSON
  --key KEY, -k KEY  An explicit API key to use
  
```

#### Todo

- [ ] Validate & add checks for both importable & CLI operation (Currently only validated for CLI usage)
- [ ] Implement the API for domains delegated to Gandi itself 

# ./wireguard/ Utilities

### enrollWgClient.py

Reads the existing wireguard configuration & enrolls additional clients to it + generates the required client configuration as a file, stdout or QR code.

```
usage: enrollWgClient.py [-h] [--server SERVER] [--conf CONF] [--port PORT] 
		[--file FILE] [--qr] name

Enroll a new peer into Wireguard

positional arguments:
  name             Uniquily identifable client name

options:
  -h, --help       show this help message and exit
  --server SERVER  Server endpoint hostname/address
  --conf CONF      Wireguard conf path
  --port PORT      Set client port
  --file FILE      Export client configuration to file
  --qr             Display as QR code
  
```

#### Todo

- [ ] Code clean-up
- [ ] Add PreUp & PostUp options
- [ ] Add PersistentKeepAlive option

### toggleWgIpMasq.bsh

Simple toggle to enable or disable IP masquerade via iptables on Linux.

```
usage: toggleWgIpMasq.bsh enable | disable [interface]
```

#### Todo

- [ ] Add checking for existing rule before adding `iptables -C`



