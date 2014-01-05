'''A module to create/update/remove Redmine time entries from a iCal feeds.'''
import logging, argparse, os, sys, json, re
# Append the parent directory in the system path.
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
# Get a global logger called log.
from ical2redmine.logger import LOG as log
from datetime import datetime, timedelta
from dateutil.tz import tzlocal

REQUIRED_SETTINGS_FIELDS = [ "redmine_url", "pattern", "api_key" ]

DEFAULT_SETTINGS = {
	"update_entries": True,
	"custom_user_field_name": "iCal Time Entry URL",
	"custom_time_entry_field_name": "iCal UID",
	"create_entries_no_older_than": "", # Always create events.
	"update_entries_no_older_than": "", # Always update events.
	"delete_entries_no_older_than": "" # Always delete events.
}

LOG_LEVELS = [ 'debug', 'info', 'warning', 'error', 'critical' ]

DATE_PATTERN = "(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})" # ISO
TIMEDELTA_PATTERN = "(?P<days>\d+) ?days?" # timedelta

TIMEDELTA_SETTINGS_FIELDS = [ "create_entries_no_older_than",
	"update_entries_no_older_than", "delete_entries_no_older_than"]

def print_logo():
	'''A function that prints the logo to the output'''
	print " _             _  ______                  _       _             "
	print "(_)           | |(_____ \                | |     (_)            "
	print " _  ____ _____| |  ____) ) ____ _____  __| |____  _ ____  _____ "
	print "| |/ ___|____ | | / ____/ / ___) ___ |/ _  |    \| |  _ \| ___ |"
	print "| ( (___/ ___ | || (_____| |   | ____( (_| | | | | | | | | ____|"
	print "|_|\____)_____|\_)_______)_|   |_____)\____|_|_|_|_|_| |_|_____)"
	print " - by Kraen Hansen <kh@bitblueprint.com>                   v.0.3\n"

def parse_arguments():
	'''Parsing the runtime arguments given to the tool'''
	parser = argparse.ArgumentParser()
	parser.add_argument('-s', '--settings', required=True,
		help='The settings to use for creating time entries.')
	parser.add_argument('-l', '--log', default='info',
		help='Set the log level.', choices=LOG_LEVELS)
	parser.add_argument('-ll', '--liblog', default='warning',
		help='Set the libs log level.', choices=LOG_LEVELS)
	return parser.parse_args()

LIB_LOGGERS = ['pyactiveresource', 'requests']

def bootstrap_logger(log_level, liblog_level):
	'''Sets up the logger.'''
	# Make sure it's uppercase.
	log_level = log_level.upper()
	liblog_level = liblog_level.upper()
	# Derive the nummeric value for the logging level.
	numeric_log_level = getattr(logging, log_level, None)
	if not isinstance(numeric_log_level, int):
		raise ValueError('Invalid log level: %s' % log_level)
	# Set the basic configuration on the logger.
	logging.basicConfig(format='%(name)s %(levelname)s: %(message)s',
		level=numeric_log_level)
	log.debug("Logger was configured.")
	# Set the logging level of the libs.
	# Derive the nummeric value for the logging level.
	numeric_liblog_level = getattr(logging, liblog_level, None)
	if not isinstance(numeric_log_level, int):
		raise ValueError('Invalid lib log level: %s' % liblog_level)
	# Set the libs logger to warning mode.
	for lib_logger in LIB_LOGGERS:
		logging.getLogger(lib_logger).setLevel(numeric_liblog_level)

def bootstrap_libs():
	'''Sets include path for the libs.'''
	# What is the current directory of this file?
	current_path = os.path.dirname(os.path.realpath(__file__))
	libs_path = os.path.join(current_path, "..", "lib")
	# Check if the lib has been build.
	for lib in os.listdir(libs_path):
		# First, onload any included libs from the path.
		unload_lib(lib)
		# Then find the libs new path.
		lib_path = os.path.join(libs_path, lib)
		lib_path = os.path.realpath(lib_path)
		if 'build' not in os.listdir(lib_path):
			log.error("Library not build! You have to build the %s lib, "
				"before you run this tool. Navigate into the %s "
				"directory and execute 'python setup.py build'.", lib, lib_path)
			sys.exit(-3)
		else:
			# Put the lib in the python path.
			lib_build_path = os.path.join(lib_path, 'build')
			# Find the specific platform dependent folder.
			platform_folder = os.listdir(lib_build_path)[0]
			lib_platform_path = os.path.join(lib_build_path, platform_folder)
			log.debug("Adding lib %s to the python path.", lib_platform_path)
			sys.path.append(lib_platform_path)

def load_settings(settings_filepath):
	'''Loads the settings file.'''
	settings_filepath = os.path.realpath(settings_filepath)
	log.debug("Loading the settings file '%s'" % settings_filepath)
	try:
		settings_handle = open(settings_filepath, 'r')
		settings = json.loads(settings_handle.read())
		settings_handle.close()
		return settings
	except IOError as error:
		log.error("Couldn't load settings file: %s" % error)
		sys.exit(-1)

