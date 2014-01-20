'''This module fetches, creates, updates and removes time entries in Redmine.'''
from ical2redmine.logger import LOG as log
from ical2redmine.redmine import TimeEntries

def fetch(user, settings):
	'''Fetches time entries from Redmine.'''
	custom_field_id = settings['custom_time_entry_field_id']
	result = []
	offset = 0
	while True:
		entries = TimeEntries.find( user_id=user.id, offset=offset )
		offset += len(entries)
		for entry in entries:
			# Filter out the entries that has been manually created.
			if entry.created_by_ical2redmine(custom_field_id):
				result.append(entry)
		# If we are not getting any more entries.
		if len(entries) == 0:
			break
	return result

def event2entry(event, issue_id, known_entries, settings):
	'''Maps an event into an entry, without saving it.'''
	event_uid = unicode(event.get('UID'))
	delta = event.get('DTEND').dt-event.get('DTSTART').dt
	delta_hours = delta.total_seconds() / 3600.0 # 60 secs * 60 minutes in an hour
	# Check if the UID is in the known entries.
	entry = TimeEntries()
	if event_uid in known_entries.keys():
		# Update this 'new' time entry with the values (including id)
		# of any known entries.
		entry.attributes.update(known_entries[event_uid].attributes)
	# This is where we handle repeats, events too old or in the future.
	entry.attributes.update({
	 	'issue_id': issue_id,
	 	'spent_on': event.get('DTSTART').dt.strftime("%Y-%m-%d"),
	 	'hours': "%.1f" % delta_hours,
	 	'comments': unicode(event.get('DESCRIPTION')),
	 	'custom_fields': [{
	 		"id": unicode(settings['custom_time_entry_field_id']),
	 		"value": unicode(event.get('UID'))
	 	}]
	})
	if entry.attributes['comments'] == "":
		entry.attributes['comments'] = None
	return entry

def create(event, issue_id, known_entries, settings):
	'''Creates time entries in Redmine from an event.'''
	entry = event2entry(event, issue_id, known_entries, settings)
	assert entry, "Something went wrong when mapping the event 2 entry."
	if not entry.id:
		created = entry.save()
		if created and entry.id:
			return entry
		else:
			return None
	else:
		log.warning("Was asked to create an entry for an event that already exists!")
		return entry

def update(event, issue_id, known_entries, settings):
	'''Updates time entries in Redmine.'''
	entry = event2entry(event, issue_id, known_entries, settings)
	assert entry.id, "Update failed, as no entry existed already. Use create!"
	updated = entry.save()
	if updated:
		return entry
	else:
		return None

def delete(event, users_entries): #entry
	'''Removes time entries in Redmine from an event.'''
	uid = unicode(event.get('UID'))
	if uid in users_entries.keys():
		return users_entries[uid].destroy()
	else:
		raise ValueError("Couldn't delete the entry as it was not already there.")