'''This module fetches users from Redmine'''
# We need the log
from ical2redmine.logger import LOG as log

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