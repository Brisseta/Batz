import json
import os
import threading
from datetime import date
import platform  # For getting the operating system name
import subprocess  # For executing a shell command

import huaweisms.api.sms
import huaweisms.api.user
import huaweisms.api.wlan
import win32timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Batz.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
import Batz_API.models
from Batz_API.autoMode import AutoMode

global connetivity_context
content_global = ""
user_in_db_global = 1
with open('../ressouces.json', 'r') as f:
    ressource_json = json.load(f)


class CheckTemperature(threading.Thread):

    def __init__(self, room1, room2, room3):
        threading.Thread.__init__(self)
        self.room1 = room1
        self.roo2 = room2
        self.roo3 = room3
        # initialisation de la variable qui portera le résultat
        self.result = None

    def run(self):
        """Lance le check status en tâche de fond et stocke le résultat en BDD dans la table trigger"""

    def result(self):
        """Renvoie le résultat lorsqu'il est connu"""
        return self.result


class SendSMS(threading.Thread, ):
    def __init__(self, event, contact, text):  # event = objet Event
        threading.Thread.__init__(self)  # = donnée supplémentaire
        self.event = event  # on garde un accès à l'objet Event
        self.contact = contact
        self.text = text

    def run(self):
        # -*-coding:Latin-1 -*
        if not connetivity_context:
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


def CheckConnectivity():
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ressource_json['MODEM_IPV4']]
    return subprocess.call(command) == 0


def GetSMS():
    if not connetivity_context:
        print(just_log("GETSMS function failed , working on last SMS content"))
        temp = dict()
        temp['authent'] = 0
        temp['content'] = "Batz set chauffage auto"
        temp['number'] = "0666669261"
        temp['index'] = 12102
        print(just_log("last sms content : "))
        print(temp)
        return temp

    else:
        # -*-coding:Latin-1 -*
        ctx = huaweisms.api.user.quick_login("admin", ressource_json["MODEM_PASSWD"])

        # reading sms
        messages = huaweisms.api.sms.get_sms(
            ctx
        )
        temp = dict()
        temp['authent'] = userInDB(messages)
        temp['content'] = getContent(messages)
        temp['number'] = getNumber(messages)
        temp['index'] = getIndex(messages)
        return temp


def GetSMSCount():
    # -*-coding:Latin-1 -*
    if not connetivity_context:
        print(just_log("GETSMSCOUNT function failed : check if your 4G dongle is online"))
        return 1
    else:

        ctx = huaweisms.api.user.quick_login("admin", ressource_json["MODEM_PASSWD"])

        # reading sms
        count = huaweisms.api.sms.sms_count(
            ctx
        )
        return count['response']['LocalUnread']


def ClearSms(sms_index):
    if not connetivity_context:
        print(just_log("CLEARSMS function failed because 4G dongle cannot be reached"))

    else:
        # -*-coding:Latin-1 -*
        ctx = huaweisms.api.user.quick_login("admin", ressource_json["MODEM_PASSWD"])

        # deleting last sms
        huaweisms.api.sms.delete_sms(
            ctx, sms_index
        )


class SendToLog(threading.Thread, ):
    def __init__(self, event, severity, content):  # event = objet Event
        threading.Thread.__init__(self)  # = donnée supplémentaire
        self.event = event  # on garde un accès à l'objet Event
        self.severity = severity
        self.content = content

    def run(self):
        tempLog = Batz_API.models.Log.create(log_severity=self.severity, log_date=date.today(), log_data=self.content)
        tempLog.save()
        self.event.set()


def getMessagerie(messagerie):
    return messagerie['response']['Messages'].items()


def getIndex(messagerie):
    return messagerie['response']['Messages']['Message'][0]['Index']


def userInDB(message):
    contacts = Batz_API.models.Contact.objects
    try:
        for item in getMessagerie(message):
            if contacts.get(contact_phonenumber="0" + item[1][0]['Phone'][3:]) is not None:
                return 0
            else:
                return 1
    except Batz_API.models.Contact.DoesNotExist:
        event_du_log = threading.Event()  # on crée un objet de type Event
        event_du_log.clear()  # simple clear de précaution
        thread_du_log = SendToLog(event_du_log, severity="INFO", content=
        "<phone> " + getMessagerie(message)[1][0]['Phone'] + " <content> " + getMessagerie(message)[1][0][
            'Content'])
        thread_du_log.start()  # démarre le thread,
        event_du_log.wait()  # on attend la fin du get


def getContent(message):
    for item in getMessagerie(message):
        return item[1][0]['Content']


def getNumber(message):
    for item in getMessagerie(message):
        return "0" + item[1][0]['Phone'][3:]


