#!/bin/bash
PYTHONPATH="./lib/pyactiveresource/build/lib.linux-x86_64-2.7/" pylint --disable=E1103 --indent-string="\t" --reports=n ical2redmine
STATUS=$?
if [ $STATUS == 0 ] || [ $STATUS == 4 ]
then
  echo ""
  echo "------------------------------ Running ------------------------------"
  echo ""
  python ical2redmine --log debug --liblog info --settings settings.production.json
else
  echo "Fix the errors before running - status code is $STATUS"
fi
