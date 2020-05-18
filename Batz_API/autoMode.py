import os
import datetime
import time
from multiprocessing.context import Process
from typing import Any
from polling import poll, TimeoutException
from rest_framework.utils import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Batz.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
import Batz_API
from Batz_API.Common import just_log
from Batz_API.Main import automode_status
from Batz_API.models import Trigger, TriggerLog

with open('/home/pi/project/Batz/Batz_API/ressouces.json', 'r') as f:
    ressource_json = json.load(f)


class AutoMode(Process):
    def __init__(self):
        super().__init__()
        self.name = "Automode"
        self.triggers = Batz_API.models.Trigger.objects
        self.relai1_obj = self.triggers.get(trigger_name='relai1')
        self.relai2_obj = self.triggers.get(trigger_name='relai2')
        self.thermostat_obj = self.triggers.get(trigger_name='termostat')
        self.timer1_obj = self.triggers.get(trigger_name='timer1')
        self.timer2_obj = self.triggers.get(trigger_name='timer2')
        self.chauffage_status_obj = self.triggers.get(trigger_name='chauffage')

    def start(self):
        automode_status = True
        do_it_again = True
        Batz_API.Common.change_trigger_status(trigger_name='relai1', value='ON')
        while do_it_again:
            self.refresh()
            self.checkup()
            do_it_again = Batz_API.Common.get_trigger_data('chauffage') == 'AUTO'
            try:
                poll(
                    lambda: not do_it_again,
                    step=int(ressource_json["POLLER_UPDATE_MINUTE"]),
                    timeout=int(ressource_json["POLLER_UPDATE_MINUTE"]) * 10)
            except TimeoutException:
                if not do_it_again:
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
        Batz_API.Common.do_check_temp()
        self.commit()

    def stop(self):
        Batz_API.Common.change_trigger_status("timer1", value="OFF")
        self.save()
        self.terminate()
        automode_status = False
        print(just_log("Fin du automode"))

    # notify at the end  TODO
    def save(self):
        self.relai1_obj.save(force_update=True)
        self.relai2_obj.save(force_update=True)
        self.chauffage_status_obj.save(force_update=True)
        self.thermostat_obj.save(force_update=True)
        self.triggers.all().update(trigger_date=datetime.datetime.now())

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
        print("Status on %s" % datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
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
        # Batz_API.Common.BinaryInput
        if Batz_API.Common.get_trigger_data("termostat") == "ON":
            Batz_API.Common.change_trigger_status("relai2", value="ON")
            Batz_API.Common.change_trigger_status("timer1", value="ON")
        else:
            if Batz_API.Common.get_trigger_data("termostat") == "OFF" and Batz_API.Common.get_trigger_data(
                    "timer1") == "ON":
                Batz_API.Common.change_trigger_status("relai2", value="ON")
            elif Batz_API.Common.get_trigger_data("termostat") == "OFF":
                Batz_API.Common.change_trigger_status("relai2", value="OFF")
                Batz_API.Common.change_trigger_status("timer1", value="OFF")

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)

    def __getattribute__(self, name: str) -> Any:
        return super().__getattribute__(name)


if __name__ == '__main__':
    temp = AutoMode()
    temp.start()
    temp.stop()
