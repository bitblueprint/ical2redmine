'''This modules sends out emails with summeries.'''
from ical2redmine.logger import LOG as log
# Import smtplib for the actual sending function
import smtplib
# Import the email modules we'll need
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ical2redmine import destinator

def event2str(an_event):
	'''Converts an event to a string'''
	result = "'%s'" % an_event.get('SUMMARY')
	start_dt_string = an_event.get('DTSTART').dt.strftime("%Y-%m-%d %H:%M")
	result += " starting %s " % start_dt_string
	return result

def get_error_message(err, style='simple'):
	'''Converts an error to a message'''
	if style == "html":
		result = "<b>%s</b>" % err['exp']
	else:
		result = "%s" % err['exp']
	result += ": "
	result += "Entry for event %s" % event2str(err['event'])
	result += "referencing issue #%u" % int(err['issue_id'])
	result += ", couldn't be %s" % err['destiny']
	return result

def send(summary_report, user, settings):
	'''Send a summary to the user.'''
	log.info("A summary should be sent to the user!")
	simple_lines = []
	html_lines = []
	simple_lines.append("A message from the ical2redmine robot at %s" %
		settings['redmine_url'])
	link = "<a href='%s'>%s</a>" % (settings['redmine_url'],
		settings['redmine_url'])
	html_lines.append("A message from the ical2redmine robot at %s" % link)
	if summary_report[destinator.DESTINY_CREATE] > 0:
		simple_lines.append("Entries created: %u" %
			summary_report[destinator.DESTINY_CREATE])
		html_lines.append("<p>Entries created: %u</p>" %
			summary_report[destinator.DESTINY_CREATE])
	if summary_report[destinator.DESTINY_UPDATE] > 0:
		simple_lines.append("Entries updated: %u" %
			summary_report[destinator.DESTINY_UPDATE])
		html_lines.append("<p>Entries updated: %u</p>" %
			summary_report[destinator.DESTINY_UPDATE])
	if summary_report[destinator.DESTINY_DELETE] > 0:
		simple_lines.append("Entries deleted: %u" %
			summary_report[destinator.DESTINY_DELETE])
		html_lines.append("<p>Entries deleted: %u</p>" %
			summary_report[destinator.DESTINY_DELETE])
	if len(summary_report["recurring_events"]) > 0:
		simple_lines.append("Recurring events found: %u." %
			len(summary_report["recurring_events"]))
		html_lines.append("<p>Recurring events found: %u.</p>" %
			len(summary_report["recurring_events"]))
		html_lines.append("<ul>")
		for uid, recurring_event in summary_report["recurring_events"].items():
			simple_lines.append("- %s" % event2str(recurring_event[0]) )
			html_lines.append("<li>%s</li>" % event2str(recurring_event[0]) )
		html_lines.append("</ul>")
		simple_lines.append("Recurring events are not supported!")
		html_lines.append("<p><b>Recurring events are not supported!</b></p>")
	if len(summary_report['errors']) > 0:
		simple_lines.append("%u errors occured: " % len(summary_report['errors']))
		html_lines.append("%u errors occured: " % len(summary_report['errors']))
		html_lines.append("<ul>")
		for err in summary_report['errors']:
			simple_lines.append("- %s" % get_error_message(err, 'simple') )
			html_lines.append("<li>%s</li>" % get_error_message(err, 'html') )
		html_lines.append("</ul>")

	msg = MIMEMultipart('alternative')
	msg['Subject'] = settings['mail_summary_subject']
	msg['From'] = settings['mail_from']
	msg['To'] = user.mail
	# Create the body of the message (a plain-text and an HTML version).
	simple_message = "\n".join(simple_lines)
	html_message = """\
	<html>
	  <head></head>
	  <body>
	    %s
	  </body>
	</html>
	""" % "\n".join(html_lines)
	# Record the MIME types of both parts - text/plain and text/html.
	msg.attach( MIMEText(simple_message.encode('utf-8'), 'plain', 'utf-8') )
	msg.attach( MIMEText(html_message.encode('utf-8'), 'html', 'utf-8') )
	log.debug("=== Sending mail to %s ===\n\t%s\n=== END OF MESSAGE ===", msg['To'], "\n\t".simple_message.split("\n"))
	smtp = smtplib.SMTP_SSL(settings['mail_smtp_host'])
	smtp.login(settings['mail_smtp_user'], settings['mail_smtp_password'])
	response = smtp.sendmail(msg['From'], msg['To'], msg.as_string())
	smtp.quit()
	return len(response) == 0