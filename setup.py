from setuptools import setup

setup(
   name='p1_to_mqtt',
   version='1.0',
   description='P1 to MQTT process',
   author='Gerben van Eerten',
   author_email='info@gerbenvaneerten.nl',
   packages=['p1_to_mqtt'],
   install_requires=['pytz', 'pyserial', 'paho-mqtt'],
)
