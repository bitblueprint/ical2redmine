'''This module fetches and processes events from an iCal feed.'''
import requests, icalendar
from ical2redmine.logger import LOG as log
from datetime import datetime
from ical2redmine import entries, destinator
from dateutil.tz import tzlocal
from pyactiveresource.connection import ForbiddenAccess

def localize_timezones(event):
	'''Makes sure all date and datetimes are in the local timezone.'''
	for field_name, field_value in event.items():
		if isinstance(field_value, icalendar.prop.vDDDTypes):
			# Is this infact a datetime?
			if isinstance(field_value.dt, datetime):
				event[field_name].dt = field_value.dt.astimezone( tzlocal() )
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

def find_recurring_events(in_events):
	'''This function expands recurrances of events, within a time interval'''
	result = {}
	for uid, (event, issue_id) in in_events.items():
		if event.get('RRULE'): # TODO: Need to implement support for this.
			rrule = event.get('RRULE')
			result[uid] = (event, issue_id)
	return result

def expand_recurrances(recurring_events, start=False, end=None ):
	'''This function expands recurrances of events, within a time interval'''
	if end == None:
		# Use now as the default value.
		end = datetime.now(tzlocal())
	log.error("The expand rrules functionality has not yet been implemented.")
	result = {}
	for uid, (event, issue_id) in recurring_events.items():
		log.debug("RRULE found!")
		rrule = event.get('RRULE')
		#for recurrance in recurrances:
		# TODO: Do something about this.
		#	result[uid + "#" + recurrance] = (event, issue_id)
	return result

def process(users_events, users_entries, settings):
	'''Processes events from an iCal feed.'''
	summary = {
		destinator.DESTINY_SKIP: 0,
		destinator.DESTINY_CREATE: 0,
		destinator.DESTINY_UPDATE: 0,
		destinator.DESTINY_DELETE: 0,
		'recurring_events': 0,
		'errors': []
	}
	matching_events = {}
	# Loop through all iCal events from the ical feed.
	for uid, event in users_events.items():
		event_summary = unicode(event.get('SUMMARY'))
		# Match the pattern with the summary.
		match = settings["pattern"].match(event_summary)
		if match:
			issue_id = match.group('issue_id')
			matching_events[uid] = event, issue_id
			# We've got a relevant event
			log.debug("An event '%s' (%s) matches issue id #%s",
				event_summary, uid, issue_id)
	original_matching_events_count = len(matching_events)
	# Check for recurring events (currently not supported).
	recurring_events = find_recurring_events(matching_events)
	summary["recurring_events"] = len(recurring_events)
	# matching_events.update(expand_recurrances(recurring_events))
	log.info("Found %u events in the iCal feed matching the pattern," \
		" which was expanded to %u when expading rrules.",
		original_matching_events_count,
		len(matching_events) )

	for uid, (event, issue_id) in matching_events.items():
		destiny = destinator.determine_event_destiny(
			event, issue_id, users_entries, settings)
		log.debug("Event (uid=%s) should be %s.", uid, destiny)
		try:
			if destiny == destinator.DESTINY_CREATE:
				entry = entries.create(event, issue_id, users_entries, settings)
				if entry == None or not entry.id:
					log.error("Error occurred when creating entry.")
			elif destiny == destinator.DESTINY_UPDATE:
				log.error("Event should be updated, but its not implemented!")
				entry = entries.update(event, issue_id, users_entries, settings)
				if entry == None or not entry.id:
					log.error("Error occurred when updating entry.")
			elif destiny == destinator.DESTINY_DELETE:
				entries.delete(event, users_entries)
			elif destiny != destinator.DESTINY_SKIP:
				log.error("Unsupported destiny!")
			summary[destiny] += 1
		except Exception as exp:
			summary['errors'].append({
				'uid': uid,
				'event': event,
				'issue_id': issue_id,
				'destiny': destiny,
				'exp': exp
			})
	return summary
