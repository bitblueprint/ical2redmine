'''Determines an events destiny: skipped, created, updated or deleted?'''
import dateutil.parser
from dateutil.tz import tzlocal
from ical2redmine.logger import LOG as log
from ical2redmine.entries import event2entry
from datetime import datetime

DESTINY_SKIP = 'skipped'
DESTINY_CREATE = 'created'
DESTINY_UPDATE = 'updated'
DESTINY_DELETE = 'deleted'

def entry_freezed(entry, settings):
	'''Tests if an entry is too old to be deleted or updated.'''
	if settings['freeze_entries_older_than'] == "":
		return False
	spent_on = dateutil.parser.parse(entry.spent_on)
	if settings['freeze_entries_older_than'].replace(tzinfo=None) > spent_on:
		log.debug("Entry freezed because it's too old.")
		return True
	else:
		return False

def event_ignored(event, settings):
	'''Tests if an event is too old to be created or updated as entry.'''
	if settings['ignore_events_older_than'] == "":
		return False
	else:
		too_old = settings['ignore_events_older_than'] > event.get('DTSTART').dt
		in_future = event.get('DTEND').dt > datetime.now( tzlocal() )
		if too_old:
			log.debug("Event ignored because it's too old.")
			return True
		elif in_future:
			log.debug("Event ignored because it's in the future.")
			return True
		else:
			return False

def has_event_changed(event, entry1, issue_id, settings):
	'''Test if event has changed'''
	entry2 = event2entry(event, issue_id, {}, settings)
	changed_spent_on = entry1.spent_on != entry2.spent_on
	changed_hours = entry1.hours != entry2.hours
	changed_comments = entry1.comments != entry2.comments
	changed_issue_id = entry1.issue.id != entry2.issue_id
	if changed_spent_on:
		log.debug("Event has changed the spent_on value.")
		return True
	elif changed_hours:
		log.debug("Event has changed the hours value.")
		return True
	elif changed_comments:
		log.debug("Event has changed the comments value.")
		return True
	elif changed_issue_id:
		log.debug("Event has changed the issue_id value.")
		return True
	else:
		log.debug("Event wasn't changed.")
		return False

def determine_event_destiny(event, issue_id, users_entries, settings):
	'''Determines an events destiny, should it be created, updated or deleted?
	* An entry should be created if:
	  1. The event is not already represented in Redmine,
	  2. The event's start date is not too far in the past. (otherwise it's ignored)
	  3. The event's end date is not in the future. (otherwise it's ignored)
	* An entry should be updated if:
	  1. The event is already represented in Redmine
	  2. It's data has changed,
	  3. The event is not too old, (otherwise it's ignored)
	  4. The entry is not too old, (otherwise it's freezed)
	  5. The event's end date has not been moved into the future. (otherwise it's ignored)
	* An entry should be deleted if:
	  1. The event is represented in Redmine,
	  2. The entry is not too old, (otherwise it's freezed)
	  3. The event's start date has been moved too far back to be considered for creation or it's end date into the future. (otherwise it's ignored)
	* An entry should be deleted if: (cleaning up)
	  1. The entry is in Redmine,
	  2. The entry is not too old, (otherwise it's freezed)
	  3. The event has been removed from the feed,
	'''
	# Make sure that these are in fact datetimes, I suppose if dates are returned
	# as .dt attribute, the event is a full-day event.
	if not isinstance(event.get('DTSTART').dt, datetime):
		log.warning("Skipping an event: As the events DTSTART is a date"\
		" (creating entries for full-day event doesn't make sence)")
		return DESTINY_SKIP
	if not isinstance(event.get('DTEND').dt, datetime):
		log.warning("Skipping an event: As the events DTEND is a date"\
		" (creating entries for full-day event doesn't make sence)")
		return DESTINY_SKIP
	# Derive predicates
	is_represented = unicode(event.get('UID')) in users_entries.keys()
	# TODO: Consider if it should be end or start dates used here.
	event_is_ignored = event_ignored(event, settings)
	if not is_represented and event_is_ignored:
		destiny = DESTINY_SKIP
	elif is_represented:
		entry = users_entries[unicode(event.get('UID'))]
		entry_is_freezed = entry_freezed(entry, settings)
		if entry_is_freezed:
			destiny = DESTINY_SKIP
		elif event_is_ignored:
			destiny = DESTINY_DELETE
		else:
			event_has_changed = has_event_changed(event, entry, issue_id, settings)
			if event_has_changed:
				destiny = DESTINY_UPDATE
			else:
				destiny = DESTINY_SKIP
	else:
		destiny = DESTINY_CREATE
	return destiny