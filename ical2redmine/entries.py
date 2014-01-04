'''This module fetches, creates, updates and removes time entries in Redmine.'''
# We need the log
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

def create(data):
	'''Creates time entries in Redmine.'''
	entry = TimeEntries()
	entry.attributes.update(data)
	return entry.save()

def update(): #entry, date
	'''Updates time entries in Redmine.'''
	#entry.attributes.update(data)
	#return entry.save()
	log.error("Not implemented!")

def remove(): #entry
	'''Removes time entries in Redmine.'''
	log.error("Not implemented!")