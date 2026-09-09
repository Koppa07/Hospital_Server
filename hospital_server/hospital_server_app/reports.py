import io
import os
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_fonts():
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("DejaVu", font_path))
        return "DejaVu"
    return "Helvetica"


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
        self.setFont("Helvetica", 9)
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
