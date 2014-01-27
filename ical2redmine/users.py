'''This module fetches and processes users from Redmine'''
import sys
from ical2redmine.logger import LOG as log
from ical2redmine import events, entries, redmine, destinator, summary

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
		try:
			users_events = events.fetch(ical_url)
		except Exception as err:
			log.error( "Couldn't fetch iCal events: %s", err )
			continue
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
		summary_report = events.process(users_events, existing_user_entries, settings)
		log.info("Skipped: %u", summary_report[destinator.DESTINY_SKIP])
		log.info("Entries created: %u" % summary_report[destinator.DESTINY_CREATE])
		log.info("Entries updated: %u" % summary_report[destinator.DESTINY_UPDATE])
		log.info("Entries deleted: %u" % summary_report[destinator.DESTINY_DELETE])
		log.info("Recurring events: %u" % len(summary_report["recurring_events"]))
		log.info("Errors: %u", len(summary_report['errors']))
		for err in summary_report['errors']:
			log.error("Error '%s': when an entry for issue #%u was attempted %s." % (
				err['exp'],
				int(err['issue_id']),
				err['destiny']
			))
		should_send_summary = summary_report[destinator.DESTINY_CREATE] > 0 or \
			summary_report[destinator.DESTINY_UPDATE] > 0 or \
			summary_report[destinator.DESTINY_DELETE] > 0 or \
			len(summary_report['errors']) > 0
			# TODO: Consider that this might end up spamming the user.
		if should_send_summary:
			summary.send(summary_report, user, settings)
