import io
import os
from collections import defaultdict
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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


def register_fonts():
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "Roboto-Regular.ttf")
    bold_path = os.path.join(settings.BASE_DIR, "static", "fonts", "Roboto-Bold.ttf")
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Не найден шрифт: {font_path}")
    pdfmetrics.registerFont(TTFont("Roboto", font_path))
    pdfmetrics.registerFont(TTFont("Roboto-Bold", bold_path))

    pdfmetrics.registerFontFamily(
        "Roboto",
        normal="Roboto",
        bold="Roboto-Bold" if os.path.exists(bold_path) else "Roboto",
        italic="Roboto",
        boldItalic="Roboto-Bold" if os.path.exists(bold_path) else "Roboto",
    )

    return "Roboto"


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
        self.setFillColor(colors.HexColor("#000000"))
        self.drawRightString(
            A4[0] - 36, 20, f"Страница {self._pageNumber} из {page_count}"
        )


def generate_analytics_pdf(report_data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    font_name = register_fonts()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        fontName=font_name,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#000000"),
        bold=True,
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubTitle",
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#000000"),
        spaceAfter=20,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        fontName=font_name,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#000000"),
        bold=True,
        spaceBefore=15,
        spaceAfter=10,
    )
    normal_style = ParagraphStyle(
        "NormalText",
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#000000"),
    )

    story = []

    story.append(Paragraph("Аналитический отчет работы врача", title_style))
    story.append(
        Paragraph(
            f"Врач: <b>{report_data['doctor_name']}</b> | Период: {report_data['period']}",
            subtitle_style,
        )
    )

    story.append(Paragraph("Общие показатели", section_style))

    summary_table_data = [
        [Paragraph("Показатель", normal_style), Paragraph("Значение", normal_style)],
        [
            Paragraph("Всего запланировано приемов", normal_style),
            str(report_data["total_appointments"]),
        ],
        [
            Paragraph("Успешно завершено", normal_style),
            str(report_data["completed_count"]),
        ],
        [
            Paragraph("Отменено / Неявки", normal_style),
            str(report_data["cancelled_count"]),
        ],
    ]

    summary_table = Table(summary_table_data, colWidths=[350, 150])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFFFFF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#000000")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#000000")),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Распределение диагнозов (МКБ-10)", section_style))

    diseases_table_data = [
        [
            Paragraph("Код МКБ", normal_style),
            Paragraph("Наименование заболевания", normal_style),
            Paragraph("Кол-во случаев", normal_style),
        ]
    ]

    for item in report_data["top_diseases"]:
        diseases_table_data.append(
            [
                item["code"],
                Paragraph(item["title"], normal_style),
                str(item["count"]),
            ]
        )

    diseases_table = Table(diseases_table_data, colWidths=[80, 320, 100])
    diseases_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFFFFF")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#000000")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(diseases_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


def generate_diagnosis_drug_pdf(report_data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    font_name = register_fonts()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=40,
    )

    title_style = ParagraphStyle(
        "DiagnosisReportTitle",
        fontName=font_name,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#000000"),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "DiagnosisReportSubtitle",
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#000000"),
        spaceAfter=20,
    )
    section_style = ParagraphStyle(
        "DiagnosisReportSection",
        fontName="Roboto-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#000000"),
        spaceBefore=12,
        spaceAfter=7,
    )
    normal_style = ParagraphStyle(
        "DiagnosisReportNormal",
        fontName=font_name,
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#000000"),
    )
    header_style = ParagraphStyle(
        "DiagnosisReportHeader",
        fontName="Roboto-Bold",
        fontSize=7.5,
        leading=9,
        textColor=colors.white,
    )

    records = report_data["records"]
    appointments = set()
    diagnoses = defaultdict(set)
    drugs = defaultdict(int)
    total_drugs = 0

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
            drug_key = (
                drug_title,
                record.get("DRUG_TYPE"),
                record.get("DOSAGE"),
            )
            drugs[drug_key] += 1
            total_drugs += 1

    def as_text(value, fallback="—"):
        if value is None or value == "":
            return fallback
        return escape(str(value)).replace("\n", "<br/>")

    def as_paragraph(value, style=normal_style, fallback="—"):
        return Paragraph(as_text(value, fallback), style)

    def format_appointment_date(value):
        if value is None:
            return "—"
        if hasattr(value, "strftime"):
            return value.strftime("%d.%m.%Y %H:%M")
        return str(value)

    story = [
        Paragraph(
            "Отчет по поставленным диагнозам и назначенным препаратам",
            title_style,
        ),
        Paragraph(
            f"Отчетный период: <b>{as_text(report_data['period'])}</b>",
            subtitle_style,
        ),
        Paragraph("Общие показатели", section_style),
    ]

    summary_table = Table(
        [
            [
                Paragraph("Показатель", header_style),
                Paragraph("Количество", header_style),
            ],
            [
                Paragraph("Приемы (по дате, пациенту и врачу)", normal_style),
                str(len(appointments)),
            ],
            [Paragraph("Диагнозы", normal_style), str(len(diagnoses))],
            [Paragraph("Назначения препаратов", normal_style), str(total_drugs)],
        ],
        colWidths=[350, 150],
        repeatRows=1,
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000000")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#000000")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 12)])

    story.append(Paragraph("Часто встречающиеся диагнозы", section_style))
    disease_rows = [
        [
            Paragraph("Код", header_style),
            Paragraph("Заболевание", header_style),
            Paragraph("Приемы", header_style),
        ]
    ]
    for (code, title), visits in sorted(
        diagnoses.items(), key=lambda item: (-len(item[1]), str(item[0]))
    )[:10]:
        disease_rows.append([as_paragraph(code), as_paragraph(title), str(len(visits))])
    if not diagnoses:
        disease_rows.append(
            [Paragraph("За период диагнозы не указаны.", normal_style), "", ""]
        )

    disease_table = Table(
        disease_rows,
        colWidths=[90, 355, 55],
        repeatRows=1,
        hAlign="LEFT",
    )
    disease_table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000000")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#000000")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]
    if not diagnoses:
        disease_table_style.append(("SPAN", (0, 1), (-1, 1)))
    disease_table.setStyle(TableStyle(disease_table_style))
    story.append(disease_table)

    story.append(Paragraph("Часто назначаемые препараты", section_style))
    drug_rows = [
        [
            Paragraph("Препарат", header_style),
            Paragraph("Тип", header_style),
            Paragraph("Дозировка", header_style),
            Paragraph("Назначения", header_style),
        ]
    ]
    for (title, drug_type, dosage), count in sorted(
        drugs.items(), key=lambda item: (-item[1], str(item[0]))
    )[:10]:
        drug_rows.append(
            [
                as_paragraph(title),
                as_paragraph(drug_type),
                as_paragraph(dosage),
                str(count),
            ]
        )
    if not drugs:
        drug_rows.append(
            [
                Paragraph("За период назначения препаратов отсутствуют.", normal_style),
                "",
                "",
                "",
            ]
        )

    drug_table = Table(
        drug_rows,
        colWidths=[190, 100, 145, 65],
        repeatRows=1,
        hAlign="LEFT",
    )
    drug_table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000000")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#000000")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]
    if not drugs:
        drug_table_style.append(("SPAN", (0, 1), (-1, 1)))
    drug_table.setStyle(TableStyle(drug_table_style))
    story.append(drug_table)

    story.append(Paragraph("Детализация приемов и назначений", section_style))
    details = [
        [
            Paragraph("Дата", header_style),
            Paragraph("Пациент / врач", header_style),
            Paragraph("Диагноз", header_style),
            Paragraph("Препарат / тип", header_style),
            Paragraph("Дозировка", header_style),
            Paragraph("Рекомендации", header_style),
        ]
    ]
    for record in records:
        patient_and_doctor = (
            f"<b>Пациент:</b> {as_text(record.get('PATIENT_NAME'))}<br/>"
            f"<b>Врач:</b> {as_text(record.get('DOCTOR_NAME'))}"
        )
        diagnosis = (
            f"<b>{as_text(record.get('DISEASE_CODE'))}</b><br/>"
            f"{as_text(record.get('DISEASE_TITLE'))}"
        )
        drug = (
            f"<b>{as_text(record.get('DRUG_TITLE'))}</b><br/>"
            f"{as_text(record.get('DRUG_TYPE'))}"
        )
        details.append(
            [
                as_paragraph(format_appointment_date(record.get("APPOINTMENT_DATE"))),
                Paragraph(patient_and_doctor, normal_style),
                Paragraph(diagnosis, normal_style),
                Paragraph(drug, normal_style),
                as_paragraph(record.get("DOSAGE")),
                as_paragraph(record.get("RECOMMENDATIONS")),
            ]
        )

    if records:
        details_table = LongTable(
            details,
            colWidths=[58, 95, 105, 92, 58, 92],
            repeatRows=1,
            hAlign="LEFT",
        )
        details_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000000")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#000000")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F3F6FA")],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(details_table)
    else:
        story.append(
            Paragraph(
                "За выбранный период завершенных приемов не найдено.",
                normal_style,
            )
        )

    doc.build(story, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return buffer
