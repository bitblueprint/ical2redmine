#!/bin/bash
PYTHONPATH="./lib/pyactiveresource/build/lib.linux-x86_64-2.7/" pylint --indent-string="\t" --reports=n ical2redmine
echo ""
echo "------------------------------ Running ------------------------------"
echo ""

python ical2redmine --log DEBUG --settings settings.json