def check_settings(settings):
	'''Checks (using assertions) the sanity of the settings file'''
	# Check requered fields.
	for field in REQUIRED_SETTINGS_FIELDS:
		assert field in settings.keys(), "Required field '%s' was not set in the"\
		" settings file, please consult settings.example.json to learn the"\
		" correct fieldnames." % field

def unload_lib(package_name):
	'''Unloading a package .egg'''
	for package_path in sys.path:
		if package_name in package_path and ".egg" in package_path:
			log.debug("Removing the %s package (%s) from the system path."
				% (package_name, package_path))
			sys.path.remove(package_path)

def check_custom_fields(settings, custom_fields):
	'''Fetches and checks the custom fields, given in settings.'''
	fields = [
		('custom_time_entry_field_id', 'custom_time_entry_field_name'),
		('custom_user_field_id', 'custom_user_field_name')
	]
	for field_id, field_name in fields:
		field_id_value = settings.get(field_id)
		field_name_value = settings.get(field_name)
		settings[field_id] = check_custom_field( custom_fields, field_id_value,
			field_name_value )

def check_custom_field(custom_fields, field_id, field_name):
	'''Checks a single custom field, given in settings.'''
	if field_id:
		for field in custom_fields:
			if int(field.id) == field_id:
				return int(field.id)
		raise ValueError("Custom field (id=%s) doesn't exist." % field_id)
	elif field_name:
		for field in custom_fields:
			if field.name == field_name:
				return int(field.id)
		raise ValueError("Custom field (name='%s') doesn't exist." % field_name)
	else:
		raise ValueError("Either id or name of the custom field must be specified!")

def convert_timedelta_settings(settings):
	'''Convert all the timedelta settings.'''
	for settings_field in TIMEDELTA_SETTINGS_FIELDS:
		settings_value = settings[settings_field]
		date_match = re.match(DATE_PATTERN, settings_value)
		timedelta_match = re.match(TIMEDELTA_PATTERN, settings_value)
		if date_match:
			# No older than a specific date.
			year = int(date_match.group('year'))
			month = int(date_match.group('month'))
			day = int(date_match.group('day'))
			settings[settings_field] = datetime( year=year, month=month, day=day,
				tzinfo=tzlocal() )
		elif timedelta_match:
			days = int(timedelta_match.group('days'))
			latest_datetime = datetime.now( tz=tzlocal() ) - timedelta( days=days )
			settings[settings_field] = latest_datetime
		elif settings_value == "" or settings_value == True:
			# Do it no matter the date.
			# Setting to True, in case of an empty string.
			settings[settings_field] = True
		elif settings_value == False:
			# Never do it!
			continue
		else:
			raise ValueError("The value of the %s field in the settings, "\
				"doesn't match the expected format, please read the "\
				"settings.example.json or the projects README file.")

def process(settings):
	'''Start the processing of '''
	# We should wait with the imports until now that the libs are loaded.
	import pyactiveresource
	# should be loaded first.
	from ical2redmine import redmine, users
	# Setting the API key for the active resource to use.
	redmine.setup(settings['redmine_url'], settings['api_key'])
	try:
		check_custom_fields(settings, redmine.CustomFields.find())
		# Fetch all the redmine users with iCal URLs sat.
		all_users = users.fetch(settings)
		log.info( "Found %u user(s) in Redmine, with the iCal Feed URL sat."
			% len(all_users) )
		users.process(all_users, settings)
		log.info("All done ...")
	except pyactiveresource.connection.UnauthorizedAccess as err:
		log.error("Unauhorized access to Redmine, are you sure the api_key" \
			" in the settings file belongs to an administrator? %s", err)
		sys.exit(-1)

def main():
	'''This is where it all comes together.'''
	arguments = parse_arguments()
	print_logo()
	bootstrap_logger(arguments.log, arguments.liblog)
	bootstrap_libs()
	try:
		loaded_settings = load_settings(arguments.settings)
		check_settings(loaded_settings)
	except AssertionError as settings_error:
		log.error("Invalid settings file: %s" % settings_error)
		sys.exit(-2)
	except ValueError as settings_error:
		log.error("Invalid settings file: %s" % settings_error)
		sys.exit(-2)
	settings = dict()
	settings.update(DEFAULT_SETTINGS)
	settings.update(loaded_settings)
	# Compiling the pattern.
	settings["pattern"] = re.compile(settings["pattern"])
	assert settings["pattern"], "The pattern didn't compile."
	issue_id_in_pattern = 'issue_id' in settings["pattern"].groupindex.keys()
	assert issue_id_in_pattern,	"The pattern specified in the settings, " \
		"must have a named group called 'issue_id', please visit " \
		"http://docs.python.org/2/library/re.html#regular-expression-syntax " \
		"for more information on how to define a regular expression pattern."
	convert_timedelta_settings(settings)
	#print settings['update_entries_age_day_limit']
	process(settings)

if __name__ == '__main__':
	main()