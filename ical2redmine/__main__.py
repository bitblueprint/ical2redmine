'''A module to create/update/remove Redmine time entries from a iCal feeds.'''
import logging, argparse, os, sys, json
# Append the parent directory in the system path.
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
# Get a global logger called log.
from ical2redmine.logger import LOG as log

REQUIRED_SETTINGS_FIELDS = ["redmine_url", "pattern",
	"custom_time_entry_field_id", "custom_user_field_id", "api_key"]

DEFAULT_SETTINGS = {
	"update_entries": True,
	"update_entries_age_day_limit": 30
}

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
	parser.add_argument('-l', '--log', default='WARNING',
		help='Set the log level to debug.')
	return parser.parse_args()

def bootstrap_logger(log_level):
	'''Sets up the logger.'''
	# Make sure it's uppercase.
	log_level = log_level.upper()
	# Derive the nummeric value for the logging level.
	numeric_level = getattr(logging, log_level.upper(), None)
	if not isinstance(numeric_level, int):
		raise ValueError('Invalid log level: %s' % log_level)
	# Set the basic configuration on the logger.
	logging.basicConfig(format='%(name)s %(levelname)s: %(message)s',
		level=numeric_level)
	log.debug("Logger was configured.")

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

def main():
	'''This is where it all comes together.'''
	arguments = parse_arguments()
	print_logo()
	bootstrap_logger(arguments.log)
	bootstrap_libs()
	# Set the pyactiveresource logger to warning mode.
	# logging.getLogger('pyactiveresource').setLevel(logging.WARNING)
	try:
		loaded_settings = load_settings(arguments.settings)
		check_settings(loaded_settings)
	except AssertionError as settings_error:
		log.error("Invalid settings file: %s" % settings_error)
		sys.exit(-2)
	settings = dict()
	settings.update(DEFAULT_SETTINGS)
	settings.update(loaded_settings)
	# We should wait with the imports until now that the libs are loaded.
	import pyactiveresource
	# should be loaded first.
	from ical2redmine import user_fetcher
	from ical2redmine.redmine import RedmineActiveResource
	# Setting the API key for the active resource to use.
	RedmineActiveResource._site = settings['redmine_url']
	RedmineActiveResource._user = settings['api_key']
	try:
		# Fetch all the redmine users with iCal URLs sat.
		users = user_fetcher.fetch(settings)
		print "Found %u user(s) in Redmine, with the iCal Feed URL sat." % len(users)
		for user in users:
			print "Processing %s" % user.login
	except pyactiveresource.connection.UnauthorizedAccess as err:
		log.error("Unauhorized access to Redmine, are you sure the api_key" +
			" in the settings file belongs to an administrator? %s" % err)

if __name__ == '__main__':
	main()