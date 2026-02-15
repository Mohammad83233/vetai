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
from .dependencies import get_current_user, require_doctor

router = APIRouter(prefix="/reports", tags=["SOAP Reports"])


async def generate_pdf(report: dict) -> BytesIO:
    """Generate PDF from SOAP report."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=12)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=12, spaceAfter=6, textColor=colors.darkblue)
    normal_style = styles['Normal']
    
    story = []
    
    # Header
    story.append(Paragraph(f"<b>VETERINARY CLINICAL REPORT</b>", title_style))
    story.append(Paragraph(f"VetAI Clinical Decision Support System", normal_style))
    story.append(Spacer(1, 12))
    
    # Patient Info Table
    patient_data = [
        ["Patient Name:", report.get("patient_name", "N/A"), "Species:", report.get("species", "N/A")],
        ["Breed:", report.get("breed", "N/A"), "Weight:", f"{report.get('weight_kg', 'N/A')} kg"],
        ["Age:", f"{report.get('age_months', 0)} months", "Owner:", report.get("owner_name", "N/A")],
        ["Doctor:", report.get("doctor_name", "N/A"), "Date:", str(report.get("created_at", "N/A"))[:10]]
    ]
    
    patient_table = Table(patient_data, colWidths=[1.2*inch, 2*inch, 1*inch, 2*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # SOAP Sections
    subjective = report.get("subjective", {})
    story.append(Paragraph("<b>S - SUBJECTIVE</b>", heading_style))
    story.append(Paragraph(f"<b>Chief Complaint:</b> {subjective.get('chief_complaint', 'N/A')}", normal_style))
    if subjective.get('history_of_present_illness'):
        story.append(Paragraph(f"<b>History:</b> {subjective.get('history_of_present_illness')}", normal_style))
    if subjective.get('owner_observations'):
        story.append(Paragraph(f"<b>Owner Observations:</b> {', '.join(subjective.get('owner_observations', []))}", normal_style))
    story.append(Spacer(1, 12))
    
    objective = report.get("objective", {})
    story.append(Paragraph("<b>O - OBJECTIVE</b>", heading_style))
    vitals = objective.get('vital_signs', {})
    if vitals:
        vitals_text = ", ".join([f"{k}: {v}" for k, v in vitals.items() if v])
        story.append(Paragraph(f"<b>Vital Signs:</b> {vitals_text}", normal_style))
    if objective.get('physical_exam_findings'):
        story.append(Paragraph(f"<b>Physical Exam:</b> {', '.join(objective.get('physical_exam_findings', []))}", normal_style))
    story.append(Spacer(1, 12))
    
    assessment = report.get("assessment", {})
    story.append(Paragraph("<b>A - ASSESSMENT</b>", heading_style))
    story.append(Paragraph(f"<b>Primary Diagnosis:</b> {assessment.get('primary_diagnosis', 'N/A')}", normal_style))
    if assessment.get('differential_diagnoses'):
        story.append(Paragraph(f"<b>Differentials:</b> {', '.join(assessment.get('differential_diagnoses', []))}", normal_style))
    if assessment.get('prognosis'):
        story.append(Paragraph(f"<b>Prognosis:</b> {assessment.get('prognosis')}", normal_style))
    story.append(Spacer(1, 12))
    
    plan = report.get("plan", {})
    story.append(Paragraph("<b>P - PLAN</b>", heading_style))
    if plan.get('medications'):
        story.append(Paragraph("<b>Medications:</b>", normal_style))
        for med in plan.get('medications', []):
            med_name = med.get('name', 'Unknown')
            dosage = med.get('dosage', {})
            story.append(Paragraph(f"  • {med_name}: {dosage.get('instructions', 'As directed')}", normal_style))
    if plan.get('dietary_recommendations'):
        story.append(Paragraph(f"<b>Diet:</b> {plan.get('dietary_recommendations')}", normal_style))
    if plan.get('follow_up_appointments'):
        story.append(Paragraph(f"<b>Follow-up:</b> {', '.join(plan.get('follow_up_appointments', []))}", normal_style))
    if plan.get('emergency_instructions'):
        story.append(Paragraph(f"<b>Emergency:</b> {plan.get('emergency_instructions')}", normal_style))
    
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
    
    assessment = AssessmentSection(
        primary_diagnosis=diagnosis.get("predictions", [{}])[0].get("disease_name", "Pending") if diagnosis else "Pending evaluation",
        differential_diagnoses=[p.get("disease_name") for p in diagnosis.get("predictions", [])[1:4]] if diagnosis else [],
        ai_predictions=diagnosis.get("predictions", [])[:3] if diagnosis else None,
        ai_confidence=diagnosis.get("confidence_score") if diagnosis else None,
        prognosis="Good with appropriate treatment" if diagnosis else "Pending evaluation"
    )
    
    plan = PlanSection(
        medications=treatment.get("medications", []) if treatment else [],
        dietary_recommendations=treatment.get("dietary_recommendations") if treatment else None,
        activity_restrictions=treatment.get("activity_restrictions") if treatment else None,
        follow_up_appointments=treatment.get("follow_up_schedule", []) if treatment else ["Schedule follow-up as needed"],
        monitoring_instructions=treatment.get("monitoring_instructions") if treatment else None,
        emergency_instructions=treatment.get("emergency_instructions") if treatment else "Contact clinic if symptoms worsen"
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
