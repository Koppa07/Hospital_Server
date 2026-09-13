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
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

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
    path("change-password/", views_user.change_password, name="change-password"),
]
schedule_patterns = [
    path("", views_appointment.get_schedule, name="schedule-events"),
    path("slots/", views_appointment.get_available_slots, name="available-slots"),
    path("create/", views_appointment.create_schedule, name="create-schedule"),
    path("book/", views_appointment.book_appointment, name="appointment-book"),
]

appointment_patterns = [
    path("", views_appointment.get_appointments, name="get-appointments"),
    path(
        "<int:log_id>/complete/",
        views_appointment.complete_reception,
        name="appointment-complete",
    ),
    path(
        "<int:log_id>/cancel/",
        views_appointment.cancel_or_no_show_appointment,
        name="appointment-cancel",
    ),
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
    path("api-auth/", include("rest_framework.urls")),
    path("token/", TokenObtainPairView.as_view(), name="get_token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="refresh_token"),
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
    path("diseases/<int:pk>/", views_disease.disease, name="disease"),
    path("drugs/", views_drug.drugs, name="drugs"),
    path("drugs/<int:pk>/", views_drug.drug, name="drug"),
    path("doctors/", views_doctor.doctors, name="create-doctor"),
    path("doctors/<int:pk>/", views_doctor.doctor, name="doctor"),
    path("doctors/", views_doctor.DoctorListView.as_view(), name="get-doctors"),
    path(
        "doctor/profile/",
        views_doctor.create_or_update_doctor_profile,
        name="doctor-profile",
    ),
    path(
        "medical-history/",
        views_appointment.medical_history,
        name="history",
    ),
    path("patients/<int:pk>/", views_patient.patient, name="patient"),
    path("patients/", views_patient.PatientListView.as_view(), name="get-patients"),
    path("patients/register/", views_patient.register_patient, name="register-patient"),
    path(
        "patient/profile/",
        views_patient.create_or_update_patient_profile,
        name="patient-profile",
    ),
    path("schedule/", include(schedule_patterns)),
    path("appointments/", include(appointment_patterns)),
    path(
        "reports/doctor/<int:doctor_id>/pdf/",
        views_report.export_doctor_analytics,
        name="export-doctor-pdf",
    ),
]
