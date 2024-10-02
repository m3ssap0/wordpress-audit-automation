import requests
import argparse
import os
import json
import subprocess
import zipfile
import shutil
import logging
import time
from datetime import datetime
from io import BytesIO
from dbutils import (
    connect_to_db,
    delete_results_table,
    insert_result_into_db,
    insert_plugin_into_db,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def http_get(url):
    do_request = True
    while do_request:
        try:
            response = requests.get(url)
            do_request = False
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout for '{url}'.")
            time.sleep(5)
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error for '{url}'.")
            time.sleep(5)

    return response


# Let's only retrieve 10 plugins per page so people feel like the status bar is actually moving
def get_plugins(page=1, per_page=10):
    url = f"https://api.wordpress.org/plugins/info/1.2/?action=query_plugins&request[page]={page}&request[per_page]={per_page}"
    response = http_get(url)

    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to retrieve page {page}: {response.status_code}")
        return None


def write_plugins_to_csv_db_and_download(db_conn, cursor, download_dir, verbose=False):
    logger.info("Download plugins.")

    # Get the first page to find out the total number of pages
    data = get_plugins(page=1)

    if not data or "info" not in data:
        logger.error("Failed to retrieve the plugin information.")
        return

    total_pages = data["info"]["pages"]

    # Ensure the directory for plugins exists
    os.makedirs(os.path.join(download_dir, "plugins"), exist_ok=True)

    # Iterate through the pages
    for page in range(1, total_pages + 1):
        if verbose:
            logger.info(f"Page {page}/{total_pages}.")

        data = get_plugins(page=page)

        if not data or "plugins" not in data:
            break

        for plugin in data["plugins"]:
            insert_plugin_into_db(cursor, plugin)
            db_conn.commit()

            if verbose:
                logger.info(f"Inserted data for plugin {plugin['slug']}.")
            # Download and extract the plugin
            download_and_extract_plugin(plugin, download_dir, verbose)


def download_and_extract_plugin(plugin, download_dir, verbose):
    slug = plugin["slug"]
    download_link = plugin.get("download_link")
    last_updated = plugin.get("last_updated")

    # Check if the plugin was last updated in the last 2 years, we'll only download the ones that actively maintained
    try:
        # Parse the date format 'YYYY-MM-DD HH:MMpm GMT'
        last_updated_datetime = datetime.strptime(last_updated, "%Y-%m-%d %I:%M%p %Z")
        last_updated_year = last_updated_datetime.year
        if last_updated_year < (datetime.now().year - 2):
            return
    except ValueError:
        logger.error(f"Invalid date format for plugin {slug}: {last_updated}")
        return

    # Excluding plugins with few installs.
    try:
        active_installs = int(plugin.get("active_installs"))
        if active_installs < 1000:
            return
    except:
        logger.error(f"Invalid active installs format for plugin {slug}: {active_installs}")
        return

    # Download and extract the plugin
    plugin_path = os.path.join(download_dir, "plugins", slug)

    # Skip the plugin if the directory exists
    if os.path.exists(plugin_path):
        if verbose:
            logger.warning(f"Plugin folder already exists, skipping folder creation: {plugin_path}")
        return

    try:
        if verbose:
            logger.info(f"Downloading and extracting plugin: {slug}")
        response = http_get(download_link)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            z.extractall(os.path.join(download_dir, "plugins"))
    except requests.RequestException as e:
        logger.error(f"Failed to download {slug}: {e}")
    except zipfile.BadZipFile:
        logger.error(f"Failed to unzip {slug}: Not a zip file or corrupt zip file")


def run_semgrep_and_store_results(db_conn, cursor, download_dir, config, verbose=False):
    logger.info("Run Semgrep and store results.")

    plugins = os.listdir(os.path.join(download_dir, "plugins"))

    for plugin in plugins:
        plugin_path = os.path.join(download_dir, "plugins", plugin)
        output_file = os.path.join(plugin_path, "semgrep_output.json")

        command = [
            "semgrep",
            "--config",
            "{}".format(config),
            "--json",
            "--no-git-ignore",
            "--output",
            output_file,
            "--quiet",  # Suppress non-essential output
            plugin_path,
        ]

        try:
            # Run the semgrep command
            subprocess.run(command, check=True)
            if verbose:
                logger.info(f"Semgrep analysis completed for {plugin}.")

        except subprocess.CalledProcessError as e:
            logger.error(f"Semgrep failed for {plugin}: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for {plugin}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error for {plugin}: {e}")

        # Read the output file and process results
        with open(output_file, "r") as file:
            data = json.load(file)
            for item in data["results"]:
                insert_result_into_db(cursor, plugin, item)
                db_conn.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Downloads or audits all Wordpress plugins."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download and extract plugins, if plugin directory already exists, it will delete it and redownload",
    )
    parser.add_argument(
        "--download-dir",
        type=str,
        default=".",
        help="The directory to save/audit downloaded plugins (default: current directory)",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Audits downloaded plugins sequentially",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="p/php",
        help="Semgrep config/rules to run - https://semgrep.dev/docs/running-rules#running-semgrep-registry-rules-locally (default: p/php)",
    )
    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create the database and schema if this flag is set",
    )
    parser.add_argument(
        "--clear-results",
        action="store_true",
        help="Clear audit table and then run, useful if run as a cron job and we only care about the latest release",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print detailed messages"
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.download and not args.audit:
        logger.error("Please set either the --download or --audit option.\n")
        parser.print_help()

    else:
        logger.info("Started audit.")
        # Create schema
        db_conn, cursor = connect_to_db(args.create_schema)
        if args.clear_results:
            delete_results_table(cursor)

        # Write plugins to CSV, Database, and possibly download them
        if args.download:
            write_plugins_to_csv_db_and_download(
                db_conn, cursor, args.download_dir, args.verbose
            )
        if args.audit:
            run_semgrep_and_store_results(
                db_conn, cursor, args.download_dir, args.config, args.verbose
            )

        cursor.close()
        db_conn.close()
