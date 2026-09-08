from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Patient, Doctor

User = get_user_model()


@receiver(post_save, sender=User)
def create_patient_profile(sender, instance, created, **kwargs):
    if created and instance.role == "PATIENT":
        if not hasattr(instance, "patient_profile"):
            Patient.objects.create(
                user=instance,
                patient_name=instance.get_full_name() or instance.username,
                birth_date="2000-01-01",
            )


@receiver(post_save, sender=User)
def create_doctor_profile(sender, instance, created, **kwargs):
    if created and instance.role == "DOCTOR":
        if not hasattr(instance, "doctor_profile"):
            Doctor.objects.create(
                user=instance,
                doctror_name=instance.get_full_name() or instance.username,
                spec_id=1,
                dep_id=1,
                room=1,
            )
