import io
import os
from io import BytesIO
from collections import defaultdict
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLACK = colors.black
HEADER_BACKGROUND = colors.HexColor("#F1F3F4")


def register_fonts():
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "Roboto-Regular.ttf")
    bold_path = os.path.join(settings.BASE_DIR, "static", "fonts", "Roboto-Bold.ttf")
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Не найден шрифт: {font_path}")
    if "Roboto" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Roboto", font_path))
    if os.path.exists(bold_path) and "Roboto-Bold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Roboto-Bold", bold_path))

    pdfmetrics.registerFontFamily(
        "Roboto",
        normal="Roboto",
        bold="Roboto-Bold" if os.path.exists(bold_path) else "Roboto",
        italic="Roboto",
        boldItalic="Roboto-Bold" if os.path.exists(bold_path) else "Roboto",
    )

    return "Roboto"


def create_document(buffer, pagesize=A4):
    return SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
    )


def create_report_styles(font_name, body_font_size=9):
    bold_font = (
        "Roboto-Bold"
        if "Roboto-Bold" in pdfmetrics.getRegisteredFontNames()
        else font_name
    )
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            fontName=bold_font,
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=BLACK,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=BLACK,
            spaceAfter=14,
        ),
        "section": ParagraphStyle(
            "ReportSection",
            fontName=bold_font,
            fontSize=11,
            leading=14,
            textColor=BLACK,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            fontName=font_name,
            fontSize=body_font_size,
            leading=body_font_size + 2,
            textColor=BLACK,
        ),
        "header": ParagraphStyle(
            "ReportTableHeader",
            fontName=bold_font,
            fontSize=body_font_size,
            leading=body_font_size + 2,
            textColor=BLACK,
        ),
    }


def create_table_style(font_name, font_size=9):
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BACKGROUND),
            ("TEXTCOLOR", (0, 0), (-1, -1), BLACK),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#808080")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def as_paragraph(value, style):
    text = "—" if value is None or value == "" else str(value)
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.setFont("Roboto", 9)
        self.setFillColor(BLACK)
        self.drawRightString(
            self._pagesize[0] - 36, 20, f"Страница {self._pageNumber} из {page_count}"
        )


