'''This module fetches and processes events from an iCal feed.'''
import requests
# We need the log
from ical2redmine.logger import LOG as log
from icalendar import Calendar

def fetch(ical_url):
	'''Fetches events from an iCal feed.'''
	log.debug("Fetching ical feeds from %s." % ical_url)
	response = requests.get(ical_url)
	calendar = Calendar.from_ical(response.text)
	print calendar.items()
	name = calendar.get('X-WR-CALNAME')
	description = calendar.get('X-WR-CALDESC')
	if name and description:
		log.debug("Fetched calendar: '%s' (%s).", name, description)
	elif name:
		log.debug("Fetched calendar: '%s'.", name)
	else:
		log.debug("Fetched calendar!")
	result = dict()
	for event in calendar.walk("VEVENT"):
		result[str(event.get('UID'))] = event
	return result

def determine_event_destiny(event, users_entries, settings):
	'''Determines an events destiny, should it be created, updated or deleted?
	* An entry should be created if:
	  1. The event is not already represented in Redmine,
	  2. The event's start date is not too far into the past.
	* An entry should be updated if:
	  1. The event is already represented in Redmine
	  2. It's data has changed,
	  3. The event is not too old,
	  4. The entry is not too old,
	  5. The event has not been moved into the future.
	* An entry should be deleted if:
	  1. The event is represented in Redmine,
	  2. The entry is not too old,
	  2. The event has been moved too far back or into the future.
	* An entry should be deleted if: (cleaning up)
	  1. The entry is in Redmine,
	  2. The entry is not too old,
	  3. The event has been removed from the feed,
	'''
	event_start = event.get('DTSTART').dt
	event_end = event.get('DTEND').dt
	#print users_entries
	event_is_represented = False # TODO: Implement this when an event is created.
	event_too_old_for_creation = \
		settings['create_entries_no_older_than'] > event_start
	if not event_is_represented and not event_too_old_for_creation:
		return "create"
	return "skipped"

def process(users_events, users_entries, settings):
	'''Processes events from an iCal feed.'''
	matching_events = {}
	# Loop through all iCal events from the ical feed.
	for uid, event in users_events.items():
		summary = unicode(event.get('SUMMARY'))
		# Match the pattern with the summary.
		match = settings["pattern"].match(summary)
		if match:
			issue_id = match.group('issue_id')
			matching_events[uid] = event, issue_id
			# We've got a relevant event
			log.debug("An event '%s' (%s) matches issue id #%s", summary, uid, issue_id)
	log.info("Found %u events in the iCal feed matching the pattern.",
		len(matching_events) )
	for uid, (event, issue_id) in matching_events.items():
		if 'DTSTART' not in event.keys() or 'DTEND' not in event.keys():
			log.error("Skipping malformed event from iCal feed, uid=%s", uid)
			continue # Skip
		destiny = determine_event_destiny(event, users_entries, settings)
		log.debug("The processing should %s event with uid = %s", destiny, uid)
		if event.get('SEQUENCE'): # TODO: Need to implement support for this.
			log.debug("SEQUENCE found!")
