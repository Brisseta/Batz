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

    def __init__(self, param1, param2, ):
        threading.Thread.__init__(self)
        self.param1 = param1
        self.param2 = param2
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
            print(ctx)
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
                print("toto")
        except ConnectionError:
            event_du_log = threading.Event()  # on crée un objet de type Event
            event_du_log.clear()  # simple clear de précaution
            thread_du_log = SendToLog(event_du_log, severity="ERROR", content=
            "Connection au dongle interrompue")
            thread_du_log.start()  # démarre le thread,
            event_du_log.wait()  # on attend la fin du get

        # output: <ApiCtx modem_host=192.168.8.1>
        self.event.set()


def GetSMS():
    # -*-coding:Latin-1 -*
    ctx = huaweisms.api.user.quick_login("admin", "admin")
    print(ctx)
    # output: <ApiCtx modem_host=192.168.8.1>

    # reading sms
    messages = huaweisms.api.sms.get_sms(
        ctx
    )
    temp = dict()
    temp['authent'] = userInDB(messages)
    temp['content'] = getContent(messages)
    temp['number'] = getNumber(messages)
    print(temp)
    return temp


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
    response = ""
    response += ressource_json['Bonjour'] + " "
    response += contacts.get(contact_phonenumber=number).contact_prenom
    response += "\n"
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


if __name__ == '__main__':
    getsms = GetSMS()  # crée un thread pour le get
    content = getsms['content']
    is_authent = getsms['authent']
    number = getsms['number']

    # --------------- DEBUT DU TRAITEMENT DU GET --------------------------- #

    if ressource_json['CMD_DEFAULT'] in content and is_authent == 0:
        if ressource_json['GET_VIEW'] in content:
            # send sms display
            event_du_send = threading.Event()  # on crée un objet de type Event
            event_du_send.clear()  # simple clear de précaution
            thread_du_send = SendSMS(event_du_send, number, build_get_view(number))  # crée un thread pour le get
            thread_du_send.start()  # démarre le thread,
            event_du_send.wait()  # on attend la fin du get

        if ressource_json['GET_LOG'] in content:
            # send sms log all
            if "info" in content:
                event_du_send = threading.Event()  # on crée un objet de type Event
                event_du_send.clear()  # simple clear de précaution
                thread_du_send = SendSMS(event_du_send, number, build_get_log("INFO"))  # crée un thread pour le get
                thread_du_send.start()  # démarre le thread,
                event_du_send.wait()  # on attend la fin du get
            if "warnning" in content:
                print("warn")
            if "error" in content:
                print("error")
