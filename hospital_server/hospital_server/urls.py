from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from hospital_server_app.views import (
    views_appointment,
    views_department,
    views_disease,
    views_doctor,
    views_drug,
    views_patient,
    views_room,
    views_specialization,
    views_user,
    views_report,
)
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

user_patterns = [
    path("signup/", views_user.signup, name="signup"),
    path("login/", views_user.login, name="login"),
    path("get/", views_user.get_users, name="get_users"),
    path("get_info/", views_user.get_user_info, name="get_user_info"),
    path("logout/", views_user.logout, name="logout"),
]

urlpatterns = [
    path(
        "swagger.<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("admin/", admin.site.urls),
    path("user/", include(user_patterns)),
    path("rooms/", views_room.rooms, name="rooms"),
    path("rooms/<int:pk>/", views_room.room, name="room"),
    path("departments/", views_department.departments, name="departments"),
    path("departments/<int:pk>/", views_department.department, name="department"),
    path(
        "specializations/", views_specialization.specializations, name="specializations"
    ),
    path(
        "specializations/<int:pk>/",
        views_specialization.specialization,
        name="specialization",
    ),
    path("diseases/", views_disease.diseases, name="diseases"),
    path("drugs/", views_drug.drugs, name="drugs"),
    path("drugs/<int:pk>/", views_drug.drug, name="drug"),
    path("doctors/", views_doctor.doctors, name="doctors"),
    path("doctors/<int:pk>/", views_doctor.doctor, name="doctor"),
    path("get-doctors/", views_doctor.DoctorListView.as_view(), name="get-doctors"),
    path(
        "patients/<int:pk>/history/",
        views_patient.medical_history,
        name="patient-history",
    ),
    path("patients/<int:pk>/", views_patient.patient, name="patient"),
    path("get-patients/", views_patient.PatientListView.as_view(), name="get-patients"),
    path("patients/", views_patient.register_patient, name="register-patient"),
    path(
        "appointments/cancel-or-noshow/",
        views_appointment.cancel_or_no_show_appointment,
        name="appointment-cancel-noshow",
    ),
    path(
        "appointments/book/",
        views_appointment.book_appointment,
        name="appointment-book",
    ),
    path(
        "appointments/complete/",
        views_appointment.complete_reception,
        name="appointment-complete",
    ),
    path(
        "slots/<int:pk>/", views_appointment.get_available_slots, name="available-slots"
    ),
    path("schedule/", views_appointment.create_schedule, name="create-schedule"),
    path(
        "api/reports/doctor/<int:doctor_id>/pdf/",
        views_report.export_doctor_analytics,
        name="export-doctor-pdf",
    ),
]
