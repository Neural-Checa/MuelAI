"""
Servicio para generar reportes PDF de historial médico usando fpdf2.
Usa fuente Arial TTF del sistema para soporte Unicode completo (español).
"""
import os
from datetime import datetime

from fpdf import FPDF
from sqlalchemy.orm import Session

from src.database.models import Appointment, Doctor, MedicalHistory, Patient
from src.database.connection import CLINIC_NAME, CLINIC_PHONE, CLINIC_WEBSITE, CLINIC_ADDRESS


# ── Colores ───────────────────────────────────────────────────────────
PRIMARY = (14, 165, 233)       # #0EA5E9
SECONDARY = (99, 102, 241)     # #6366F1
ACCENT = (5, 150, 105)         # #059669
DARK = (30, 41, 59)            # #1E293B
LIGHT_BG = (241, 245, 249)     # #F1F5F9
TEXT_GRAY = (71, 85, 105)      # #475569
WHITE = (255, 255, 255)

# ── Fuentes TTF del sistema ───────────────────────────────────────────
FONTS_DIR = r"C:\Windows\Fonts"


class MedicalReportPDF(FPDF):
    """PDF personalizado con header y footer de la clínica."""

    def __init__(self, patient_name: str = ""):
        super().__init__()
        self.patient_name = patient_name
        self._register_fonts()

    def _register_fonts(self):
        """Registra fuentes TTF con soporte Unicode."""
        # Arial (disponible en todos los Windows)
        self.add_font("ArialUni", "", os.path.join(FONTS_DIR, "arial.ttf"), uni=True)
        self.add_font("ArialUni", "B", os.path.join(FONTS_DIR, "arialbd.ttf"), uni=True)
        self.add_font("ArialUni", "I", os.path.join(FONTS_DIR, "ariali.ttf"), uni=True)
        self.add_font("ArialUni", "BI", os.path.join(FONTS_DIR, "arialbi.ttf"), uni=True)

    def _font(self, style: str = "", size: int = 10):
        """Helper para setear fuente Unicode."""
        self.set_font("ArialUni", style, size)

    def header(self):
        # Barra superior de color
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 3, "F")

        self.set_y(8)
        self._font("B", 14)
        self.set_text_color(*PRIMARY)
        self.cell(0, 8, CLINIC_NAME, new_x="LMARGIN", new_y="NEXT")

        self.set_y(8)
        self._font("", 8)
        self.set_text_color(*TEXT_GRAY)
        self.cell(0, 8, "Historial Médico", align="R", new_x="LMARGIN", new_y="NEXT")

        # Línea divisora
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.6)
        self.line(10, 18, 200, 18)
        self.set_y(22)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(*LIGHT_BG)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())

        self.set_y(-16)
        self._font("", 7)
        self.set_text_color(*TEXT_GRAY)
        self.cell(60, 5, CLINIC_PHONE)
        self.cell(70, 5, f"Página {self.page_no()}/{{nb}}", align="C")
        self.cell(60, 5, CLINIC_WEBSITE, align="R")

    def section_title(self, title: str):
        self.ln(6)
        self._font("B", 13)
        self.set_text_color(*PRIMARY)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def subsection_title(self, title: str):
        self.ln(3)
        self._font("B", 10)
        self.set_text_color(*SECONDARY)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def info_row(self, label: str, value: str, stripe: bool = False):
        if stripe:
            self.set_fill_color(*LIGHT_BG)
        else:
            self.set_fill_color(*WHITE)

        self._font("B", 9)
        self.set_text_color(*DARK)
        self.cell(50, 7, label, fill=True)

        self._font("", 9)
        self.set_text_color(*TEXT_GRAY)
        self.cell(0, 7, value, fill=True, new_x="LMARGIN", new_y="NEXT")

    def colored_bullet(self, color: tuple, label: str, text: str):
        x = self.get_x()
        y = self.get_y()

        # Bullet circle
        self.set_fill_color(*color)
        self.ellipse(x + 2, y + 2, 3, 3, "F")

        # Label
        self.set_x(x + 8)
        self._font("B", 9)
        self.set_text_color(*DARK)
        self.cell(28, 7, f"{label}:")

        # Text
        self._font("", 9)
        self.set_text_color(*TEXT_GRAY)
        remaining_w = 190 - 8 - 28
        self.multi_cell(remaining_w, 5, text)
        self.ln(1)


