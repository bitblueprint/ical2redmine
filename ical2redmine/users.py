'''This module fetches and processes users from Redmine'''
# We need the log
import sys
from ical2redmine.logger import LOG as log
from ical2redmine import events, entries, redmine

def fetch(settings):
	'''Fetches users from Redmine'''
	log.debug("Fetching users from %s." % settings["redmine_url"])
	from ical2redmine.redmine import Users
	result = []
	for user in Users.find():
		ical_url = user.get_custom_field_value(settings['custom_user_field_id'])
		if ical_url:
			result.append(user)
	return result

def process(all_users, settings):
	'''Processes users from Redmine'''
	# Process all the users.
	for user in all_users:
		log.info("Processing Redmine user with login '%s'" % user.login)
		redmine.impersonate_user(user)
		ical_url = user.get_custom_field_value(settings['custom_user_field_id'])
		assert ical_url, "The iCal customfield was not sat for this particular user."
		# Fetch the events.
		users_events = events.fetch(ical_url)
		log.info( "Found %u events in the iCal feed." % len(users_events) )
		# Fetch all Redmine time entries for this particular user.
		users_entries = entries.fetch(user, settings)
		log.info( "Found %u entries in the Redmine." % len(users_entries) )
		# Gather ical uids from the Redmine time entries.
		existing_user_entries = {}
		for entry in users_entries:
			uid = entry.get_custom_field_value(settings["custom_time_entry_field_id"])
			if uid in existing_user_entries.keys():
				other_id = existing_user_entries[uid].id
				log.error('Found two time entries (id=%s and id=%s)' +
					' referencing the same iCal uid=%s!', entry.id, other_id, uid )
				continue # Skip the insertion of this entry.
			existing_user_entries[uid] = entry
		if len(existing_user_entries.keys()) != len(users_entries):
			log.error('Found duplicate uids in Redmine, please fix this manually!')
			sys.exit(-1)
		# Process the events.
		events.process(users_events, users_entries, settings)
		# entry_data = {
		# 	'issue_id': 210,
		# 	'spent_on': '2014-01-04',
		# 	'hours': 1,
		# 	'comments': 'Created via script.',
		# 	'custom_fields': [{
		# 		"id": str(settings['custom_time_entry_field_id']),
		# 		"value": 'automatically'
		# 	}]
		# }
		# result = entries.create(entry_data)