#!/bin/bash

export $(grep -v '^#' .env | xargs -d '\n')

function router() {
    docker-compose -f docker-compose.yml up --build -d --force-recreate --no-deps router
}

function writers() {
    docker-compose -f docker-compose.yml up --build -d --force-recreate --no-deps generic-writer xray-writer
}

function db() {
    docker-compose -f docker-compose.yml up --build -d --force-recreate --no-deps generic-db xray-db
}

function all() {
    docker-compose -f docker-compose.yml up --build -d --force-recreate
}

if [[ -z "$1" ]]; then
    all
else
    $1
fi