def generate_report_pdf(session: Session, patient_id: int) -> bytes:
    """
    Genera un PDF profesional con el historial médico del paciente.
    Retorna los bytes del PDF listo para descargar.
    """
    patient = session.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return b""

    history = (
        session.query(MedicalHistory)
        .filter(MedicalHistory.patient_id == patient_id)
        .order_by(MedicalHistory.date.desc())
        .all()
    )

    appointments = (
        session.query(Appointment)
        .filter(Appointment.patient_id == patient_id, Appointment.status == "scheduled")
        .order_by(Appointment.appointment_date, Appointment.start_time)
        .all()
    )

    today = datetime.now().strftime("%d/%m/%Y")
    days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    pdf = MedicalReportPDF(patient_name=patient.name)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=25)

    # ══════════════════════════════════════════════════════
    #  PORTADA
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.ln(30)

    pdf._font("B", 28)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 15, CLINIC_NAME, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf._font("", 10)
    pdf.set_text_color(*TEXT_GRAY)
    pdf.cell(0, 6, CLINIC_ADDRESS, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Tel: {CLINIC_PHONE}  |  Web: {CLINIC_WEBSITE}", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(15)
    pdf.set_draw_color(*PRIMARY)
    pdf.set_line_width(1.2)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())

    pdf.ln(12)
    pdf._font("B", 20)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 12, "Reporte de Historial Médico", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf._font("B", 16)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 10, patient.name, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(12)
    pdf.set_draw_color(*PRIMARY)
    pdf.set_line_width(1.2)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())

    pdf.ln(20)
    pdf._font("", 10)
    pdf.set_text_color(*TEXT_GRAY)
    pdf.cell(0, 6, f"Fecha de generación: {today}", align="C", new_x="LMARGIN", new_y="NEXT")

    # ══════════════════════════════════════════════════════
    #  DATOS DEL PACIENTE
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title("Datos del Paciente")

    pdf.info_row("Nombre Completo", patient.name, stripe=True)
    pdf.info_row("DNI", patient.dni, stripe=False)
    pdf.info_row("Teléfono", patient.phone or "No registrado", stripe=True)
    pdf.info_row("Correo Electrónico", patient.email or "No registrado", stripe=False)
    pdf.info_row(
        "Fecha de Registro",
        patient.created_at.strftime("%d/%m/%Y") if patient.created_at else "N/A",
        stripe=True,
    )

    # ══════════════════════════════════════════════════════
    #  HISTORIAL MÉDICO
    # ══════════════════════════════════════════════════════
    pdf.section_title("Historial Médico")

    if history:
        # Tabla resumen
        pdf.set_fill_color(*DARK)
        pdf.set_text_color(*WHITE)
        pdf._font("B", 9)
        pdf.cell(25, 7, "Fecha", fill=True, border=1)
        pdf.cell(70, 7, "Diagnóstico", fill=True, border=1)
        pdf.cell(0, 7, "Tratamiento", fill=True, border=1, new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(*DARK)
        for i, record in enumerate(history):
            if i % 2 == 0:
                pdf.set_fill_color(*LIGHT_BG)
            else:
                pdf.set_fill_color(*WHITE)

            date_str = record.date.strftime("%d/%m/%Y")
            pdf._font("", 8)
            pdf.cell(25, 6, date_str, fill=True, border=1)

            diag = (record.diagnosis[:48] + "...") if len(record.diagnosis) > 48 else record.diagnosis
            pdf.cell(70, 6, diag, fill=True, border=1)

            treat = (record.treatment[:55] + "...") if len(record.treatment) > 55 else record.treatment
            pdf.cell(0, 6, treat, fill=True, border=1, new_x="LMARGIN", new_y="NEXT")

        # Detalle
        pdf.ln(6)
        pdf.subsection_title("Detalle de Consultas")

        for i, record in enumerate(history, 1):
            if pdf.get_y() > 240:
                pdf.add_page()

            date_str = record.date.strftime("%d/%m/%Y")

            pdf.set_fill_color(*LIGHT_BG)
            pdf._font("B", 10)
            pdf.set_text_color(*DARK)
            pdf.cell(0, 8, f"  Consulta {i} - {date_str}", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            pdf.set_x(15)
            pdf.colored_bullet(PRIMARY, "Diagnóstico", record.diagnosis)

            pdf.set_x(15)
            pdf.colored_bullet(ACCENT, "Tratamiento", record.treatment)

            notes = record.notes or "Sin observaciones adicionales."
            pdf.set_x(15)
            pdf.colored_bullet(SECONDARY, "Observaciones", notes)

            pdf.ln(3)
    else:
        pdf._font("I", 10)
        pdf.set_text_color(*TEXT_GRAY)
        pdf.cell(0, 8, "El paciente no tiene historial médico registrado.", new_x="LMARGIN", new_y="NEXT")

    # ══════════════════════════════════════════════════════
    #  CITAS PROGRAMADAS
    # ══════════════════════════════════════════════════════
    if pdf.get_y() > 230:
        pdf.add_page()

    pdf.section_title("Citas Programadas")

    if appointments:
        pdf.set_fill_color(*DARK)
        pdf.set_text_color(*WHITE)
        pdf._font("B", 9)
        pdf.cell(35, 7, "Fecha", fill=True, border=1)
        pdf.cell(25, 7, "Hora", fill=True, border=1)
        pdf.cell(45, 7, "Doctor", fill=True, border=1)
        pdf.cell(0, 7, "Motivo", fill=True, border=1, new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(*DARK)
        for i, appt in enumerate(appointments):
            if i % 2 == 0:
                pdf.set_fill_color(*LIGHT_BG)
            else:
                pdf.set_fill_color(*WHITE)

            day_name = days_es[appt.appointment_date.weekday()][:3]
            date_str = f"{day_name} {appt.appointment_date.strftime('%d/%m/%Y')}"
            time_str = f"{appt.start_time.strftime('%H:%M')}-{appt.end_time.strftime('%H:%M')}"

            doctor = session.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
            doc_name = doctor.name if doctor else f"Doctor #{appt.doctor_id}"

            reason = appt.reason or "Sin motivo"
            if len(reason) > 38:
                reason = reason[:38] + "..."

            pdf._font("", 8)
            pdf.cell(35, 6, date_str, fill=True, border=1)
            pdf.cell(25, 6, time_str, fill=True, border=1)
            pdf.cell(45, 6, doc_name, fill=True, border=1)
            pdf.cell(0, 6, reason, fill=True, border=1, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf._font("I", 10)
        pdf.set_text_color(*TEXT_GRAY)
        pdf.cell(0, 8, "No hay citas programadas actualmente.", new_x="LMARGIN", new_y="NEXT")

    # ══════════════════════════════════════════════════════
    #  PIE DEL DOCUMENTO
    # ══════════════════════════════════════════════════════
    pdf.ln(15)

    pdf.set_draw_color(*PRIMARY)
    pdf.set_line_width(0.5)
    y_line = pdf.get_y()
    if y_line > 250:
        pdf.add_page()
        y_line = pdf.get_y() + 10

    pdf.line(30, y_line, 180, y_line)
    pdf.ln(6)

    pdf._font("", 8)
    pdf.set_text_color(*TEXT_GRAY)
    pdf.cell(0, 5, f"Este documento fue generado automáticamente por {CLINIC_NAME}.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Para consultas, comuníquese al {CLINIC_PHONE} o visite {CLINIC_WEBSITE}.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf._font("I", 7)
    pdf.cell(0, 4, f"Documento generado el {today} - Confidencial", align="C", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()
