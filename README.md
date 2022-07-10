# Nix-Toolkit

An assortment of Linux utilities built for specific development and deployment needs as required over the years.

Note: This repository is in the process of being built up from a collection of personal offline sources and subject to change quite a bit until this full composite list of utilities is finalized and refactored to work more generally.

## Utilities

| Name                | Purpose                                                      |
| ------------------- | ------------------------------------------------------------ |
| scriptFunctions     | Essentially macros to be sourced externally by other scripts |
| <u>funcs/</u>       | A concise list of function scripts to be called by <u>*scriptFunctions*</u> |
| checkUpdate.bsh     | A multi-distribution wrapper to check system updates & churn them into a CSV formatting for additional post-processing. |
| backupDirectory.bsh | An NFS-specific backup utility (callable from crontab) to automate the backup of a given directory to external NFS server with automatic backup clean-up (Based on modified date). |
| discoverSystem.bsh  | Performs numerous system-level checks to determine the current hardware and operating system state. Designed to be run-post installation to determine local system capability. |
| notifyService.py    | A service-agnostic method of callable external system notifications using templates invoked either directly, or through piped commands. |
