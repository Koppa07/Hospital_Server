from unittest.mock import MagicMock, patch
from datetime import timedelta
from django.db import DatabaseError, connection
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from django.utils import timezone
from .models import *


class SignupTests(APITestCase):
    def setUp(self):
        self.url = reverse("signup")

    def test_signup_201(self):
        data = {"username": "TestAdmin", "password": "pass123", "role": "ADMIN"}
        response = self.client.post(self.url, data)
        user = User.objects.get(username="TestAdmin")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Token.objects.filter(user=user).exists())

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
        self.url = reverse("login")

    def test_login_200(self):
        data = {"username": "TestDoctor", "password": "pass123"}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["role"], "DOCTOR")

    def test_login_400_wrong_password(self):
        data = {"username": "TestDoctor", "password": "pass1234"}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "Неверное имя пользователя или пароль."
        )

    def test_login_400_no_data(self):
        data = {"username": "", "password": ""}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "Имя пользователя и пароль обязательны."
        )


class LogoutTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="TestDoctor", password="pass123")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url = reverse("logout")

    def test_logout_200(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_logout_401_unauthorized(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_401_token_invalid(self):
        self.client.post(self.url)
        response = self.client.get("/rooms/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PatientTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_user", password="password123", role="ADMIN"
        )
        self.admin_token = Token.objects.create(user=self.admin_user)

        self.patient_user = User.objects.create_user(
            username="patient_user", password="password123", role="PATIENT"
        )
        self.patient_token = Token.objects.create(user=self.patient_user)

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
        self.other_patient_token = Token.objects.create(user=self.other_patient_user)

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
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    # TODO Тесты с БД
    # @patch("django.db.connection.cursor")
    # def test_register_patient_success(self, mock_cursor):
    #     cursor_mock = MagicMock()
    #     cursor_mock.fetchone.return_value = [105]

    #     mock_cursor.return_value.__enter__.return_value = cursor_mock

    #     data = {
    #         "patient_name": "Сидоров Сидор Сидорович",
    #         "birth_date": "1995-05-15",
    #         "address": "г. Тверь, ул. Мира, д. 5",
    #         "insurance": "9876543210987654",
    #     }

    #     response = self.client.post(self.register_url, data, format="json")

    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertEqual(response.data["card_number"], 105)
    #     self.assertEqual(response.data["message"], "Пациент успешно зарегистрирован")

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

    # TODO Тесты с БД
    # @patch("django.db.connection.cursor")
    # def test_register_patient_database_error(self, mock_cursor):
    #     cursor_mock = MagicMock()
    #     cursor_mock.execute.side_effect = DatabaseError(
    #         "ERROR: unique constraint CONTEXT: during execution"
    #     )
    #     mock_cursor.return_value.__enter__.return_value = cursor_mock

    #     data = {
    #         "patient_name": "Петров Петр",
    #         "birth_date": "2000-01-01",
    #         "address": "Москва",
    #         "insurance": "1111222233334444",
    #     }

    #     response = self.client.post(self.register_url, data, format="json")

    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertIn("error", response.data)

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
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

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
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

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
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

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
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

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
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

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
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

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
        self.patient_token = Token.objects.create(user=self.patient_user)

        self.other_patient_user = User.objects.create_user(
            username="other_patient", password="password123", role="PATIENT"
        )
        self.other_patient_token = Token.objects.create(user=self.other_patient_user)

        self.doctor_user = User.objects.create_user(
            username="doctor_user", password="password123", role="DOCTOR"
        )
        self.doctor_token = Token.objects.create(user=self.doctor_user)

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
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    # TODO Тесты с БД
    # @patch.object(connection, "cursor")
    # def test_book_appointment_201(self, mock_cursor):
    #     data = {
    #         "doctor_id": self.doctor.doctor_id,
    #         "patient_id": self.patient.card_number,
    #         "appointment_date": self.slot_datetime.isoformat(),
    #     }
    #     response = self.client.post(self.book_url, data, format="json")

    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertEqual(response.data["message"], "Вы успешно записаны на прием!")

    #     self.slot.refresh_from_db()
    #     self.assertTrue(self.slot.is_booked)

    def test_book_appointment_foreign_patient_403(self):
        data = {
            "doctor_id": self.doctor.doctor_id,
            "patient_id": self.other_patient.card_number,
            "appointment_date": self.slot_datetime.isoformat(),
        }
        response = self.client.post(self.book_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)

    def test_book_appointment_slot_already_booked_400(self):
        self.slot.is_booked = True
        self.slot.save()

        data = {
            "doctor_id": self.doctor.doctor_id,
            "patient_id": self.patient.card_number,
            "appointment_date": self.slot_datetime.isoformat(),
        }
        response = self.client.post(self.book_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_get_available_slots_200(self):
        date_str = self.slot_datetime.strftime("%Y-%m-%d")
        response = self.client.get(f"{self.slots_url}?date={date_str}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_available_slots_missing_date_param_400(self):
        response = self.client.get(self.slots_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_appointment_by_owner_patient_200(self):
        appointment = ReceptionLog.objects.create(
            doctor_id=self.doctor,
            patient_id=self.patient,
            appointment_date=self.slot_datetime,
            status="BOOKED",
        )
        self.slot.is_booked = True
        self.slot.save()

        data = {"log_id": appointment.log_id, "status": "CANCELLED"}
        response = self.client.post(self.cancel_noshow_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        appointment.refresh_from_db()
        self.slot.refresh_from_db()
        self.assertEqual(appointment.status, "CANCELLED")
        self.assertFalse(self.slot.is_booked)

    def test_patient_cannot_mark_no_show_403(self):
        appointment = ReceptionLog.objects.create(
            doctor_id=self.doctor,
            patient_id=self.patient,
            appointment_date=self.slot_datetime,
            status="BOOKED",
        )

        data = {"log_id": appointment.log_id, "status": "NO_SHOW"}
        response = self.client.post(self.cancel_noshow_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancel_other_patient_appointment_forbidden_403(self):
        appointment = ReceptionLog.objects.create(
            doctor_id=self.doctor,
            patient_id=self.other_patient,
            appointment_date=self.slot_datetime,
            status="BOOKED",
        )

        data = {"log_id": appointment.log_id, "status": "CANCELLED"}
        response = self.client.post(self.cancel_noshow_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # TODO Тесты с БД
    # def test_complete_reception_200(self):
    #     self.set_auth(self.doctor_token)

    #     original_cursor_func = connection.cursor

    #     def get_mocked_cursor():
    #         # Получаем реальный курсор базы данных
    #         real_cursor = original_cursor_func()

    #         # Сохраняем оригинальный метод execute
    #         original_execute = real_cursor.execute

    #         def mocked_execute(sql, params=None):
    #             # Если вызывается процедура COMPLETE_RECEPTION, подменяем логику
    #             if "COMPLETE_RECEPTION" in str(sql).upper():
    #                 # Подменяем fetchone только для этого вызова
    #                 real_cursor.fetchone = lambda: [50]
    #                 return None

    #             # Для всех остальных запросов (аутентификация, ORM) выполняем реальный SQL
    #             return original_execute(sql, params)

    #         # Переопределяем метод execute у реального курсора
    #         real_cursor.execute = mocked_execute
    #         return real_cursor

    #     # Подменяем генератор курсоров
    #     connection.cursor = get_mocked_cursor

    #     try:
    #         # 1. Создаем реальную запись приема
    #         appointment = ReceptionLog.objects.create(
    #             doctor_id=self.doctor,
    #             patient_id=self.patient,
    #             appointment_date=self.slot_datetime,
    #             status="BOOKED",
    #         )
    #         drug = Drug.objects.create(drug_title="Vaseline", drug_type="Cream")

    #         data = {
    #             "log_id": appointment.pk,
    #             "disease_id": self.disease.disease_id,
    #             "complains": "Жалобы на головную боль",
    #             "recommendations": "Покой и обильное питье",
    #             "drugs": [
    #                 {"drug_id": drug.drug_id, "dosage": "1 таблетка 2 раза в день"}
    #             ],
    #         }

    #         response = self.client.post(self.complete_url, data, format="json")
    #         print("ОШИБКА ВАЛИДАЦИИ:", response.data)

    #         self.assertEqual(response.status_code, status.HTTP_200_OK)

    #     finally:
    #         # Возвращаем оригинальную функцию генерации курсоров
    #         connection.cursor = original_cursor_func

    def test_create_schedule_success(self):
        self.set_auth(self.doctor_token)

        schedule_date = (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        data = {
            "doctor": self.doctor.doctor_id,
            "date": schedule_date,
            "start_time": "08:00:00",
            "end_time": "16:00:00",
        }

        response = self.client.post(self.schedule_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            DoctorSchedule.objects.filter(
                doctor=self.doctor, date=schedule_date
            ).exists()
        )

        self.assertTrue(
            TimeSlot.objects.filter(
                doctor=self.doctor, start_datetime__date=schedule_date
            ).exists()
        )
