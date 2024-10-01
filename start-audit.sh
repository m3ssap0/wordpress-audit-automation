#!/usr/bin/env sh

wait_mysql() {
    echo "Waiting MySQL to be ready..."
    while ! nc -z database 3306; do   
        sleep 3
    done
    echo "MySQL is ready!"
}

wait_mysql

if [ -d "/audit/semgrep-rules/" ]; then
    python3 ./wordpress-plugin-audit.py --verbose --create-schema --download --audit --download-dir /audit/ --config /audit/semgrep-rules/
else
    python3 ./wordpress-plugin-audit.py --verbose --create-schema --download --audit --download-dir /audit/
fi