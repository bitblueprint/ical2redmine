#!/bin/bash
DIR=$(cd "$(dirname "$0")"; pwd)
python "$DIR/ical2redmine" --settings settings.json
