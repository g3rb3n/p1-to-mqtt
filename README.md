

== Prerequisites ==
- A Pi. Being a RaspberryPi, an OrangePi or something similar.
- A OS. Being Armbian, Raspbian or something similar.
- A TTL to USB converter.
- SSH access to the Pi.

== Change config ==
```
cp config_example.json config.json
vi config.json
```
Fill in your username and paasword for your mqtt server.

== Deploy ==
make/deploy <YOUR_P1_HOST>
