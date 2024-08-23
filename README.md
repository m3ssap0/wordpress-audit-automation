# Wordpress Automated CVE Hunting

Scripts to download every Wordpress plugin (updated in the last 2 years) and run Semgrep over the lot of it while storing output in a database.

Full write-up: https://projectblack.io/blog/cve-hunting-at-scale/

## Getting Started

### Prerequisites

* Ubuntu or other nix system
* MySQL database server
* Python
* Patience

## Steps
1. Setup a MySQL database server
2. Clone this repo
    ```
    git clone https://github.com/prjblk/wordpress-audit-automation
    ```
3. Configure the config file with database credentials/details
    ```
    cp config.ini.sample config.ini
    nano config.ini
    ```
4. Setup the database schema manually (skip this step if providing privileged database credentials to the script)
    * Create a database and run the SQL in create_plugin_data_table and create_plugin_results_table in dbutils.py
5. Run the download script with the --download flag and --create-schema
    * You might want to run this and the audit script in a tmux/screen session as it takes ages
6. Run the audit script
7. Triage output
8. ???
9. CVEs

### Example Usage

```
$ python3 plugin-download.py -h
usage: plugin-download.py [-h] [--csv CSV] [--download-dir DOWNLOAD_DIR] [--download] [--create-schema] [--verbose]

Download WordPress plugins information, save to a CSV file, insert into a database and optionally download the plugins.

options:
  -h, --help            show this help message and exit
  --csv CSV             The name of the output CSV file (default: output.csv)
  --download-dir DOWNLOAD_DIR
                        The directory to save downloaded files (default: current directory)
  --download            Download and extract plugins based on the CSV file
  --create-schema       Create the database and schema if this flag is set
  --verbose             Print detailed messages

$ python3 plugin-download.py --download --create-schema
Downloading plugins:   0%|                 
```

```
$ python3 plugin-audit.py -h
usage: plugin-audit.py [-h] [--download-dir DOWNLOAD_DIR] [--config CONFIG] [--create-schema] [--verbose]

Runs semgrep over the downloaded plugins and inserts output into the database.

options:
  -h, --help            show this help message and exit
  --download-dir DOWNLOAD_DIR
                        The directory to save downloaded files (default: current directory)
  --config CONFIG       Semgrep config/rules to run - https://semgrep.dev/docs/running-rules#running-semgrep-registry-rules-locally (default: p/php)
  --create-schema       Create the database and schema if this flag is set
  --verbose             Print detailed messages

$ python3 plugin-audit.py
Auditing plugins:  10%|█████████████▍            
```
#### Useful SQL Queries

```
USE SemgrepResults;
SELECT PluginResults.slug,PluginData.active_installs,PluginResults.file_path,PluginResults.start_line,PluginResults.vuln_lines 
FROM PluginResults INNER JOIN PluginData ON PluginResults.slug = PluginData.slug 
WHERE check_id = "php.lang.security.injection.tainted-sql-string.tainted-sql-string"
ORDER BY active_installs DESC
```