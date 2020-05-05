import json
import os
import platform  # For getting the operating system name
import subprocess  # For executing a shell command
import threading

import huaweisms.api.sms
import huaweisms.api.user
import huaweisms.api.wlan

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Batz.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
import Batz_API.models
from Batz_API.Common import just_log, SendSMS, SendToLog, check_for_alert

global connetivity_context
content_global = ""
user_in_db_global = 1
global automode_status
automode_status = False
with open('../ressouces.json', 'r') as f:
    ressource_json = json.load(f)


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
    response += ressource_json['CAPTEUR_EXT'] + str(Batz_API.Common.get_trigger_data(
        trigger_name=ressource_json['CAPTEUR_EXT_LIB']).lower()) + ressource_json['Celsus'] + "\n"
    response += ressource_json['CAPTEUR_INT'] + str(Batz_API.Common.get_trigger_data(
        trigger_name=ressource_json['CAPTEUR_INT_LIB'])) + ressource_json['Celsus'] + "\n"
    response += ressource_json['CAPTEUR_RAD'] + str(Batz_API.Common.get_trigger_data(
        trigger_name=ressource_json['CAPTEUR_RAD_LIB'])) + ressource_json['Celsus'] + "\n"
    response += ressource_json['CHAUFFAGE'] + Batz_API.Common.get_trigger_data(
        trigger_name=ressource_json['CHAUFFAGE_LIB']) + "\n"
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


def build_command_change(trigger_name, set_value):
    triggers = Batz_API.models.Trigger.objects
    trigger_last_value = triggers.get(trigger_name=trigger_name).trigger_data
    result = ressource_json['STATUS_CHANGEMENT'] + "pour " + trigger_name
    result += ressource_json['STATUS_CHANGEMENT_PREVIOUS'] + trigger_last_value + " "
    result += ressource_json['STATUS_CHANGEMENT_CURRENT'] + set_value + "\n"
    print(just_log("Update on " + trigger_name + " /last value : " + trigger_last_value + " /new value : " + set_value))
    return result


if __name__ == '__main__':

    while 1 < 2:  # infinite loop
        connetivity_context = CheckConnectivity()
        local_unread = int(GetSMSCount())
        Batz_API.Common.check_for_alert()
        if local_unread != 0:
            getsms = GetSMS()  # crée un thread pour le get
            # --------------- DEBUT DU TRAITEMENT DU GET --------------------------- #

            if ressource_json['CMD_DEFAULT'] in getsms['content'] and getsms['authent'] == 0:
                if ressource_json['GET_VIEW'] in getsms['content']:
                    # send sms display
                    event_du_send = threading.Event()  # on crée un objet de type Event
                    event_du_send.clear()  # simple clear de précaution
                    thread_du_send = SendSMS(connetivity_context, event_du_send, getsms['number'],
                                             build_get_view(getsms['number']))  # crée un thread pour le get
                    thread_du_send.start()  # démarre le thread,
                    event_du_send.wait()  # on attend la fin du get
                if ressource_json['SET_CHAUFFAGE'] in getsms['content']:
                    if ressource_json['CHAUFFAGE_ON'] in getsms['content'].upper():
                        Batz_API.Common.change_to_on_mode()
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(connetivity_context, event_du_send, getsms['number'],
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_ON']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                        Batz_API.Common.change_trigger_status(trigger_name='chauffage', value='ON')
                    if ressource_json['CHAUFFAGE_OFF'] in getsms['content'].upper():
                        Batz_API.Common.change_to_off_mode()
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(connetivity_context, event_du_send, getsms['number'],
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_OFF']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                        Batz_API.Common.change_trigger_status(trigger_name='chauffage', value='OFF')

                    if ressource_json['CHAUFFAGE_AUTO'] in getsms['content'].upper():
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(connetivity_context, event_du_send, getsms['number'],
                                                 build_command_change(ressource_json['CHAUFFAGE_LIB'],
                                                                      ressource_json[
                                                                          'CHAUFFAGE_AUTO']))
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                        Batz_API.Common.change_trigger_status("chauffage",value="AUTO")
                        if not automode_status:
                            fallback = Batz_API.Common.change_to_auto_mode()

                        continue

                if ressource_json['GET_LOG'] in getsms['content']:
                    # send sms log all
                    if "info" in getsms['content']:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(connetivity_context, event_du_send, getsms['number'],
                                                 build_get_log("INFO"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if "warning" in getsms['content']:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(connetivity_context, event_du_send, getsms['number'],
                                                 build_get_log("WARNING"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
                    if "error" in getsms['content']:
                        event_du_send = threading.Event()  # on crée un objet de type Event
                        event_du_send.clear()  # simple clear de précaution
                        thread_du_send = SendSMS(connetivity_context, event_du_send, getsms['number'],
                                                 build_get_log("ERROR"))  # crée un thread pour le get
                        thread_du_send.start()  # démarre le thread,
                        event_du_send.wait()  # on attend la fin du get
        break