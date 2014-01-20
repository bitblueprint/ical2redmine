ical2redmine
============

A tool to keep your redmine time entries updated directly from an ical exportable calendar.
This tool will create, update and delete time entries on your redmine installation based on ical events from a feed of ical events (such as Google Calendar).

Installing dependencies:
 1. Redmine 2.2.0 or above (It has only been tested with Redmine 2.4 but I would expect it to work from Redmine 2.2.0 (as it depends the feature to [Impersonate user through REST API auth](http://www.redmine.org/issues/11755))).
 2. Python interpreter (tested on v2.7 other versions might work as well).
 3. icalendar python module (running ```sudo easy_install icalendar``` after ```sudo apt-get install python-setuptools``` - if the easy_install tool is not installed)
 4. requests python module (running ```sudo easy_install requests```)

Limitations:
 * At the moment the tool doesn't support recurring events - I have plans to fix this.

How to install:
 1. Clone the Github repo onto your local machine or server, running ```git clone https://github.com/bitblueprint/ical2redmine.git``` on a unix/linux machine.
 2. Fetch the pyactiveresource dependency submodule by navigating into your newly cloned ical2redmine directory and run ```git submodule update --init```
 3. You have to build the pyactiveresource dependency by first navigating into the folder: ```cd pyactiveresource``` and then building the library, running: ```python setup.py build```, navigate back to the ical2redmine directory. (I hope to add these two manual build steps automatically in the future.)
 4. You have to create two custom variables on your Redmine installation.
  * Login to your redmine installation, using an administrative account.
  * Navigate to _Administration > Custom fields_
  * Under the tab titled _Spent time_ click the _New custom field_ link, enter the name _iCal UID_ and hit the _Save_ button (leaving _Text_ as _Type_ and _Required_ unchecked).
  * Under the tab titled _Users_ create another customfield named _iCal Time Entry URL_ same options as the other custom field.
  * NB: It is also possible to give these custom fields other names, but then you have to specify their custom field ids in the ical2redmine settings.json file.
 5. Copy the settings.example.json (located in the root of the repository) file to some other file like settings.json (```cp settings.example.json settings.json```) and start filling in the blank ___'s. Please consult the example file and source-code for details on the values of the parameters. (I hope to incorporate a settings guide into the tool sooner or later - until now you have to live with the following.)
  * __redmine_url__: The URL to the redmine installation, into which iCal events should be imported.
  * __pattern__: A [reqular expression pattern](http://docs.python.org/2/howto/regex.html) for the summary(/title) of the iCal events. This patterns is required to have a named group called "issue_id", this tells ical2redmine which issue to log time on.
  * __create_entries_no_older_than__: Put a limit onto how old an event can be, to be considered for creation in Redmine. The value should be
   * A date (in the YYYY-MM-DD format) ex: _"2014-01-20"_ for the 20th of January 2014,
   * A timedelta in days, ex: _"1 day"_ or _"30 days"_,
   * A boolean value _true_ or the empty string _""_ if events be created as entries no matter how far in the past they are. (This is default behaviour)
   * A boolean value _false_ if events should never be created.
  * __update_entries_no_older_than__: Put a limit onto how old an event can be, to be considered for update in Redmine. Same values as prevouis bullit.
  * __delete_entries_no_older_than__: Put a limit onto how old an event can be, to be considered for deletion in Redmine. Same values as prevouis bullit.
  * __custom_time_entry_field_id__: The _id_ of the field created in 4.3 (not needed if you gave it the correct name)
  * __custom_user_field_id__: The _user_ of the field created in 4.4 (not needed if you gave it the correct name)
  * __api_key__: The API key of an administrative user. This is visible on the _My account_ (link in the top-right corner) page, when clicking the _Show_ link below _API access key_ on the light hand side.
 6. The final step is to add the URL of the iCal feed to your users account: Again on the _My account_ page add the URL in the newly created _iCal Time Entry URL_ custom field. If you are importing from Google Calendar, follow [this guide](https://support.google.com/calendar/answer/37111?hl=en&ref_topic=1672003) to obtain your private iCal URL. Instead of downloading the .ical file, copy the link. Please note that sharing this link on the Redmine installation will enable administrators to see and change your calendar, so consider using a seperate calendar for this.
 7. Now create events in the calendar, whereever you would like to report time entries. Using the standard pattern provided in the example settings file, the summary(/title) should contain _#n_ where _n_ is an integer referring to an issue id, on which to report time.
 8. Now run the tool by executing the following command: ```python ical2redmine.py --settings settings.json```.
 9. Consider setting this up as a periotic [cron job](http://www.adminschoice.com/crontab-quick-reference/) so you don't have to run the tool manually.

The process that the processor goes through:
 1. Fetch all users from Redmine, filter them such that only the ones with an _iCal Time Entry URL_ custom field sat remains. Loop trough these users one by one:
   1. Fetch the iCal feed of events, from the URL specified by the user.
   2. Fetch all the users time entries in Redmine, filter them such that only the ones with the _iCal UID_ custom field sat remains.
   3. Loop through all iCal events from the ical feed and determine if they should be
   4. Loop through all the users Redmine events from the ical feed:

Further suggestions for implementations:
 * Consider: Keep a state (a dictionary of hases of the response from fetching iCal URLs) and check if the iCal feed has changed before fetching and looping though Redmine entries.
 * Add email support to warn users if an event without a comment is created or if an event is referencing an issue on a project where the user is not participating.
 * Implementing the use of SEQUENCE numbers, from the iCal events to detect changes.
 * Implementing the use of LAST-MODIFIED datetimes, from the iCal events to detect changes.
 * Implementing the use of CREATED datetimes, from the iCal events to detect new events.