def generate_analytics_pdf(report_data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    font_name = register_fonts()
    doc = create_document(buffer)
    styles = create_report_styles(font_name, body_font_size=9)

    story = []

    story.append(Paragraph("Аналитический отчет работы врача", styles["title"]))
    story.append(
        Paragraph(
            f"Врач: <b>{escape(str(report_data['doctor_name']))}</b> | "
            f"Период: {escape(str(report_data['period']))}",
            styles["subtitle"],
        )
    )

    story.append(Paragraph("Общие показатели", styles["section"]))

    summary_table_data = [
        [
            Paragraph("Показатель", styles["header"]),
            Paragraph("Значение", styles["header"]),
        ],
        [
            as_paragraph("Всего запланировано приемов", styles["body"]),
            str(report_data["total_appointments"]),
        ],
        [
            as_paragraph("Успешно завершено", styles["body"]),
            str(report_data["completed_count"]),
        ],
        [
            as_paragraph("Отменено / Неявки", styles["body"]),
            str(report_data["cancelled_count"]),
        ],
    ]

    summary_table = Table(summary_table_data, colWidths=[120 * mm, 40 * mm])
    summary_table.setStyle(create_table_style(font_name))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Распределение диагнозов (МКБ-10)", styles["section"]))

    diseases_table_data = [
        [
            Paragraph("Код МКБ", styles["header"]),
            Paragraph("Наименование заболевания", styles["header"]),
            Paragraph("Кол-во случаев", styles["header"]),
        ]
    ]

    for item in report_data["top_diseases"]:
        diseases_table_data.append(
            [
                as_paragraph(item["code"], styles["body"]),
                as_paragraph(item["title"], styles["body"]),
                str(item["count"]),
            ]
        )

    diseases_table = Table(
        diseases_table_data, colWidths=[25 * mm, 105 * mm, 30 * mm], repeatRows=1
    )
    diseases_table.setStyle(create_table_style(font_name))
    story.append(diseases_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


def generate_diagnosis_drug_pdf(report_data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    font_name = register_fonts()
    doc = create_document(buffer)
    styles = create_report_styles(font_name, body_font_size=7.5)
    records = report_data["records"]
    appointments = set()
    diagnoses = defaultdict(set)
    drugs = defaultdict(int)

    for record in records:
        appointment_key = (
            record.get("APPOINTMENT_DATE"),
            record.get("PATIENT_NAME"),
            record.get("DOCTOR_NAME"),
        )
        appointments.add(appointment_key)

        disease_code = record.get("DISEASE_CODE")
        disease_title = record.get("DISEASE_TITLE")
        if disease_code or disease_title:
            diagnoses[(disease_code, disease_title)].add(appointment_key)

        drug_title = record.get("DRUG_TITLE")
        if drug_title:
            drug_key = (drug_title, record.get("DRUG_TYPE"), record.get("DOSAGE"))
            drugs[drug_key] += 1

    def format_date(value):
        if hasattr(value, "strftime"):
            return value.strftime("%d.%m.%Y %H:%M")
        return value

    story = [
        Paragraph(
            "Отчет по поставленным диагнозам и назначенным препаратам",
            styles["title"],
        ),
        Paragraph(
            f"Отчетный период: <b>{escape(str(report_data['period']))}</b>",
            styles["subtitle"],
        ),
        Paragraph("Общие показатели", styles["section"]),
    ]

    summary_table = Table(
        [
            [
                Paragraph("Показатель", styles["header"]),
                Paragraph("Количество", styles["header"]),
            ],
            [
                as_paragraph("Приемы (по дате, пациенту и врачу)", styles["body"]),
                str(len(appointments)),
            ],
            [as_paragraph("Диагнозы", styles["body"]), str(len(diagnoses))],
            [as_paragraph("Назначения препаратов", styles["body"]), str(sum(drugs.values()))],
        ],
        colWidths=[120 * mm, 40 * mm],
        repeatRows=1,
    )
    summary_table.setStyle(create_table_style(font_name, font_size=7.5))
    story.extend([summary_table, Spacer(1, 10)])

    story.append(Paragraph("Часто встречающиеся диагнозы", styles["section"]))
    disease_rows = [
        [
            Paragraph("Код", styles["header"]),
            Paragraph("Заболевание", styles["header"]),
            Paragraph("Приемы", styles["header"]),
        ]
    ]
    for (code, title), visits in sorted(
        diagnoses.items(), key=lambda item: (-len(item[1]), str(item[0]))
    )[:10]:
        disease_rows.append(
            [
                as_paragraph(code, styles["body"]),
                as_paragraph(title, styles["body"]),
                str(len(visits)),
            ]
        )
    if not diagnoses:
        disease_rows.append([as_paragraph("За период диагнозы не указаны.", styles["body"]), "", ""])

    disease_table = Table(
        disease_rows, colWidths=[25 * mm, 110 * mm, 25 * mm], repeatRows=1
    )
    disease_table.setStyle(create_table_style(font_name, font_size=7.5))
    if not diagnoses:
        disease_table.setStyle(
            TableStyle([("SPAN", (0, 1), (-1, 1))])
        )
    story.append(disease_table)

    story.append(Paragraph("Часто назначаемые препараты", styles["section"]))
    drug_rows = [
        [
            Paragraph("Препарат", styles["header"]),
            Paragraph("Тип", styles["header"]),
            Paragraph("Дозировка", styles["header"]),
            Paragraph("Назначения", styles["header"]),
        ]
    ]
    for (title, drug_type, dosage), count in sorted(
        drugs.items(), key=lambda item: (-item[1], str(item[0]))
    )[:10]:
        drug_rows.append(
            [
                as_paragraph(title, styles["body"]),
                as_paragraph(drug_type, styles["body"]),
                as_paragraph(dosage, styles["body"]),
                str(count),
            ]
        )
    if not drugs:
        drug_rows.append(
            [
                as_paragraph("За период назначения препаратов отсутствуют.", styles["body"]),
                "",
                "",
                "",
            ]
        )

    drug_table = Table(
        drug_rows, colWidths=[60 * mm, 30 * mm, 45 * mm, 25 * mm], repeatRows=1
    )
    drug_table.setStyle(create_table_style(font_name, font_size=7.5))
    if not drugs:
        drug_table.setStyle(TableStyle([("SPAN", (0, 1), (-1, 1))]))
    story.append(drug_table)

    story.append(Paragraph("Детализация приемов и назначений", styles["section"]))
    details = [
        [
            Paragraph("Дата", styles["header"]),
            Paragraph("Пациент / врач", styles["header"]),
            Paragraph("Диагноз", styles["header"]),
            Paragraph("Препарат / тип", styles["header"]),
            Paragraph("Дозировка", styles["header"]),
            Paragraph("Рекомендации", styles["header"]),
        ]
    ]
    for record in records:
        patient_and_doctor = (
            f"<b>Пациент:</b> {escape(str(record.get('PATIENT_NAME') or '—'))}<br/>"
            f"<b>Врач:</b> {escape(str(record.get('DOCTOR_NAME') or '—'))}"
        )
        diagnosis = (
            f"<b>{escape(str(record.get('DISEASE_CODE') or '—'))}</b><br/>"
            f"{escape(str(record.get('DISEASE_TITLE') or '—'))}"
        )
        drug = (
            f"<b>{escape(str(record.get('DRUG_TITLE') or '—'))}</b><br/>"
            f"{escape(str(record.get('DRUG_TYPE') or '—'))}"
        )
        details.append(
            [
                as_paragraph(format_date(record.get("APPOINTMENT_DATE")), styles["body"]),
                Paragraph(patient_and_doctor, styles["body"]),
                Paragraph(diagnosis, styles["body"]),
                Paragraph(drug, styles["body"]),
                as_paragraph(record.get("DOSAGE"), styles["body"]),
                as_paragraph(record.get("RECOMMENDATIONS"), styles["body"]),
            ]
        )

    if records:
        details_table = LongTable(
            details,
            colWidths=[18 * mm, 31 * mm, 31 * mm, 28 * mm, 20 * mm, 32 * mm],
            repeatRows=1,
        )
        details_table.setStyle(create_table_style(font_name, font_size=7.5))
        story.append(details_table)
    else:
        story.append(
            Paragraph(
                "За выбранный период завершенных приемов не найдено.",
                styles["body"],
            )
        )

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


def generate_patient_age_pdf(report_data: dict) -> BytesIO:
    buffer = BytesIO()
    font_name = register_fonts()
    doc = create_document(buffer)
    styles = create_report_styles(font_name)
    rows = report_data["rows"]
    table_data = [
        [
            Paragraph("Возрастная группа", styles["header"]),
            Paragraph("Количество пациентов", styles["header"]),
        ]
    ]
    total = 0
    for item in rows:
        count = int(item["patient_count"] or 0)
        total += count
        table_data.append(
            [
                as_paragraph(item["age_group"], styles["body"]),
                str(count),
            ]
        )
    table_data.append(
        [
            Paragraph("<b>Всего</b>", styles["body"]),
            Paragraph(f"<b>{total}</b>", styles["body"]),
        ]
    )
    table = Table(table_data, colWidths=[100 * mm, 60 * mm], repeatRows=1)
    table.setStyle(create_table_style(font_name))

    story = [
        Paragraph("Отчет о возрастной структуре пациентов", styles["title"]),
        Paragraph(
            f"Дата формирования: {escape(str(report_data['as_of_date']))}",
            styles["subtitle"],
        ),
        table,
    ]
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


def generate_appointment_status_pdf(report_data: dict) -> BytesIO:
    buffer = BytesIO()
    font_name = register_fonts()
    doc = create_document(buffer)
    styles = create_report_styles(font_name)
    status_names = {
        "BOOKED": "Запланирован",
        "COMPLETED": "Завершен",
        "CANCELLED": "Отменен",
        "NO_SHOW": "Неявка",
    }
    table_data = [
        [
            Paragraph("Статус записи", styles["header"]),
            Paragraph("Количество записей", styles["header"]),
            Paragraph("Количество пациентов", styles["header"]),
        ]
    ]
    total_appointments = 0
    total_patients_by_status = 0
    for item in report_data["rows"]:
        appointment_count = int(item["appointment_count"] or 0)
        patient_count = int(item["patient_count"] or 0)
        total_appointments += appointment_count
        total_patients_by_status += patient_count
        status_name = status_names.get(
            item["appointment_status"], item["appointment_status"]
        )
        table_data.append(
            [
                as_paragraph(status_name, styles["body"]),
                str(appointment_count),
                str(patient_count),
            ]
        )
    table_data.append(
        [
            as_paragraph("Сумма по статусам", styles["body"]),
            str(total_appointments),
            str(total_patients_by_status),
        ]
    )
    table = Table(
        table_data, colWidths=[70 * mm, 45 * mm, 45 * mm], repeatRows=1
    )
    table.setStyle(create_table_style(font_name))
    story = [
        Paragraph("Отчет о состоянии записей на прием", styles["title"]),
        Paragraph(
            f"Период: {escape(str(report_data['date_from']))} — "
            f"{escape(str(report_data['date_to']))}",
            styles["subtitle"],
        ),
        table,
    ]
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


def generate_doctor_load_pdf(report_data: dict) -> BytesIO:
    buffer = BytesIO()
    font_name = register_fonts()
    doc = create_document(buffer, pagesize=landscape(A4))
    styles = create_report_styles(font_name, body_font_size=7.5)
    headers = (
        "Врач",
        "Специализация",
        "Отделение",
        "Рабочие дни",
        "Часы",
        "Записи",
        "Завершено",
        "Отменено",
        "Неявки",
    )
    table_data = [[Paragraph(header, styles["header"]) for header in headers]]
    for item in report_data["rows"]:
        hours = float(item["work_minutes"] or 0) / 60
        table_data.append(
            [
                as_paragraph(item["doctor_name"], styles["body"]),
                as_paragraph(item["spec_title"], styles["body"]),
                as_paragraph(item["dep_title"], styles["body"]),
                str(item["work_days"]),
                f"{hours:.1f}",
                str(item["appointment_count"]),
                str(item["completed_count"]),
                str(item["cancelled_count"]),
                str(item["no_show_count"]),
            ]
        )
    if not report_data["rows"]:
        table_data.append(
            [as_paragraph("За выбранный период данных нет.", styles["body"])]
            + [""] * (len(headers) - 1)
        )
    column_widths = [43, 38, 38, 25, 18, 23, 26, 26, 24]
    table = Table(
        table_data,
        colWidths=[width * mm for width in column_widths],
        repeatRows=1,
    )
    table.setStyle(create_table_style(font_name, font_size=7.5))
    if not report_data["rows"]:
        table.setStyle(TableStyle([("SPAN", (0, 1), (-1, 1))]))
    story = [
        Paragraph("Отчет о загрузке врачей", styles["title"]),
        Paragraph(
            f"Период: {escape(str(report_data['date_from']))} — "
            f"{escape(str(report_data['date_to']))}",
            styles["subtitle"],
        ),
        table,
    ]
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer
