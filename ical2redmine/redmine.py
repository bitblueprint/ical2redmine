'''Implements all the redmine active resources needed for this tool.'''
# We need the pyactiverecord module.
from pyactiveresource.activeresource import ActiveResource
#from pyactiveresource import formats

class RedmineActiveResource(ActiveResource):
	'''Active resource for a general Redmine entity'''
	_site = None
	_user = None
	def get_custom_field_value(self, custom_field_id):
		'''Get the value of a custom field on the resource.'''
		if "custom_fields" in self.to_dict().keys():
			for field in self.custom_fields:
				#print type(field.attributes)
				if int(field.id) == int(custom_field_id):
					return field.value
			return None

class TimeEntries(RedmineActiveResource):
	'''A time entity's active resource'''
	_singular = 'time_entry'
	_since = None
	
	# Changing the default values.
	def to_xml(self, root=None, header=True, pretty=False, dasherize=False):
		return super(TimeEntries, self).to_xml(root=root, header=header,
			pretty=pretty, dasherize=dasherize)

	def created_by_ical2redmine(self, custom_time_entry_field_id):
		'''Was this time entity created by this tool?'''
		return self.get_custom_field_value(custom_time_entry_field_id) is not None

class Users(RedmineActiveResource):
	'''A user's active resource'''
	_singular = 'user'