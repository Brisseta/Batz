import json
import os
import threading
from datetime import date

import huaweisms.api.sms
import huaweisms.api.user
import huaweisms.api.wlan

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Batz.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
import Batz_API.models

content_global = ""
user_in_db_global = 1
with open('ressouces.json', 'r') as f:
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
        try:
            ctx = huaweisms.api.user.quick_login("admin", "admin")
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


def GetSMS():
    # -*-coding:Latin-1 -*
    ctx = huaweisms.api.user.quick_login("admin", "admin")

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
    ctx = huaweisms.api.user.quick_login("admin", "admin")

    # reading sms
    count = huaweisms.api.sms.sms_count(
        ctx
    )
    return count['response']['LocalUnread']


def ClearSms(sms_index):
    # -*-coding:Latin-1 -*
    ctx = huaweisms.api.user.quick_login("admin", "admin")

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
    return result


if __name__ == '__main__':
    while 1 < 2:  # infinite loop
        local_unread = int(GetSMSCount())
        if local_unread != 0:
            getsms = GetSMS()  # crée un thread pour le get
            content = getsms['content']
            is_authent = getsms['authent']
            number = getsms['number']
            index = int(getsms['index'])
            ClearSms(index)
            # --------------- DEBUT DU TRAITEMENT DU GET --------------------------- #

            if ressource_json['CMD_DEFAULT'] in content and is_authent == 0:
                if ressource_json['GET_VIEW'] in content:
                    # send sms display
                    event_du_send = threading.Event()  # on crée un objet de type Event
                    event_du_send.clear()  # simple clear de précaution
                    thread_du_send = SendSMS(event_du_send, number,
                                             build_get_view(number))  # crée un thread pour le get
                    thread_du_send.start()  # démarre le thread,
                    event_du_send.wait()  # on attend la fin du get
                if ressource_json['SET_CHAUFFAGE'] in content:
                    if ressource_json['CHAUFFAGE_ON'] in content:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, number,
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_ON']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if ressource_json['CHAUFFAGE_OFF'] in content:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, number,
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_OFF']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if ressource_json['CHAUFFAGE_AUTO'] in content:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, number,
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_AUTO']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                if ressource_json['GET_LOG'] in content:
                    # send sms log all
                    if "info" in content:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, number,
                                                 build_get_log("INFO"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if "warning" in content:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, number,
                                                 build_get_log("WARNING"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if "error" in content:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(event_du_send, number,
                                                 build_get_log("ERROR"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
