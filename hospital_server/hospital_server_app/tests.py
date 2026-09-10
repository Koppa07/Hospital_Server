from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import *


class SignupTests(APITestCase):
    def setUp(self):
        self.url = reverse("signup")

    def test_signup_201(self):
        data = {"username": "TestAdmin", "password": "pass123", "role": "ADMIN"}
        response = self.client.post(self.url, data)
        user = User.objects.get(username="TestAdmin")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(user)

    def test_signup_201_no_role(self):
        data = {
            "username": "TestPatient",
            "password": "pass123",
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], "PATIENT")


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestDoctor", password="pass123", role="DOCTOR"
        )
        # Если вы используете штатный JWT-эндпоинт:
        self.url = reverse("get_token")
        # Если у вас кастомный вью логина: reverse("login")

    def test_login_200(self):
        data = {"username": "TestDoctor", "password": "pass123"}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # В JWT проверяем наличие access и refresh токенов
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_400_wrong_password(self):
        data = {"username": "TestDoctor", "password": "pass1234"}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_400_no_data(self):
        data = {"username": "", "password": ""}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="TestDoctor", password="pass123")

        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        self.url = reverse("logout")

    def test_logout_200(self):
        data = {"refresh": str(self.refresh)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_401_unauthorized(self):
        self.client.credentials()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PatientTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_user", password="password123", role="ADMIN"
        )
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)

        self.patient_user = User.objects.create_user(
            username="patient_user", password="password123", role="PATIENT"
        )
        self.patient_token = str(RefreshToken.for_user(self.patient_user).access_token)

        self.patient = Patient.objects.create(
            user=self.patient_user,
            patient_name="Иванов Иван Иванович",
            birth_date="1990-01-01",
            address="г. Москва, ул. Ленина, д. 10",
            insurance="1234567890123456",
        )

        self.other_patient_user = User.objects.create_user(
            username="other_patient", password="password123", role="PATIENT"
        )
        self.other_patient_token = str(
            RefreshToken.for_user(self.other_patient_user).access_token
        )

        self.other_patient = Patient.objects.create(
            user=self.other_patient_user,
            patient_name="Петров Петр Петровиче",
            birth_date="1992-02-02",
            address="г. Москва, ул. Мира, д. 1",
            insurance="6543210987654321",
        )

        self.register_url = reverse("register-patient")
        self.list_url = reverse("get-patients")
        self.user_info_url = reverse("get_user_info")

        self.set_auth(self.admin_token)

    def set_auth(self, token):
        # Префикс изменился с "Token " на "Bearer "
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_register_patient_invalid_insurance_not_digits(self):
        data = {
            "patient_name": "Петров Петр",
            "birth_date": "2000-01-01",
            "address": "Москва",
            "insurance": "1234567890ABCDEF",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("insurance", response.data)

    def test_register_patient_invalid_insurance_length(self):
        data = {
            "patient_name": "Петров Петр",
            "birth_date": "2000-01-01",
            "address": "Москва",
            "insurance": "12345",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("insurance", response.data)

    def test_get_patients_list_200(self):
        self.set_auth(self.admin_token)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_search_patient_by_name(self):
        self.set_auth(self.admin_token)
        response = self.client.get(self.list_url, {"search": "Иванов"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["patient_name"], "Иванов Иван Иванович")

    def test_update_patient_put_200(self):
        url = reverse("patient", kwargs={"pk": self.patient.card_number})
        data = {
            "patient_name": "Иванов Иван Сергеевич",
            "birth_date": "1990-01-01",
            "address": "г. СПБ, Невский пр., д. 1",
            "insurance": "9999999999999999",
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.patient_name, "Иванов Иван Сергеевич")

    def test_update_patient_patch_200(self):
        url = reverse("patient", kwargs={"pk": self.patient.card_number})
        data = {"address": "Новый адрес"}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.address, "Новый адрес")

    def test_update_patient_not_found(self):
        url = reverse("patient", kwargs={"pk": 99999})
        response = self.client.patch(url, {"address": "Новый адрес"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_patient_204(self):
        url = reverse("patient", kwargs={"pk": self.patient.card_number})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(pk=self.patient.card_number).exists())

    def test_get_medical_history_as_owner_patient_200(self):
        self.set_auth(self.patient_token)
        url = reverse(
            "patient-history",
            kwargs={"pk": self.patient.card_number},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_medical_history_as_other_patient_403(self):
        self.set_auth(self.other_patient_token)
        url = reverse(
            "patient-history",
            kwargs={"pk": self.patient.card_number},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)

    def test_get_medical_history_as_admin_200(self):
        self.set_auth(self.admin_token)
        url = reverse(
            "patient-history",
            kwargs={"pk": self.patient.card_number},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_info_patient_success_200(self):
        self.set_auth(self.patient_token)
        response = self.client.get(self.user_info_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["card_number"], self.patient.card_number)
        self.assertEqual(response.data["patient_name"], "Иванов Иван Иванович")

    def test_get_user_info_non_patient_404(self):
        self.set_auth(self.admin_token)
        response = self.client.get(self.user_info_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)


class SpecializationsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestAdminSpec", password="pass123", role="ADMIN"
        )
        self.specialization = Specialization.objects.create(spec_title="Физиотерапевт")

        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.list_url = reverse("specializations")
        self.detail_url = reverse(
            "specialization", kwargs={"pk": self.specialization.pk}
        )

    def test_create_specialization_201(self):
        data = {"spec_title": "Хирург"}
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Specialization.objects.count(), 2)

        created_data = response.data.get("Добавлена специализация", {})
        self.assertEqual(created_data.get("spec_title"), "Хирург")

    def test_get_specializations_200(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_specialization_400(self):
        data = {"spec_title": ""}
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("spec_title", response.data)
        self.assertEqual(Specialization.objects.count(), 1)

    def test_full_update_spec_200(self):
        data = {"spec_title": "Стоматолог"}
        response = self.client.put(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация о специализации", response.data)

        self.specialization.refresh_from_db()
        self.assertEqual(self.specialization.spec_title, "Стоматолог")

    def test_partial_update_spec_200(self):
        data = {"spec_title": "Частично обновленная специализация"}
        response = self.client.patch(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация о специализации", response.data)

        self.specialization.refresh_from_db()
        self.assertEqual(
            self.specialization.spec_title, "Частично обновленная специализация"
        )

    def test_delete_spec_204(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Specialization.objects.count(), 0)
        self.assertIn("Специализация удалена", response.data)

        response2 = self.client.delete(self.detail_url)

        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_spec_detail_404_not_found(self):
        detail_url = reverse("specialization", kwargs={"pk": 9999})
        response = self.client.get(detail_url)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DepartmentsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestAdminDep", password="pass123", role="ADMIN"
        )
        self.department = Department.objects.create(
            dep_title="Физиотерапия", name_of_manager="Ivan Ivanov"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.url = reverse("departments")
        self.detail_url = reverse("department", kwargs={"pk": self.department.pk})

    def test_create_department_201(self):
        data = {"dep_title": "Хирургия", "name_of_manager": "Василиса Кагановская"}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_data = response.data.get("Добавлено отделение", {})
        self.assertEqual(created_data.get("dep_title"), "Хирургия")
        self.assertEqual(created_data.get("name_of_manager"), "Василиса Кагановская")
        self.assertEqual(Department.objects.count(), 2)

    def test_get_departments_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_department_400(self):
        data = {"dep_title": "", "name_of_manager": ""}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("dep_title", response.data)
        self.assertEqual(Department.objects.count(), 1)

    def test_full_update_dep_200(self):
        data = {"dep_title": "Стоматология", "name_of_manager": "Таисия Васильевна"}
        response = self.client.put(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация об отделении", response.data)

        self.department.refresh_from_db()
        self.assertEqual(self.department.dep_title, "Стоматология")

    def test_partial_update_dep_200(self):
        data = {"dep_title": "Частично обновленное отделение"}
        response = self.client.patch(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация об отделении", response.data)

        self.department.refresh_from_db()
        self.assertEqual(self.department.dep_title, "Частично обновленное отделение")

    def test_delete_dep_204(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Department.objects.count(), 0)
        self.assertIn("Информация об отделении удалена", response.data)

        response2 = self.client.delete(self.detail_url)

        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_dep_detail_404_not_found(self):
        detail_url = reverse("department", kwargs={"pk": 9999})
        response = self.client.get(detail_url)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RoomsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestAdminRoom", password="pass123", role="ADMIN"
        )
        self.room = Room.objects.create(room_number=67, equipment="Аппарат МРТ")
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.url = reverse("rooms")
        self.detail_url = reverse("room", kwargs={"pk": self.room.pk})

    def test_create_room_201(self):
        data = {"room_number": "52", "equipment": "Аппарат КТ"}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Room.objects.count(), 2)

        created_data = response.data.get("Добавлен кабинет", {})
        self.assertEqual(created_data.get("room_number"), 52)
        self.assertEqual(created_data.get("equipment"), "Аппарат КТ")

    def test_get_rooms_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_room_400(self):
        data = {"room_number": ""}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("room_number", response.data)
        self.assertEqual(Room.objects.count(), 1)

    def test_create_room_duplicate_400(self):
        data = {"room_number": self.room.room_number}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Room.objects.count(), 1)

    def test_full_update_room_200(self):
        data = {"room_number": "42", "equipment": self.room.equipment}
        response = self.client.put(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация о кабинете", response.data)

        self.room.refresh_from_db()
        self.assertEqual(self.room.room_number, 42)

    def test_partial_update_room_200(self):
        data = {"equipment": "Частично обновленное оборудование"}
        response = self.client.patch(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация о кабинете", response.data)

        self.room.refresh_from_db()
        self.assertEqual(self.room.equipment, "Частично обновленное оборудование")

    def test_delete_room_204(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Room.objects.count(), 0)
        self.assertIn("Информация о кабинете удалена", response.data)

        response2 = self.client.delete(self.detail_url)

        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_room_detail_404_not_found(self):
        detail_url = reverse("room", kwargs={"pk": 9999})
        response = self.client.get(detail_url)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DrugsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestAdminDrug", password="pass123", role="ADMIN"
        )
        self.drug = Drug.objects.create(drug_title="Vaseline", drug_type="Крем")
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.url = reverse("drugs")
        self.detail_url = reverse("drug", kwargs={"pk": self.drug.pk})

    def test_create_drug_201(self):
        data = {"drug_title": "Нурофен", "drug_type": "Таблетки"}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Drug.objects.count(), 2)

        created_data = response.data.get("Добавлен медикамент", {})
        self.assertEqual(created_data.get("drug_title"), "Нурофен")
        self.assertEqual(created_data.get("drug_type"), "Таблетки")

    def test_get_drugs_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_drug_400(self):
        data = {"drug_title": ""}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("drug_title", response.data)
        self.assertEqual(Drug.objects.count(), 1)

    def test_full_update_drug_200(self):
        data = {"drug_title": self.drug.drug_title, "drug_type": "Мазь"}
        response = self.client.put(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация о медикаменте", response.data)

        self.drug.refresh_from_db()
        self.assertEqual(self.drug.drug_type, "Мазь")

    def test_partial_update_drug_200(self):
        data = {"drug_type": "Частично обновленный тип"}
        response = self.client.patch(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация о медикаменте", response.data)

        self.drug.refresh_from_db()
        self.assertEqual(self.drug.drug_type, "Частично обновленный тип")

    def test_delete_drug_204(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Drug.objects.count(), 0)
        self.assertIn("Информация о медикаменте удалена", response.data)

        response2 = self.client.delete(self.detail_url)

        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_drug_detail_404_not_found(self):
        detail_url = reverse("drug", kwargs={"pk": 9999})
        response = self.client.get(detail_url)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DiseasesTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestAdminDisease", password="pass123", role="ADMIN"
        )
        self.disease = Disease.objects.create(
            disease_code="C00-C97", disease_title="Злокачественные новообразования"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.url = reverse("diseases")

    def test_get_diseases_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class DoctorsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestAdminDoctor", password="pass123", role="ADMIN"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.doctor_user = User.objects.create_user(
            username="DoctorUser", password="pass123", role="DOCTOR"
        )
        self.specialization = Specialization.objects.create(spec_title="Терапия")
        self.department = Department.objects.create(
            dep_title="Терапевтическое", name_of_manager="Петров П.П."
        )
        self.room = Room.objects.create(room_number=101)

        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            doctor_name="Иван Иванов",
            spec=self.specialization,
            dep=self.department,
            room=self.room,
        )

        self.list_url = reverse("get-doctors")
        self.create_url = reverse("doctors")

    def test_get_doctors_list_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_and_search_doctors_200(self):
        response = self.client.get(self.list_url, {"search": "Иван"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get(self.list_url, {"spec": self.specialization.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_doctor_201(self):
        data = {
            "doctor_name": "Сергей Сергеев",
            "spec_id": self.specialization.pk,
            "dep_id": self.department.pk,
            "room_id": self.room.pk,
            "username": "DoctorSergey",
            "password": "pass12345",
        }
        response = self.client.post(self.create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Добавлен врач", response.data)
        self.assertEqual(Doctor.objects.count(), 2)

    def test_create_doctor_400_invalid_data(self):
        data = {"doctor_name": ""}
        response = self.client.post(self.create_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Doctor.objects.count(), 1)

    def test_update_doctor_put_200(self):
        detail_url = reverse("doctor", kwargs={"pk": self.doctor.pk})
        data = {
            "doctor_name": "Иван Обновленный",
            "spec": self.specialization.pk,
            "dep": self.department.pk,
            "room": self.room.pk,
        }
        response = self.client.put(detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Обновлена информация о враче", response.data)

        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.doctor_name, "Иван Обновленный")

    def test_update_doctor_patch_200(self):
        detail_url = reverse("doctor", kwargs={"pk": self.doctor.pk})
        data = {"doctor_name": "Иван Частичный"}
        response = self.client.patch(detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.doctor_name, "Иван Частичный")

    def test_delete_doctor_204(self):
        detail_url = reverse("doctor", kwargs={"pk": self.doctor.pk})
        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Doctor.objects.count(), 0)

    def test_doctor_detail_404_not_found(self):
        detail_url = reverse("doctor", kwargs={"pk": 9999})
        response = self.client.get(detail_url)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AppointmentAndScheduleTests(APITestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            username="patient_user", password="password123", role="PATIENT"
        )
        self.patient_token = str(RefreshToken.for_user(self.patient_user).access_token)

        self.other_patient_user = User.objects.create_user(
            username="other_patient", password="password123", role="PATIENT"
        )
        self.other_patient_token = str(
            RefreshToken.for_user(self.other_patient_user).access_token
        )

        self.doctor_user = User.objects.create_user(
            username="doctor_user", password="password123", role="DOCTOR"
        )
        self.doctor_token = str(RefreshToken.for_user(self.doctor_user).access_token)

        self.specialization = Specialization.objects.create(spec_title="Терапия")
        self.department = Department.objects.create(
            dep_title="Терапевтическое", name_of_manager="Петров П.П."
        )
        self.room = Room.objects.create(room_number=101)

        self.patient = Patient.objects.create(
            user=self.patient_user,
            patient_name="Иванов Иван",
            birth_date="1990-01-01",
            address="г. Москва",
            insurance="1234567890123456",
        )

        self.other_patient = Patient.objects.create(
            user=self.other_patient_user,
            patient_name="Петров Петр",
            birth_date="1992-02-02",
            address="г. Тверь",
            insurance="6543210987654321",
        )

        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            doctor_name="Иван Иванов",
            spec=self.specialization,
            dep=self.department,
            room=self.room,
        )

        tomorrow = timezone.now() + timedelta(days=1)
        self.slot_datetime = tomorrow.replace(
            hour=10, minute=0, second=0, microsecond=0
        )

        self.slot = TimeSlot.objects.create(
            doctor=self.doctor,
            start_datetime=self.slot_datetime,
            end_datetime=self.slot_datetime + timedelta(minutes=15),
            is_booked=False,
        )
        self.disease = Disease.objects.create(
            disease_title="ОРВИ", disease_code="J06.9"
        )

        self.book_url = reverse("appointment-book")
        self.complete_url = reverse("appointment-complete")
        self.cancel_noshow_url = reverse("appointment-cancel-noshow")
        self.slots_url = reverse("available-slots", kwargs={"pk": self.doctor.pk})
        self.schedule_url = reverse("create-schedule")

        self.set_auth(self.patient_token)

    def set_auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
