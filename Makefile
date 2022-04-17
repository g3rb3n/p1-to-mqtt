PYTHON?=python3

test :
	$(PYTHON) -m pytest --cov=p1_to_mqtt tests/

run :
	$(PYTHON) -m p1_to_mqtt

deploy :
	bash/deploy $REMOTE_USER $REMOTE_HOST $REMOTE_DIST $MQTT_USER $MQTT_PASSWORD $MQTT_HOST

update :
	bash/update $REMOTE_USER $REMOTE_HOST $REMOTE_DIST $MQTT_USER $MQTT_PASSWORD $MQTT_HOST

install :
	$(PYTHON) ./setup.py install

upload : test
	$(PYTHON) ./setup.py sdist upload
