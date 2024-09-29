#!/usr/bin/env sh

wait_mysql() {
    echo "Waiting MySQL to be ready..."
    while ! nc -z database 3306; do   
        sleep 3
    done
    echo "MySQL is ready!"
}

wait_mysql
python3 ./wordpress-plugin-audit.py --create-schema --download --audit --download-dir /audit/