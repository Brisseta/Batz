import os
import threading
from datetime import date
import time
# import RPi.GPIO as GPIO
import multiprocessing as mp

import huaweisms.api.sms
import huaweisms.api.user
import huaweisms.api.wlan
import win32timezone
from rest_framework.utils import json

# from w1thermsensor import W1ThermSensor
# from w1thermsensor import W1ThermSensor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Batz.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
import Batz_API
from Batz_API import models
from Batz_API.models import TriggerLog

with open('../ressouces.json', 'r') as f:
    ressource_json = json.load(f)

my_AutoMode = None


def check_for_alert():
    # pompe_status = BinaryInput(gpio=ressource_json['POMPE_CTRL_PIN'], lib="pompe")
    # pompe_status.run()
    # if pompe_status.state == 1:
    #     change_trigger_status("pompe", value=1)
    # else:
    #     change_trigger_status("pompe", value=0)
    # secteur_status = BinaryInput(gpio=ressource_json['SECTEUR_CTRL_PIN'], lib='secteur')
    # secteur_status.run()
    # if secteur_status.state == 1:
    #     change_trigger_status("secteur", value=1)
    # else:
    #     change_trigger_status("secteur", value=0)
    if get_trigger_data("was_alerted") == 'FALSE' and get_trigger_data('status') == 'ERROR':
        if get_trigger_data('pompe') == "1":
            #             TODO send inondation alert
            print(just_log("innondation detectée"))
            change_trigger_status("was_alerted", value="TRUE")
        elif get_trigger_data('pompe') == "0":
            #             TODO send fin inondation alert
            print(just_log("fin innondation"))
            change_trigger_status("was_alerted", value="FALSE")
            change_trigger_status("status", value="NONE")
        if get_trigger_data("secteur") == "0":
            #             TODO send secteur fault alert
            print(just_log("coupure courant detectée"))
            change_trigger_status("was_alerted", value="TRUE")
        elif get_trigger_data("secteur") == "1":
            #             TODO send secteur fault alert
            print(just_log("Fin de coupure courant "))
            change_trigger_status("was_alerted", value="FALSE")
            change_trigger_status("status", value="NONE")


def just_log(some_text):
    return win32timezone.now().strftime("%d/%m/%Y %H:%M:%S") + " : " + some_text


def do_check_temp():
    CheckTemperature()
    print(just_log("Getting temperature done"))


def change_to_off_mode():
    if get_trigger_data(trigger_name='chauffage') == 'AUTO' and my_AutoMode is not None:
        my_AutoMode.stop()
    change_trigger_status(trigger_name='relai1', value='OFF')
    change_trigger_status(trigger_name='relai2', value='OFF')
    Batz_API.Common.BinaryOutput(gpio=ressource_json['RELAI1_CTRL_PIN'], state=0, lib="relai1").run()
    Batz_API.Common.BinaryOutput(gpio=ressource_json['RELAI2_CTRL_PIN'], state=0, lib="relai2").run()


def change_to_on_mode():
    if get_trigger_data(trigger_name='chauffage') == 'AUTO' and my_AutoMode is not None:
        my_AutoMode.stop()
    change_trigger_status(trigger_name='relai1', value='ON')
    change_trigger_status(trigger_name='relai2', value='ON')
    Batz_API.Common.BinaryOutput(gpio=ressource_json['RELAI1_CTRL_PIN'], state=1, lib="relai1").run()
    Batz_API.Common.BinaryOutput(gpio=ressource_json['RELAI2_CTRL_PIN'], state=1, lib="relai2").run()


def change_to_auto_mode():
    from Batz_API.autoMode import AutoMode
    pool = mp.Pool(processes=1)
    process = AutoMode()
    pool.apply_async(process.start(), )
    pool.terminate()


def commit(trigger):
    to_commit = TriggerLog(trigger_name=trigger.__getattribute__("trigger_name"),
                           trigger_data=trigger.__getattribute__("trigger_data"),
                           trigger_date=trigger.__getattribute__("trigger_date"))
    to_commit.save()


def change_trigger_status(trigger_name, value):
    trigger = models.Trigger.objects.get(trigger_name=trigger_name)
    trigger.trigger_data = value
    trigger.save(force_update=True)
    commit(trigger)


def get_trigger_data(trigger_name):
    trigger = models.Trigger.objects.get(trigger_name=trigger_name)
    return trigger.trigger_data


class CheckTemperature():
    """  Supported sensors are:
        * DS18S20
        * DS1822
        * DS18B20
        * DS1825
        * DS28EA00
        * MAX31850K

    Supported temperature units are:
        * Kelvin
        * Celsius
        * Fahrenheit
    """

    def __init__(self):
        self.name = "CheckTemp"
        self.sensors = []

    def run(self):
        """Lance le check status en tâche de fond """
        # for sensor in W1ThermSensor.get_available_sensors():
        #     self.sensors.append({"type": sensor.type, "id": sensor.id, "name": self.identify(sensor.id),
        #                          "value": sensor.get_temperature()})
        #     print("Sensor %s has temperature %.2f" % (sensor.id, sensor.get_temperature()))
        if self.is_below_trigger(trigger_name='interieur') and get_trigger_data('chauffage') == 'AUTO':
            change_trigger_status(trigger_name='timer2', value='ON')
        elif self.is_above_trigger(trigger_name='interieur') and get_trigger_data(
                trigger_name='timer2') == 'ON' and get_trigger_data("chauffage") == "AUTO":
            change_trigger_status(trigger_name='timer2', value='OFF')
        self.notify()

    def identify(self, sensor_id):
        for label in ressource_json:
            if ressource_json[str(label)] == sensor_id:
                return str(label).split('_')[0].lower()

    def is_above_trigger(self, trigger_name):
        to_compare = models.TriggerLog.objects.filter(trigger_name=trigger_name)[0]
        trigger = models.Trigger.objects.filter(trigger_name=trigger_name)[0]
        return float(to_compare.trigger_data) > float(trigger.trigger_data)

    def is_below_trigger(self, trigger_name):
        return not self.is_above_trigger(trigger_name)

    def notify(self):
        """stocke le résultat en BDD dans la table triggerLog"""
        print(just_log("Results for %d sensors" % sum(1 for _ in self.sensors)))
        for sensor in self.sensors:
            print(just_log("sensor %s %s %s"), sensor['name'], sensor['type'], sensor['value'])
            try:
                new_trigger = models.TriggerLog(trigger_name=sensor['name'], trigger_data=sensor['value'])
                new_trigger.save(force_insert=True)
            except:
                print(just_log("Unrecognised sensor name") % sensor['name'])


