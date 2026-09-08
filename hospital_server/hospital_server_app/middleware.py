from django.db import connection, DatabaseError


class PatientRLSMiddleware:
    """
    Middleware, устанавливающий сессионную переменную PostgreSQL app.current_patient_card
    для текущего аутентифицированного пациента.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        patient_card_id = None

        if (
            request.user.is_authenticated
            and getattr(request.user, "role", None) == "PATIENT"
        ):
            patient_profile = getattr(request.user, "patient_profile", None)
            if patient_profile:
                patient_card_id = patient_profile.card_number

        if patient_card_id:
            try:
                with connection.cursor() as cursor:
                    # SET LOCAL действует строго до конца текущей транзакции/запроса
                    cursor.execute(
                        "SET LOCAL app.current_patient_card = %s;",
                        [str(patient_card_id)],
                    )
            except DatabaseError:
                pass

        response = self.get_response(request)

        return response
