import os
import time
from typing import Any

import win32timezone
from rest_framework.utils import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Batz.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
import Batz_API
from Batz_API.Common import just_log
from Batz_API.models import Trigger, TriggerLog

with open('../ressouces.json', 'r') as f:
    ressource_json = json.load(f)


class AutoMode:
    def __init__(self):
        self.triggers = Batz_API.models.Trigger.objects
        self.relai1_obj = self.triggers.get(trigger_name='relai1')
        self.relai2_obj = self.triggers.get(trigger_name='relai2')
        self.thermostat_obj = self.triggers.get(trigger_name='termostat')
        self.timer1_obj = self.triggers.get(trigger_name='timer1')
        self.timer2_obj = self.triggers.get(trigger_name='timer2')
        self.chauffage_status_obj = self.triggers.get(trigger_name='chauffage')

    def start(self):
        while self.chauffage_status_obj.trigger_data == 'AUTO':
            self.checkup()
            self.refresh()
        self.stop()
        # notify at the end  TODO

    def refresh(self):
        self.print_status()
        self.relai1_obj = self.triggers.get(trigger_name='relai1')
        self.relai2_obj = self.triggers.get(trigger_name='relai2')
        self.thermostat_obj = self.triggers.get(trigger_name='termostat')
        self.timer1_obj = self.triggers.get(trigger_name='timer1')
        self.timer2_obj = self.triggers.get(trigger_name='timer2')
        self.chauffage_status_obj = self.triggers.get(trigger_name='chauffage')
        self.commit()
        self.background_poller_wait()

    def stop(self):
        self.timer1_obj.trigger_data = "OFF"
        self.save()

    # notify at the end  TODO
    def save(self):
        self.relai1_obj.save(force_update=True)
        self.relai2_obj.save(force_update=True)
        self.chauffage_status_obj.save(force_update=True)
        self.thermostat_obj.save(force_update=True)
        self.triggers.all().update(trigger_date=win32timezone.now())

    def background_timer(self):
        # sleep till the end of TIMER1
        print("Sleeping for %d Hours" % int(ressource_json['TIMER_HOURS']))
        time.sleep(int(ressource_json['TIMER_HOURS']) * 60 * 60)
        self.timer1_obj.trigger_data = "OFF"

    def background_poller_wait(self):
        # sleep till the end of TIMER1
        print("Sleeping for %d Minutes" % int(ressource_json['POLLER_UPDATE_MINUTE']))
        time.sleep(int(ressource_json['POLLER_UPDATE_MINUTE']) * 60)
        self.timer2_obj.trigger_data = "OFF"

    def print_status(self):
        print_res = {"relai1": self.relai1_obj.trigger_data, "relai2": self.relai2_obj.trigger_data,
                     "thermostat": self.thermostat_obj.trigger_data, "timer1": self.timer1_obj.trigger_data}
        print("Status on %s" % win32timezone.now().strftime("%d/%m/%Y %H:%M:%S"))
        for status in print_res.items():
            print(status)

    def commit(self):
        for trigger in self.triggers.iterator():
            to_commit = TriggerLog(trigger_name=trigger.__getattribute__("trigger_name"),
                                   trigger_data=trigger.__getattribute__("trigger_data"),
                                   trigger_date=trigger.__getattribute__("trigger_date"))
            to_commit.save()
        print(just_log(
            "sucessfully pushed " + str(sum(1 for _ in self.triggers.iterator())) + " rows to TriggerLog table"))

    def checkup(self):
        # tant que le relai 1 fonctionne et le relai 2 est éteint
        if self.relai1_obj.trigger_data == 'ON' and self.relai2_obj.trigger_data == 'OFF':
            # si le timer est écoulé le termostat se met en marche
            if self.timer1_obj.trigger_data == "OFF" and self.thermostat_obj.trigger_data == "ON":
                # Passe le status du termostat à ON
                self.timer1_obj.trigger_data = 'ON'
                # j'active le relai 2
                self.relai2_obj.trigger_data = 'ON'
                # Lance le timer
                self.background_timer()
                # A la fin du timer je désactive le relai 2 et passe le termostat à OFF
                if self.thermostat_obj.trigger_data is "ON":
                    self.thermostat_obj.trigger_data = "OFF"
                    self.relai2_obj.trigger_data = "OFF"

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)

    def __getattribute__(self, name: str) -> Any:
        return super().__getattribute__(name)


if __name__ == '__main__':
    temp = AutoMode()
    temp.start()
    temp.stop()
