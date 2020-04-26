from django.db import models


# Create your models here.

class Trigger(models.Model):
    trigger_name = models.CharField(max_length=50)
    trigger_data = models.CharField(max_length=10)
    trigger_date = models.DateTimeField(auto_now=True)

    @classmethod
    def create(cls, trigger_name, trigger_data):
        trigger = cls(trigger_name=trigger_name, trigger_data=trigger_data)
        return trigger


class TriggerLog(models.Model):
    trigger_name = models.CharField(max_length=50)
    trigger_data = models.CharField(max_length=10)
    trigger_date = models.DateTimeField(auto_now=True)

    @classmethod
    def create(cls, trigger_name, trigger_data):
        triggerlog = cls(trigger_name=trigger_name, trigger_data=trigger_data)
        return triggerlog


class Log(models.Model):
    log_severity = models.CharField(max_length=50)
    log_date = models.DateTimeField(auto_now_add=True, blank=True)
    log_data = models.CharField(max_length=256)

    @classmethod
    def create(cls, log_severity, log_date, log_data):
        log = cls(log_severity=log_severity, log_date=log_date, log_data=log_data)
        return log


class Privilege(models.Model):
    privilege_name = models.CharField(max_length=50)
    privilege_ID = models.IntegerField(default=0)

    @classmethod
    def create(cls, privilege_name, privilege_ID):
        privilege = cls(privilege_name=privilege_name, privilege_ID=privilege_ID)
        return privilege


class Contact(models.Model):
    contact_nom = models.CharField(max_length=50)
    contact_prenom = models.CharField(max_length=50)
    contact_phonenumber = models.CharField(max_length=50, default="000000000000")
    contact_privilege = models.ForeignKey(Privilege, on_delete=models.CASCADE)

    @classmethod
    def create(cls, contact_nom, contact_prenom, contact_phonenumber, contact_privilege):
        contact = cls(contact_nom=contact_nom, contact_prenom=contact_prenom, contact_phonenumber=contact_phonenumber,
                      contact_privilege=contact_privilege)
        return contact


def get_model_fields(model):
    return model._meta.fields
