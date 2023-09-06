#!/bin/bash

export $(grep -v '^#' .env | xargs -d '\n')

function router() {
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --force-recreate --no-deps orthanc-router
}

function writers() {
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --force-recreate --no-deps simple-general-writer xray-writer
}

function db() {
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --force-recreate --no-deps simple-router-db
}

function all() {
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --force-recreate
}

if [[ -z "$1" ]]; then
    all
else
    $1
fi