def build_get_view(number):
    contacts = Batz_API.models.Contact.objects
    triggers = Batz_API.models.Trigger.objects
    response = ressource_json['BATZ_INTRO']
    response += ressource_json['Bonjour'] + " "
    response += contacts.get(contact_phonenumber=number).contact_prenom
    response += "\n"
    if triggers.get(
            trigger_name=ressource_json['STATUS_LIB']).trigger_data == "ERROR":
        response += ressource_json['STATUS_ALERTE_EN_COURS']
    response += ressource_json['CAPTEUR_EXT'] + str(triggers.get(
        trigger_name=ressource_json['CAPTEUR_EXT_LIB']).trigger_data) + ressource_json['Celsus'] + "\n"
    response += ressource_json['CAPTEUR_INT'] + str(triggers.get(
        trigger_name=ressource_json['CAPTEUR_INT_LIB']).trigger_data) + ressource_json['Celsus'] + "\n"
    response += ressource_json['CAPTEUR_RAD'] + str(triggers.get(
        trigger_name=ressource_json['CAPTEUR_RAD_LIB']).trigger_data) + ressource_json['Celsus'] + "\n"
    response += ressource_json['CHAUFFAGE'] + triggers.get(
        trigger_name=ressource_json['CHAUFFAGE_LIB']).trigger_data + "\n"
    return response


def build_get_log(severity):
    logs_in_db = Batz_API.models.Log.objects
    selected_logs = logs_in_db.filter(log_severity=severity).order_by('-log_date')[:ressource_json['LOG_MAX_RESULT']]
    response = ""
    for log in selected_logs:
        response += ressource_json['CROCHET_OUVRANT'] + log.log_severity + ressource_json['CROCHET_FERMANT']
        response += " " + str(log.log_date.day) + " " + str(log.log_date.hour) + ":" + str(
            log.log_date.minute) + ":" + str(
            log.log_date.second) + ">"
        response += log.log_data + "\n"
    return response


def do_trigger_value_change(trigger_name, set_value):
    triggers = Batz_API.models.Trigger.objects
    trigger_last_value = triggers.get(trigger_name=trigger_name)
    trigger_last_value.trigger_data = set_value
    trigger_last_value.save()


def build_command_change(trigger_name, set_value):
    triggers = Batz_API.models.Trigger.objects
    trigger_last_value = triggers.get(trigger_name=trigger_name).trigger_data
    result = ressource_json['STATUS_CHANGEMENT'] + "pour " + trigger_name
    result += ressource_json['STATUS_CHANGEMENT_PREVIOUS'] + trigger_last_value + " "
    result += ressource_json['STATUS_CHANGEMENT_CURRENT'] + set_value + "\n"
    do_trigger_value_change(trigger_name, set_value)
    print(just_log("Update on " + trigger_name + " /last value : " + trigger_last_value + " /new value : " + set_value))
    return result


def just_log(some_text):
    return win32timezone.now().strftime("%d/%m/%Y %H:%M:%S") + " : " + some_text


if __name__ == '__main__':
    while 1 < 2:  # infinite loop
        connetivity_context = CheckConnectivity()
        local_unread = int(GetSMSCount())
        if local_unread != 0:
            getsms = GetSMS()  # crée un thread pour le get
            # --------------- DEBUT DU TRAITEMENT DU GET --------------------------- #

            if ressource_json['CMD_DEFAULT'] in getsms['content'] and getsms['authent'] == 0:
                if ressource_json['GET_VIEW'] in getsms['content']:
                    # send sms display
                    event_du_send = threading.Event()  # on crée un objet de type Event
                    event_du_send.clear()  # simple clear de précaution
                    thread_du_send = SendSMS(event_du_send, getsms['number'],
                                             build_get_view(getsms['number']))  # crée un thread pour le get
                    thread_du_send.start()  # démarre le thread,
                    event_du_send.wait()  # on attend la fin du get
                if ressource_json['SET_CHAUFFAGE'] in getsms['content']:
                    if ressource_json['CHAUFFAGE_ON'] in getsms['content'].upper():
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, getsms['number'],
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_ON']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if ressource_json['CHAUFFAGE_OFF'] in getsms['content'].upper():
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, getsms['number'],
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_OFF']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if ressource_json['CHAUFFAGE_AUTO'] in getsms['content'].upper():
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, getsms['number'],
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_AUTO']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                        autoMode = AutoMode()
                        autoMode.start()

                if ressource_json['GET_LOG'] in getsms['content']:
                    # send sms log all
                    if "info" in getsms['content']:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, getsms['number'],
                                                 build_get_log("INFO"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if "warning" in getsms['content']:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, getsms['number'],
                                                 build_get_log("WARNING"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if "error" in getsms['content']:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, getsms['number'],
                                                 build_get_log("ERROR"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
