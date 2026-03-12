"""
SOAP Report generation API routes.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from io import BytesIO

from ..models.report import (
    SOAPReport,
    SOAPReportCreate,
    SOAPReportExport,
    SubjectiveSection,
    ObjectiveSection,
    AssessmentSection,
    PlanSection
)
from ..models.user import User
from ..services.clinical_service import ClinicalService
from ..services.patient_service import PatientService
from ..services.treatment_service import get_treatment
from .dependencies import get_current_user, require_doctor

router = APIRouter(prefix="/reports", tags=["SOAP Reports"])


async def generate_pdf(report: dict) -> BytesIO:
    """Generate PDF matching the Clinical Report UI style."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable
    )
    
    buffer = BytesIO()
    page_w, page_h = letter
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.4*inch, bottomMargin=0.6*inch,
        leftMargin=0.6*inch, rightMargin=0.6*inch
    )
    
    # --- Colour palette matching the UI ---
    primary_blue = colors.HexColor("#3b5bdb")
    primary_dark = colors.HexColor("#2b4ac7")
    gray_50 = colors.HexColor("#f8f9fa")
    gray_100 = colors.HexColor("#f1f3f5")
    gray_200 = colors.HexColor("#e9ecef")
    gray_400 = colors.HexColor("#adb5bd")
    gray_600 = colors.HexColor("#6c757d")
    gray_800 = colors.HexColor("#343a40")
    gray_900 = colors.HexColor("#212529")
    white = colors.white
    info_bg = colors.HexColor("#e7f5ff")
    info_border = colors.HexColor("#74c0fc")
    pill_bg = colors.HexColor("#dbe4ff")
    
    # --- Styles ---
    styles = getSampleStyleSheet()
    
    header_title = ParagraphStyle(
        'HeaderTitle', fontName='Helvetica-Bold', fontSize=22,
        leading=26, textColor=white, alignment=TA_LEFT
    )
    header_sub = ParagraphStyle(
        'HeaderSub', fontName='Helvetica', fontSize=10,
        leading=13, textColor=colors.HexColor("#c3cfe2"), alignment=TA_LEFT
    )
    status_style = ParagraphStyle(
        'Status', fontName='Helvetica-Bold', fontSize=8,
        textColor=white, alignment=TA_CENTER
    )
    section_title = ParagraphStyle(
        'SectionTitle', fontName='Helvetica-Bold', fontSize=10,
        leading=14, textColor=gray_800, spaceAfter=6,
        textTransform='uppercase', tracking=0.8
    )
    label_style = ParagraphStyle(
        'Label', fontName='Helvetica-Bold', fontSize=7.5,
        leading=10, textColor=gray_400, textTransform='uppercase'
    )
    value_style = ParagraphStyle(
        'Value', fontName='Helvetica', fontSize=10,
        leading=13, textColor=gray_900
    )
    diagnosis_name = ParagraphStyle(
        'DiagName', fontName='Helvetica-Bold', fontSize=16,
        leading=20, textColor=gray_900
    )
    diag_label = ParagraphStyle(
        'DiagLabel', fontName='Helvetica-Bold', fontSize=7.5,
        leading=10, textColor=gray_600, textTransform='uppercase'
    )
    med_name_style = ParagraphStyle(
        'MedName', fontName='Helvetica-Bold', fontSize=10,
        leading=13, textColor=gray_900
    )
    med_detail = ParagraphStyle(
        'MedDetail', fontName='Helvetica', fontSize=9,
        leading=12, textColor=gray_600
    )
    note_title = ParagraphStyle(
        'NoteTitle', fontName='Helvetica-Bold', fontSize=8,
        leading=10, textColor=gray_800, textTransform='uppercase'
    )
    note_text = ParagraphStyle(
        'NoteText', fontName='Helvetica', fontSize=9,
        leading=12, textColor=gray_800
    )
    footer_style = ParagraphStyle(
        'Footer', fontName='Helvetica', fontSize=9,
        leading=12, textColor=gray_600
    )
    footer_bold = ParagraphStyle(
        'FooterBold', fontName='Helvetica-Bold', fontSize=9,
        leading=12, textColor=gray_800
    )
    
    story = []
    usable = page_w - doc.leftMargin - doc.rightMargin
    
    # ═══════════════════════════════════════════
    # HEADER — blue gradient-style banner
    # ═══════════════════════════════════════════
    status_text = report.get("status", "draft").upper()
    status_color = colors.HexColor("#2ecc71") if status_text == "FINAL" or status_text == "FINALIZED" else colors.HexColor("#f39c12")
    
    header_data = [[
        Paragraph("🩺  <b>Clinical Report</b>", header_title),
        Paragraph(status_text, status_style)
    ]]
    
    header_tbl = Table(header_data, colWidths=[usable - 1.2*inch, 1.2*inch])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), primary_blue),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 18),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (0, 0), 20),
        ('RIGHTPADDING', (-1, -1), (-1, -1), 20),
    ]))
    story.append(header_tbl)
    
    # Sub-header row
    sub_data = [[Paragraph("VetAI Clinical Decision Support System", header_sub), ""]]
    sub_tbl = Table(sub_data, colWidths=[usable, 0])
    sub_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), primary_dark),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (0, 0), 20),
    ]))
    story.append(sub_tbl)
    story.append(Spacer(1, 20))
    
    # ═══════════════════════════════════════════
    # SECTION: Patient Information
    # ═══════════════════════════════════════════
    story.append(Paragraph("👤  PATIENT INFORMATION", section_title))
    story.append(HRFlowable(width="100%", thickness=1.5, color=gray_200, spaceAfter=10))
    
    breed = report.get("breed", "")
    species = report.get("species", "N/A")
    species_breed = f"{species} ({breed})" if breed else species
    date_str = str(report.get("created_at", ""))[:10]
    
    # Patient info as a 3-column grid
    col_w = usable / 3
    patient_grid = [
        [
            [Paragraph("PATIENT NAME", label_style), Paragraph(report.get("patient_name", "N/A"), value_style)],
            [Paragraph("SPECIES / BREED", label_style), Paragraph(species_breed, value_style)],
            [Paragraph("AGE / WEIGHT", label_style), Paragraph(f"{report.get('age_months', 0)}m / {report.get('weight_kg', 'N/A')}kg", value_style)],
        ],
        [
            [Paragraph("OWNER", label_style), Paragraph(report.get("owner_name", "N/A"), value_style)],
            [Paragraph("DATE ISSUED", label_style), Paragraph(date_str, value_style)],
            [],
        ]
    ]
    
    # Flatten inner lists into Table cells
    def _cell(items):
        if not items:
            return Paragraph("", value_style)
        tbl = Table([[i] for i in items], colWidths=[col_w - 12])
        tbl.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        return tbl
    
    rows = [[_cell(c) for c in row] for row in patient_grid]
    info_table = Table(rows, colWidths=[col_w]*3)
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))
    
    # ═══════════════════════════════════════════
    # SECTION: Diagnosed Diseases
    # ═══════════════════════════════════════════
    assessment = report.get("assessment", {})
    story.append(Paragraph("⚕  DIAGNOSED DISEASES", section_title))
    story.append(HRFlowable(width="100%", thickness=1.5, color=gray_200, spaceAfter=10))
    
    # Diagnosis card
    diag_content = [
        [Paragraph("PRIMARY DIAGNOSIS", diag_label)],
        [Spacer(1, 4)],
        [Paragraph(assessment.get("primary_diagnosis", "Pending"), diagnosis_name)],
    ]
    diag_inner = Table(diag_content, colWidths=[usable - 40])
    diag_inner.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    diag_card = Table([[diag_inner]], colWidths=[usable - 12])
    diag_card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), gray_50),
        ('BOX', (0, 0), (-1, -1), 0.75, gray_200),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
    ]))
    story.append(diag_card)
    story.append(Spacer(1, 20))
    
    # ═══════════════════════════════════════════
    # SECTION: Treatment Plan
    # ═══════════════════════════════════════════
    plan = report.get("plan", {})
    story.append(Paragraph("💊  TREATMENT PLAN", section_title))
    story.append(HRFlowable(width="100%", thickness=1.5, color=gray_200, spaceAfter=10))
    
    medications = plan.get("medications", [])
    if medications:
        for med in medications:
            med_n = med.get("name", "Unknown")
            dosage = med.get("dosage", {})
            instructions = dosage.get("instructions") or None
            
            # Build detail line
            dose_parts = []
            if dosage.get("dose_mg"):
                dose_parts.append(f"{dosage['dose_mg']}mg")
            if dosage.get("duration_days"):
                dose_parts.append(f"{dosage['duration_days']} days")
            dose_line = " • ".join(dose_parts)
            
            # Pill icon cell + text cell
            pill_icon = Table([["💊"]], colWidths=[32], rowHeights=[32])
            pill_icon.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), pill_bg),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROUNDEDCORNERS', [16, 16, 16, 16]),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            text_parts = [[Paragraph(med_n, med_name_style)]]
            if instructions:
                text_parts.append([Paragraph(instructions, med_detail)])
            if dose_line:
                text_parts.append([Paragraph(dose_line, ParagraphStyle(
                    'DoseLine', fontName='Helvetica-Bold', fontSize=7.5,
                    leading=10, textColor=gray_400, textTransform='uppercase'
                ))])
            
            text_tbl = Table(text_parts, colWidths=[usable - 70])
            text_tbl.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            
            med_row = Table([[pill_icon, text_tbl]], colWidths=[42, usable - 54])
            med_row.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOX', (0, 0), (-1, -1), 0.5, gray_200),
                ('ROUNDEDCORNERS', [4, 4, 4, 4]),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (0, 0), 10),
                ('LEFTPADDING', (1, 0), (1, 0), 8),
                ('RIGHTPADDING', (-1, -1), (-1, -1), 10),
            ]))
            story.append(med_row)
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("<i>No medications prescribed.</i>", ParagraphStyle(
            'NoMeds', fontName='Helvetica-Oblique', fontSize=10, textColor=gray_400
        )))
    
    # Dietary / Notes box
    if plan.get("dietary_recommendations"):
        story.append(Spacer(1, 10))
        note_content = [
            [Paragraph("NOTES", note_title)],
            [Spacer(1, 2)],
            [Paragraph(plan["dietary_recommendations"], note_text)],
        ]
        note_inner = Table(note_content, colWidths=[usable - 44])
        note_inner.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        note_box = Table([[note_inner]], colWidths=[usable - 16])
        note_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), info_bg),
            ('BOX', (0, 0), (-1, -1), 0.75, info_border),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ]))
        story.append(note_box)
    
    # Follow-up
    if plan.get("follow_up_appointments"):
        story.append(Spacer(1, 10))
        follow_up_text = ", ".join(plan["follow_up_appointments"])
        story.append(Paragraph(f"<b>Follow-up:</b> {follow_up_text}", med_detail))
    
    story.append(Spacer(1, 24))
    
    # ═══════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════
    story.append(HRFlowable(width="100%", thickness=0.75, color=gray_200, spaceAfter=8))
    
    footer_data = [[
        Paragraph(f"<b>Doctor:</b> {report.get('doctor_name', 'N/A')}", footer_style),
        Paragraph(f"<b>Clinic:</b> {report.get('clinic_name', 'VetAI Clinic')}", footer_style),
    ]]
    footer_tbl = Table(footer_data, colWidths=[usable/2, usable/2])
    footer_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), gray_50),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (0, 0), 12),
        ('RIGHTPADDING', (-1, -1), (-1, -1), 12),
    ]))
    story.append(footer_tbl)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


