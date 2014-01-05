'''This module fetches and processes events from an iCal feed.'''
import requests, icalendar, dateutil.parser
# We need the log
from ical2redmine.logger import LOG as log
from datetime import datetime
from ical2redmine import entries
from dateutil.tz import tzlocal

def localize_timezones(event):
	'''Makes sure all date and datetimes are in the local timezone.'''
	for field_name, field_value in event.items():
		if isinstance(field_value, icalendar.prop.vDDDTypes):
			# Is this infact a datetime?
			if isinstance(field_value.dt, datetime):
				event.set(field_name, field_value.dt.astimezone( tzlocal() ) )
	return event

def fetch(ical_url):
	'''Fetches events from an iCal feed.'''
	log.debug("Fetching ical feeds from %s." % ical_url)
	response = requests.get(ical_url)
	calendar = icalendar.Calendar.from_ical(response.text)
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
		event = localize_timezones(event)
		result[str(event.get('UID'))] = event
	return result

DESTINY_SKIP = 'skipped'
DESTINY_CREATE = 'created'
DESTINY_UPDATE = 'updated'
DESTINY_DELETE = 'deleted'

def helper_destiny2settings_key(proposed_destiny):
	'''A helper that turns a destiny into a settings key.'''
	if proposed_destiny == DESTINY_CREATE:
		return 'create_entries_no_older_than'
	elif proposed_destiny == DESTINY_UPDATE:
		return 'update_entries_no_older_than'
	elif proposed_destiny == DESTINY_DELETE:
		return 'delete_entries_no_older_than'
	else:
		return None

def is_event_too_old(proposed_destiny, event, settings):
	'''Tests if an event is too old for a specific destiny.'''
	settings_key = helper_destiny2settings_key(proposed_destiny)
	if settings_key:
		if settings[settings_key] == True:
			return False
		elif settings[settings_key] == False:
			return True
		else:
			return settings[settings_key] > event.get('DTEND').dt
	else:
		raise ValueError("Unsupported destiny.")

def is_entry_too_old(proposed_destiny, entry, settings):
	'''Tests if an entry is too old for a specific destiny.'''
	settings_key = helper_destiny2settings_key(proposed_destiny)
	if settings_key:
		if settings[settings_key] == True:
			return False
		elif settings[settings_key] == False:
			return True
		else:
			spent_on = dateutil.parser.parse(entry.spent_on)
			return settings[settings_key].replace(tzinfo=None) > spent_on
	else:
		raise ValueError("Unsupported destiny.")

def determine_event_destiny(event, users_entries, settings):
	'''Determines an events destiny, should it be created, updated or deleted?
	* An entry should be created if:
	  1. The event is not already represented in Redmine,
	  2. The event's start date is not too far in the past.
	  3. The event's end date is not in the future.
	* An entry should be updated if:
	  1. The event is already represented in Redmine
	  2. It's data has changed,
	  3. The event is not too old,
	  4. The entry is not too old,
	  5. The event's end date has not been moved into the future.
	* An entry should be deleted if:
	  1. The event is represented in Redmine,
	  2. The entry is not too old,
	  3. The event's start date has been moved too far back to be considered for creation or it's end date into the future.
	* An entry should be deleted if: (cleaning up)
	  1. The entry is in Redmine,
	  2. The entry is not too old,
	  3. The event has been removed from the feed,
	'''
	# Get the datetimes of the start and end.
	now = datetime.now( tzlocal() )
	# Make sure that these are in fact datetimes, I suppose if dates are returned
	# as .dt attribute, the event is a full-day event.
	if not isinstance(event.get('DTSTART').dt, datetime):
		log.debug("Skipping an event: As the events DTSTART is a date"\
		" (creating entries for full-day event doesn't make sence)")
		return DESTINY_SKIP
	if not isinstance(event.get('DTEND').dt, datetime):
		log.debug("Skipping an event: As the events DTEND is a date"\
		" (creating entries for full-day event doesn't make sence)")
		return DESTINY_SKIP
	# Derive predicates
	event_represented = unicode(event.get('UID')) in users_entries.keys()
	# TODO: Consider if it should be end or start dates used here.
	event_too_old_for_creation = is_event_too_old(DESTINY_CREATE, event, settings)
	event_too_old_for_update = is_event_too_old(DESTINY_UPDATE, event, settings)
	event_too_old_for_deletion = is_event_too_old(DESTINY_DELETE, event, settings)
	if event_represented:
		entry = users_entries[unicode(event.get('UID'))]
		entry_too_old_for_creation = is_entry_too_old(DESTINY_CREATE, entry, settings)
		entry_too_old_for_update = is_entry_too_old(DESTINY_UPDATE, entry, settings)
		entry_too_old_for_deletion = is_entry_too_old(DESTINY_DELETE, entry, settings)
	event_in_future = event.get('DTEND').dt > now
	event_has_changed = False # TODO: Find out if it has indeed changed.
	if not event_represented and \
		not event_too_old_for_creation and \
		not event_in_future:
		return DESTINY_CREATE
	elif event_represented and \
		event_has_changed and \
		not event_too_old_for_update and \
		not entry_too_old_for_update and \
		not event_in_future:
		return DESTINY_UPDATE
	elif event_represented and \
		not entry_too_old_for_deletion and \
		(event_too_old_for_creation or event_in_future):
		return DESTINY_DELETE
	else:
		return DESTINY_SKIP

def expand_rrules(some_events, start=False, end=datetime.now(tzlocal()) ):
	'''This function expands recurrances of events, within a time interval'''
	result = {}
	for uid, (event, issue_id) in some_events.items():
		if event.get('RRULE'): # TODO: Need to implement support for this.
			log.debug("RRULE found!")
			rrule = event.get('RRULE')
			# TODO: Do something about this.
		result[uid] = (event, issue_id)
	return result

def process(users_events, users_entries, settings):
	'''Processes events from an iCal feed.'''
	destiny_summary = {
		DESTINY_SKIP: 0,
		DESTINY_CREATE: 0,
		DESTINY_UPDATE: 0,
		DESTINY_DELETE: 0
	}
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
	original_matching_events_count = len(matching_events)
	matching_events = expand_rrules(matching_events)
	log.info("Found %u events in the iCal feed matching the pattern," \
		" which was expanded to %u when expading rrules.",
		original_matching_events_count,
		len(matching_events) )
	for uid, (event, issue_id) in matching_events.items():
		destiny = determine_event_destiny(event, users_entries, settings)
		log.debug("Event (uid=%s) should be %s.", uid, destiny)
		destiny_summary[destiny] += 1
		if destiny == DESTINY_CREATE:
			created = entries.create(event, issue_id, users_entries, settings)
			print created
		elif destiny == DESTINY_UPDATE:
			log.error("Event should be updated, but its not implemented!")
			#created = entries.delete(event, users_entries)
		elif destiny == DESTINY_DELETE:
			entries.delete(event, users_entries)
		elif destiny != DESTINY_SKIP:
			log.error("Unsupported destiny!")

	log.info("Entries (and events) skipped: %u", destiny_summary[DESTINY_SKIP])
	log.info("Entries created: %u", destiny_summary[DESTINY_CREATE])
	log.info("Entries updated: %u", destiny_summary[DESTINY_UPDATE])
	log.info("Entries deleted: %u", destiny_summary[DESTINY_DELETE])
