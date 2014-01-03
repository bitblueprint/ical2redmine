from distutils.core import setup

version = '0.3'

setup(name='ical2redmine',
      version=version,
      description='Create/update/remove Redmine time entries from an iCal feed.',
      author='Kraen Hansen',
      author_email='kh@bitblueprint.com',
      url='https://github.com/bitblueprint/ical2redmine',
      packages=['ical2redmine'],
      package_dir={'ical2redmine':'src'},
      license='MIT License',
      platforms=['any'],
      classifiers=[]
    )
