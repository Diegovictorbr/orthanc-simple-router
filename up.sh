#!/bin/bash

export $(grep -v '^#' .env | xargs -d '\n')

function router() {
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --force-recreate --no-deps orthanc-router
}

function writers() {
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --force-recreate --no-deps general-writer xray-writer
}

function nginx() {
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --force-recreate --no-deps nginx
}

function all() {
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --force-recreate
}

if [[ -z "$1" ]]; then
    all
else
    $1
fi