@router.post("/generate", response_model=SOAPReport, response_model_by_alias=False)
async def generate_report(
    request: SOAPReportCreate,
    current_user: User = Depends(require_doctor)
):
    """Generate a SOAP clinical report."""
    from datetime import datetime
    from bson import ObjectId
    from ..database import Database
    
    # Get patient info
    patient = await PatientService.get_patient(request.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Get clinical record
    record = await ClinicalService.get_record(request.clinical_record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical record not found"
        )
    
    # Get diagnosis and treatment if available
    diagnoses = Database.get_collection("diagnoses")
    treatments = Database.get_collection("treatments")
    
    diagnosis = None
    treatment = None
    
    if request.diagnosis_id:
        try:
            diagnosis = await diagnoses.find_one({"_id": ObjectId(request.diagnosis_id)})
        except:
            pass
    
    if request.treatment_id:
        try:
            treatment = await treatments.find_one({"_id": ObjectId(request.treatment_id)})
        except:
            pass
    
    # Build SOAP sections
    clinical_input = record.clinical_input
    
    subjective = SubjectiveSection(
        chief_complaint=clinical_input.chief_complaint or clinical_input.text_description or "See clinical notes",
        history_of_present_illness=clinical_input.history_of_present_illness,
        owner_observations=[s.name for s in (clinical_input.symptoms or [])],
        raw_text=clinical_input.text_description
    )
    
    objective = ObjectiveSection(
        vital_signs=clinical_input.vital_signs.model_dump() if clinical_input.vital_signs else None,
        weight_kg=patient.weight_kg,
        physical_exam_findings=["See clinical record for detailed findings"],
        image_references=[img.image_id for img in (clinical_input.images or [])]
    )
    
    primary_disease = diagnosis.get("predictions", [{}])[0].get("disease_name", "Pending") if diagnosis else "Pending evaluation"
    
    assessment = AssessmentSection(
        primary_diagnosis=primary_disease,
        differential_diagnoses=[p.get("disease_name") for p in diagnosis.get("predictions", [])[1:4]] if diagnosis else [],
        ai_predictions=diagnosis.get("predictions", [])[:3] if diagnosis else None,
        ai_confidence=None,
        prognosis="Good with appropriate treatment" if diagnosis else "Pending evaluation"
    )
    
    # Build plan: use MongoDB treatment if available, otherwise look up treatment KB
    if treatment:
        plan = PlanSection(
            medications=treatment.get("medications", []),
            dietary_recommendations=treatment.get("dietary_recommendations"),
            activity_restrictions=treatment.get("activity_restrictions"),
            follow_up_appointments=treatment.get("follow_up_schedule", []),
            monitoring_instructions=treatment.get("monitoring_instructions"),
            emergency_instructions=treatment.get("emergency_instructions") or "Contact clinic if symptoms worsen"
        )
    else:
        # Look up treatment knowledge base by disease name
        kb_treatment = get_treatment(primary_disease)
        if kb_treatment.get("found"):
            plan_medications = [
                {"name": med, "dosage": {"instructions": None, "dose_mg": None, "duration_days": None}}
                for med in kb_treatment.get("medicines", [])
            ]
            plan = PlanSection(
                medications=plan_medications,
                dietary_recommendations=kb_treatment.get("notes"),
                follow_up_appointments=[f"Follow-up after {kb_treatment.get('treatment_duration', 'as needed')}"],
                emergency_instructions="Contact clinic if symptoms worsen"
            )
        else:
            plan = PlanSection(
                medications=[],
                follow_up_appointments=["Schedule follow-up as needed"],
                emergency_instructions="Contact clinic if symptoms worsen"
            )
    
    # Get doctor name
    users = Database.get_collection("users")
    doctor_user = await users.find_one({"_id": ObjectId(current_user.id)})
    doctor_name = doctor_user.get("full_name", "Unknown") if doctor_user else current_user.full_name
    
    # Create report document
    reports = Database.get_collection("reports")
    
    report_doc = {
        "patient_id": request.patient_id,
        "clinical_record_id": request.clinical_record_id,
        "diagnosis_id": request.diagnosis_id,
        "treatment_id": request.treatment_id,
        "token_id": record.token_id,
        "patient_name": patient.name,
        "species": patient.species.value if hasattr(patient.species, 'value') else patient.species,
        "breed": patient.breed,
        "weight_kg": patient.weight_kg,
        "age_months": patient.age_months,
        "owner_name": patient.owner.name,
        "subjective": subjective.model_dump(),
        "objective": objective.model_dump(),
        "assessment": assessment.model_dump(),
        "plan": plan.model_dump(),
        "created_at": datetime.utcnow(),
        "created_by": current_user.id,
        "doctor_name": doctor_name,
        "clinic_name": "VetAI Clinic",
        "status": "draft"
    }
    
    result = await reports.insert_one(report_doc)
    report_doc["_id"] = str(result.inserted_id)
    
    # Link to clinical record
    await ClinicalService.link_report(request.clinical_record_id, report_doc["_id"])
    
    return SOAPReport(**report_doc)


@router.get("/{report_id}", response_model=SOAPReport, response_model_by_alias=False)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get SOAP report by ID."""
    from bson import ObjectId
    from ..database import Database
    
    reports = Database.get_collection("reports")
    
    try:
        report = await reports.find_one({"_id": ObjectId(report_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    report["_id"] = str(report["_id"])
    return SOAPReport(**report)


@router.post("/{report_id}/finalize", response_model=SOAPReport, response_model_by_alias=False)
async def finalize_report(
    report_id: str,
    current_user: User = Depends(require_doctor)
):
    """Finalize a SOAP report."""
    from datetime import datetime
    from bson import ObjectId
    from ..database import Database
    
    reports = Database.get_collection("reports")
    
    result = await reports.find_one_and_update(
        {"_id": ObjectId(report_id)},
        {
            "$set": {
                "status": "final",
                "finalized_at": datetime.utcnow()
            }
        },
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    result["_id"] = str(result["_id"])
    
    # Auto-complete the associated clinical record
    clinical_record_id = result.get("clinical_record_id")
    if clinical_record_id:
        try:
            await ClinicalService.complete_record(clinical_record_id)
        except Exception:
            pass  # Don't fail report finalization if record completion fails
    
    return SOAPReport(**result)


@router.post("/export")
async def export_report(
    request: SOAPReportExport,
    current_user: User = Depends(get_current_user)
):
    """Export SOAP report in specified format."""
    from bson import ObjectId
    from ..database import Database
    
    reports = Database.get_collection("reports")
    
    try:
        report = await reports.find_one({"_id": ObjectId(request.report_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    report["_id"] = str(report["_id"])
    
    if request.format == "pdf":
        pdf_buffer = await generate_pdf(report)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=SOAP_Report_{report['patient_name']}_{str(report['created_at'])[:10]}.pdf"
            }
        )
    elif request.format == "json":
        return report
    elif request.format == "html":
        # Simple HTML export
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>SOAP Report - {report['patient_name']}</title></head>
        <body>
            <h1>Veterinary Clinical Report</h1>
            <h2>Patient: {report['patient_name']}</h2>
            <p>Species: {report['species']} | Breed: {report.get('breed', 'N/A')}</p>
            <p>Weight: {report['weight_kg']} kg | Age: {report['age_months']} months</p>
            <hr>
            <h3>S - Subjective</h3>
            <p>{report['subjective'].get('chief_complaint', 'N/A')}</p>
            <h3>O - Objective</h3>
            <p>Vitals: {report['objective'].get('vital_signs', {})}</p>
            <h3>A - Assessment</h3>
            <p>{report['assessment'].get('primary_diagnosis', 'N/A')}</p>
            <h3>P - Plan</h3>
            <p>Medications: {len(report['plan'].get('medications', []))} prescribed</p>
            <hr>
            <p>Doctor: {report['doctor_name']} | Date: {str(report['created_at'])[:10]}</p>
        </body>
        </html>
        """
        return StreamingResponse(
            BytesIO(html.encode()),
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=SOAP_Report_{report['patient_name']}.html"
            }
        )
