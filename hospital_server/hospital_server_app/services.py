from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from .models import DoctorSchedule, TimeSlot


def generate_time_slots_for_schedule(schedule: DoctorSchedule):
    slots_to_create = []

    current_tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(
        datetime.combine(schedule.date, schedule.start_time), current_tz
    )
    end_dt = timezone.make_aware(
        datetime.combine(schedule.date, schedule.end_time), current_tz
    )

    slot_delta = timedelta(minutes=15)
    current_time = start_dt

    while current_time + slot_delta <= end_dt:
        slot_end = current_time + slot_delta
        slots_to_create.append(
            TimeSlot(
                doctor=schedule.doctor,
                start_datetime=current_time,
                end_datetime=slot_end,
                is_booked=False,
            )
        )
        current_time = slot_end

    with transaction.atomic():
        TimeSlot.objects.bulk_create(slots_to_create, ignore_conflicts=True)
