from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = (
        ("ADMIN", "Администратор"),
        ("REGISTRAR", "Регистратор"),
        ("DOCTOR", "Врач"),
        ("PATIENT", "Пациент"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="PATIENT")

    def __str__(self):
        return f"{self.username} ({self.role})"


class Specialization(models.Model):
    spec_id = models.AutoField(primary_key=True, db_column="spec_id")
    spec_title = models.CharField(max_length=100, db_column="spec_title")

    class Meta:
        db_table = "specialization"


class Department(models.Model):
    dep_id = models.AutoField(primary_key=True, db_column="dep_id")
    dep_title = models.CharField(max_length=100, db_column="dep_title")
    name_of_manager = models.CharField(
        max_length=100, db_column="name_of_manager", null=True
    )

    class Meta:
        db_table = "department"


class Room(models.Model):
    room_id = models.AutoField(primary_key=True, db_column="room_id")
    room_number = models.IntegerField(unique=True, db_column="room_number")
    equipment = models.CharField(max_length=250, db_column="equipment", null=True)

    class Meta:
        db_table = "room"


class Disease(models.Model):
    disease_id = models.AutoField(primary_key=True, db_column="disease_id")
    disease_code = models.CharField(unique=True, db_column="disease_code")
    disease_title = models.CharField(max_length=100, db_column="disease_title")

    class Meta:
        db_table = "disease"


class Drug(models.Model):
    drug_id = models.AutoField(primary_key=True, db_column="drug_id")
    drug_title = models.CharField(max_length=100, db_column="drug_title")
    drug_type = models.CharField(max_length=100, db_column="drug_type")

    class Meta:
        db_table = "drug"


class Prescription(models.Model):
    pres_id = models.AutoField(primary_key=True, db_column="pres_id")
    recommendations = models.TextField(db_column="recommendations")

    class Meta:
        db_table = "prescription"


class PrescriptionDrug(models.Model):
    id = models.AutoField(primary_key=True)

    pres_id = models.ForeignKey(
        "Prescription",
        on_delete=models.CASCADE,
        db_column="pres_id",
        related_name="prescription_drugs",
    )

    drug_id = models.ForeignKey(
        "Drug",
        on_delete=models.PROTECT,
        db_column="drug_id",
        related_name="prescribed_in",
    )

    dosage = models.CharField(
        max_length=100,
        db_column="dosage",
        help_text="Например: '500 мг 3 раза в день после еды, 7 дней'",
    )

    class Meta:
        db_table = "pres_composition"
        unique_together = ("pres_id", "drug_id")

    def __str__(self):
        return f"Рецепт №{self.pres_id_id} - {self.drug_id.drug_title} ({self.dosage})"


class Patient(models.Model):
    card_number = models.AutoField(primary_key=True, db_column="card_number")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_profile",
        db_column="user_id",
    )
    patient_name = models.CharField(max_length=100, db_column="patient_name")
    birth_date = models.DateField(db_column="birth_date")
    address = models.TextField(db_column="address", null=True)
    insurance = models.CharField(
        max_length=16, unique=True, db_column="insurance", null=True
    )

    class Meta:
        db_table = "patient"


class Doctor(models.Model):
    doctor_id = models.AutoField(primary_key=True, db_column="doctor_id")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
        db_column="user_id",
    )
    doctor_name = models.CharField(max_length=100, db_column="doctor_name")
    spec = models.ForeignKey(
        Specialization, on_delete=models.PROTECT, db_column="spec_id"
    )
    dep = models.ForeignKey(Department, on_delete=models.PROTECT, db_column="dep_id")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, db_column="room_id")

    class Meta:
        db_table = "doctor"


class ReceptionLog(models.Model):
    log_id = models.AutoField(primary_key=True, db_column="log_id")
    doctor_id = models.ForeignKey(
        Doctor, on_delete=models.PROTECT, db_column="doctor_id"
    )
    patient_id = models.ForeignKey(
        Patient, on_delete=models.PROTECT, db_column="patient_id"
    )
    disease_id = models.ForeignKey(
        Disease, on_delete=models.PROTECT, db_column="disease_id"
    )
    pres_id = models.ForeignKey(
        Prescription, on_delete=models.PROTECT, db_column="pres_id"
    )

    appointment_date = models.DateTimeField(db_column="appointment_date")
    STATUS_CHOICES = (
        ("BOOKED", "Запланирована"),
        ("CANCELLED", "Запись отменена"),
        (
            "NO_SHOW",
            "Неявка пациента",
        ),
        ("COMPLETED", "Завершен"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="BOOKED", db_column="status"
    )
    complains = models.TextField(db_column="complains")

    class Meta:
        db_table = "reception_log"


class DoctorSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True, db_column="schedule_id")
    doctor = models.ForeignKey(
        "Doctor",
        on_delete=models.CASCADE,
        related_name="schedules",
        db_column="doctor_id",
    )
    date = models.DateField(db_column="schedule_date")
    start_time = models.TimeField(db_column="start_time")
    end_time = models.TimeField(db_column="end_time")

    class Meta:
        db_table = "schedule"
        unique_together = ("doctor", "date")
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"График: {self.doctor.doctor_name} на {self.date} ({self.start_time}-{self.end_time})"


class TimeSlot(models.Model):
    slot_id = models.AutoField(primary_key=True, db_column="slot_id")
    doctor = models.ForeignKey(
        "Doctor",
        on_delete=models.CASCADE,
        related_name="time_slots",
        db_column="doctor_id",
    )
    start_datetime = models.DateTimeField(db_column="start_datetime")
    end_datetime = models.DateTimeField(db_column="end_datetime")
    is_booked = models.BooleanField(default=False, db_column="is_booked")

    class Meta:
        db_table = "time_slot"
        unique_together = ("doctor", "start_datetime")
        ordering = ["start_datetime"]

    def __str__(self):
        status_str = "Занят" if self.is_booked else "Свободен"
        return f"{self.doctor.doctor_name} | {self.start_datetime.strftime('%Y-%m-%d %H:%M')} [{status_str}]"