class BinaryInput(threading.Thread):

    def __init__(self, event, gpio, lib):
        threading.Thread.__init__(self)
        self.name = "BinaryInput"
        self.event = event
        self.gpio = gpio
        self.lib = lib
        self.state = ''

    def run(self):
        # self.setmode(GPIO.BCM)
        # GPIO.setup(self.gpio,GPIO.IN)
        # if GPIO.input(self.gpio) == True
        #     self.state = 'ON'
        # elif GPIO.input(self.gpio) == False
        #     self.state = 'OFF'
        # time.sleep(1)
        self.notify()
        self.event.set()

    def notify(self):
        event_du_log = threading.Event()  # on crée un objet de type Event
        event_du_log.clear()  # simple clear de précaution
        thread_du_log = SendToLog(event_du_log, severity="INFO",
                                  content=just_log("Got state " + self.state + " for " + self.lib))
        thread_du_log.start()  # démarre le thread,
        event_du_log.wait()  # on attend la fin du get
        #         Testing
        print(just_log("Got state  " + self.state + " for " + self.lib))


class BinaryOutput(threading.Thread):

    def __init__(self, gpio, state, lib):
        threading.Thread.__init__(self)
        self.name = "BinaryOutput"
        self.gpio = gpio
        self.state = state
        self.lib = lib

    def run(self):
        # GPIO.cleanup()
        # self.setmode(GPIO.BCM)
        # GPIO.setup(self.gpio,GPIO.OUT)
        # if self.state == 0:
        #     GPIO.output(self.gpio,GPIO.LOW)
        # elif self.state == 1
        #     GPIO.output(self.gpio, GPIO.HIGH)
        # time.sleep(1)
        # GPIO.cleanup()
        self.notify()
        # self.event.set()

    def notify(self):
        event_du_log = threading.Event()  # on crée un objet de type Event
        event_du_log.clear()  # simple clear de précaution
        thread_du_log = SendToLog(event_du_log, severity="INFO",
                                  content=just_log("Set state to " + str(self.state) + " for " + self.lib))
        thread_du_log.start()  # démarre le thread,
        event_du_log.wait()  # on attend la fin du get
        #         Testing
        print(just_log("Set state to " + str(self.state) + " for " + self.lib))


class SendSMS(threading.Thread, ):
    def __init__(self, connetivity_context, event, contact, text):  # event = objet Event
        threading.Thread.__init__(self)  # = donnée supplémentaire
        self.name = "SendSMS"
        self.connetivity_context = None
        self.event = event  # on garde un accès à l'objet Event
        self.contact = contact
        self.text = text
        self.connectivity = connetivity_context

    def run(self, ):
        # -*-coding:Latin-1 -*
        if not self.connetivity_context:
            print(just_log("SENDSMS function failed because 4G dongle cannot be reached"))
        else:
            try:
                ctx = huaweisms.api.user.quick_login("admin", ressource_json["MODEM_PASSWD"])
                try:
                    # sending sms
                    huaweisms.api.sms.send_sms(
                        ctx, Batz_API.models.Contact.objects.get(
                            contact_phonenumber=self.contact).contact_phonenumber,
                        self.text
                    )
                    event_du_log = threading.Event()  # on crée un objet de type Event
                    event_du_log.clear()  # simple clear de précaution
                    thread_du_log = SendToLog(event_du_log, severity="INFO",
                                              content="sending to" + Batz_API.models.Contact.objects.get(
                                                  contact_phonenumber=self.contact).contact_phonenumber + " \n text : " + self.text)
                    thread_du_log.start()  # démarre le thread,
                    event_du_log.wait()  # on attend la fin du get
                except EOFError:
                    print("Error")
            except ConnectionError:
                event_du_log = threading.Event()  # on crée un objet de type Event
                event_du_log.clear()  # simple clear de précaution
                thread_du_log = SendToLog(event_du_log, severity="ERROR", content=
                "Connection au dongle interrompue")
                thread_du_log.start()  # démarre le thread,
                event_du_log.wait()  # on attend la fin du get

        self.event.set()


class SendToLog(threading.Thread, ):
    def __init__(self, event, severity, content):  # event = objet Event
        threading.Thread.__init__(self)  # = donnée supplémentaire
        self.name = "SendToLog"
        self.event = event  # on garde un accès à l'objet Event
        self.severity = severity
        self.content = content

    def run(self):
        tempLog = Batz_API.models.Log.create(log_severity=self.severity, log_date=date.today(), log_data=self.content)
        tempLog.save()
        self.event.set()


if __name__ == '__main__':
    check = CheckTemperature()
    check.identify("000155689")
    try:
        matched_trigger = models.Trigger.objects.get(trigger_name='toto')
    except:
        print("error")
