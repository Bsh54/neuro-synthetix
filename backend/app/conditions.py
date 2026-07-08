"""Data backbone : lexique de symptomes (multilingue) + carte condition -> symptomes.

Centralise pour extract.py, ingest.py et kb_builder.py.
Le lien symptome -> condition est une table medicale curee (orientation, pas
diagnostic). Les conditions servent de requetes vers les registres d'essais.
"""
from __future__ import annotations

# symptome canonique -> variantes declenchantes (EN / FR / hindi translittere), minuscules
SYMPTOM_LEXICON: dict[str, list[str]] = {
    "fever": ["fever", "fievre", "bukhar", "temperature", "high temperature"],
    "cough": ["cough", "toux", "tousse", "khansi"],
    "weight loss": ["weight loss", "perte de poids", "perdu du poids", "maigri", "vajan kam", "losing weight"],
    "night sweats": ["night sweats", "sueurs nocturnes", "sue la nuit", "raat ko pasina"],
    "chest pain": ["chest pain", "douleur thoracique", "mal a la poitrine", "seene mein dard"],
    "breathlessness": ["breathless", "shortness of breath", "essoufflement", "difficulte a respirer", "saans", "saans phoolna"],
    "wheezing": ["wheezing", "sifflement", "respiration sifflante"],
    "headache": ["headache", "mal de tete", "mal a la tete", "sar dard", "sir dard"],
    "dizziness": ["dizziness", "vertige", "vertiges", "chakkar", "lightheaded"],
    "fatigue": ["fatigue", "tired", "tiredness", "epuisement", "faible", "kamzori", "thakan"],
    "bone pain": ["bone pain", "mal aux os", "douleur osseuse", "haddi dard"],
    "joint pain": ["joint pain", "douleur articulaire", "mal aux articulations", "jodon mein dard", "arthralgia"],
    "stiffness": ["stiffness", "raideur", "akadan"],
    "swelling": ["swelling", "gonflement", "sujan", "oedema", "edema"],
    "nausea": ["nausea", "nausee", "envie de vomir", "matli", "ulti jaisa"],
    "vomiting": ["vomiting", "vomissement", "ulti", "throwing up"],
    "abdominal pain": ["abdominal pain", "stomach pain", "mal au ventre", "douleur abdominale", "pet dard", "pet mein dard"],
    "bloating": ["bloating", "ballonnement", "pet phoolna"],
    "diarrhea": ["diarrhea", "diarrhee", "dast", "loose motion"],
    "constipation": ["constipation", "kabz"],
    "thirst": ["excessive thirst", "thirst", "soif", "pyaas", "bahut pyaas"],
    "frequent urination": ["frequent urination", "urination", "urine souvent", "baar baar peshab", "peshab"],
    "blurred vision": ["blurred vision", "vision floue", "dhundhla dikhna", "blurry vision"],
    "palpitations": ["palpitations", "heart racing", "coeur qui bat vite", "dil ki dhadkan"],
    "chills": ["chills", "frissons", "thand lagna", "kampkampi"],
    "loss of appetite": ["loss of appetite", "no appetite", "perte d appetit", "bhookh nahi", "bhook kam"],
    "sadness": ["sadness", "depressed", "tristesse", "udaas", "low mood", "hopeless"],
    "insomnia": ["insomnia", "cannot sleep", "insomnie", "neend nahi", "trouble sleeping"],
    "jaundice": ["jaundice", "yellow eyes", "yellow skin", "jaunisse", "piliya"],
    "numbness": ["numbness", "engourdissement", "sunnpan", "tingling"],
    "weakness": ["weakness", "faiblesse", "kamzori", "one side weakness"],
    "confusion": ["confusion", "confus", "bhram"],
    "seizures": ["seizures", "convulsions", "fits", "daura", "mirgi"],
    "lump": ["lump", "grosseur", "boule", "ganth", "mass"],
    "skin rash": ["rash", "skin rash", "eruption", "boutons", "chakatte", "daane"],
    "sore throat": ["sore throat", "mal de gorge", "gale mein dard"],
    "loss of smell": ["loss of smell", "perte d odorat", "sungne ki shakti"],
    "back pain": ["back pain", "mal de dos", "kamar dard", "peeth dard"],
    "blood in urine": ["blood in urine", "sang dans les urines", "peshab mein khoon", "hematuria"],
}

# condition medicale -> symptomes canoniques associes
CONDITION_SYMPTOMS: dict[str, list[str]] = {
    "Tuberculosis": ["fever", "cough", "weight loss", "night sweats", "chest pain"],
    "Migraine": ["headache", "dizziness", "nausea"],
    "Anemia": ["fatigue", "dizziness", "breathlessness", "weakness"],
    "Pneumonia": ["cough", "fever", "chest pain", "breathlessness", "chills"],
    "Asthma": ["breathlessness", "cough", "chest pain", "wheezing"],
    "Diabetes": ["thirst", "frequent urination", "fatigue", "blurred vision", "weight loss"],
    "Hypertension": ["headache", "dizziness", "chest pain", "blurred vision"],
    "Depression": ["sadness", "fatigue", "insomnia", "loss of appetite"],
    "Malaria": ["fever", "chills", "headache", "fatigue", "vomiting"],
    "COVID-19": ["fever", "cough", "fatigue", "loss of smell", "sore throat"],
    "Rheumatoid Arthritis": ["joint pain", "stiffness", "swelling", "fatigue"],
    "Gastritis": ["abdominal pain", "nausea", "bloating", "vomiting"],
    "Hepatitis": ["fatigue", "jaundice", "abdominal pain", "nausea"],
    "Stroke": ["weakness", "numbness", "confusion", "headache", "dizziness"],
    "Epilepsy": ["seizures", "confusion"],
    "HIV": ["fever", "weight loss", "fatigue", "night sweats", "diarrhea"],
    "Breast Cancer": ["lump", "fatigue", "weight loss"],
    "Hypothyroidism": ["fatigue", "weight loss", "constipation", "palpitations"],
    "Chronic Kidney Disease": ["fatigue", "swelling", "nausea", "blood in urine"],
    "Heart Failure": ["breathlessness", "fatigue", "swelling", "chest pain", "palpitations"],
    "Chronic Obstructive Pulmonary Disease": ["breathlessness", "cough", "wheezing", "chest pain"],
    "Dengue": ["fever", "headache", "joint pain", "skin rash", "nausea"],
    "Osteoarthritis": ["joint pain", "stiffness", "swelling", "back pain"],
    "Parkinson Disease": ["stiffness", "weakness", "numbness"],
}
