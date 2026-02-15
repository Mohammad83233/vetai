// MongoDB initialization script
// Creates application user and database

db = db.getSiblingDB('vetai');

db.createUser({
    user: 'vetai_user',
    pwd: 'vetai_password',
    roles: [
        {
            role: 'readWrite',
            db: 'vetai'
        }
    ]
});

// Create collections with validation
db.createCollection('users');
db.createCollection('patients');
db.createCollection('tokens');
db.createCollection('clinical_records');
db.createCollection('diagnoses');
db.createCollection('treatments');
db.createCollection('reports');
db.createCollection('medical_knowledge');

// Create indexes
db.users.createIndex({ "email": 1 }, { unique: true });
db.tokens.createIndex({ "token_number": 1 }, { unique: true });
db.tokens.createIndex({ "status": 1 });
db.tokens.createIndex({ "issued_at": 1 });
db.patients.createIndex({ "owner.phone": 1 });
db.clinical_records.createIndex({ "patient_id": 1 });
db.clinical_records.createIndex({ "doctor_id": 1 });
db.clinical_records.createIndex({ "created_at": -1 });

// Insert initial medical knowledge base
db.medical_knowledge.insertMany([
    {
        disease_name: "Canine Parvovirus",
        species_affected: ["dog"],
        symptoms: ["vomiting", "diarrhea", "lethargy", "loss of appetite", "bloody stool", "fever"],
        treatments: ["IV fluids", "antiemetics", "antibiotics"],
        dosage_rules: {
            "metronidazole": { base_dose_mg_per_kg: 15, frequency: "twice daily", duration_days: 7 },
            "cerenia": { base_dose_mg_per_kg: 2, frequency: "once daily", duration_days: 5 }
        },
        urgency: "emergency",
        prognosis: "Variable - early treatment improves outcomes"
    },
    {
        disease_name: "Feline Upper Respiratory Infection",
        species_affected: ["cat"],
        symptoms: ["sneezing", "nasal discharge", "fever", "lethargy", "eye discharge", "loss of appetite"],
        treatments: ["supportive care", "antibiotics if secondary bacterial", "eye drops"],
        dosage_rules: {
            "amoxicillin": { base_dose_mg_per_kg: 10, frequency: "twice daily", duration_days: 10 }
        },
        urgency: "soon",
        prognosis: "Good with supportive care"
    },
    {
        disease_name: "Kennel Cough",
        species_affected: ["dog"],
        symptoms: ["coughing", "sneezing", "runny nose", "lethargy"],
        treatments: ["rest", "cough suppressants", "antibiotics if severe"],
        dosage_rules: {
            "doxycycline": { base_dose_mg_per_kg: 5, frequency: "twice daily", duration_days: 14 }
        },
        urgency: "routine",
        prognosis: "Excellent - usually self-limiting"
    },
    {
        disease_name: "GI Stasis",
        species_affected: ["rabbit", "guinea_pig"],
        symptoms: ["not eating", "no droppings", "lethargy", "hunched posture", "grinding teeth"],
        treatments: ["gut motility agents", "pain relief", "fluid therapy", "fiber supplementation"],
        dosage_rules: {
            "metoclopramide": { base_dose_mg_per_kg: 0.5, frequency: "three times daily", duration_days: 5 }
        },
        urgency: "urgent",
        prognosis: "Good if treated early"
    }
]);

print('VetAI database initialized successfully');
