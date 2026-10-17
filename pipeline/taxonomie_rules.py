import re

DOCUMENT_TYPE_RULES = {
    "arrete": ["arrete", "arrêté"],
    "circulaire": ["circulaire"],
    "note": ["note"],
    "guide": ["guide"],
    "procedure": ["procedure", "procédure"],
    "code_ou_loi": ["code", "loi"],
}


TAG_RULES = {

    "TVA": [
        "tva",
        "taxe sur la valeur ajoutée",
        "assujettissement à la tva",
        "crédit de tva",
        "prestataires non domiciliés"
    ],

    "IS": [
        "impôt sur les sociétés",
        "impots sur les societes",
        "is"
    ],

    "IR": [
        "impôt sur le revenu",
        "impots sur le revenu",
        "revenu"
    ],

    "ITS": [
        "traitements et salaires",
        "its",
        "rémunérations",
        "remunerations"
    ],

    "AMORTISSEMENT": [
        "amortissement",
        "taux d amortissement",
        "immobilisation",
        "immobilisations"
    ],

    "PRIX_DE_TRANSFERT": [
        "prix de transfert",
        "declaration pays par pays",
        "entreprises associées"
    ],

    "CONTROLE_FISCAL": [
        "contrôle fiscal",
        "controle fiscal",
        "vérification",
        "verification",
        "redressement"
    ],

    "CONTENTIEUX_FISCAL": [
        "contentieux fiscal",
        "recours gracieux",
        "réclamation",
        "reclamation"
    ],

    "PROCEDURES_FISCALES": [
        "procédure",
        "procedure",
        "note de service",
        "circulaire",
        "guide"
    ],

    "FACTURE_NORMALISEE": [
        "facture normalisée",
        "facture normalisee",
        "factures normalisées",
        "factures normalisees"
    ],

    "MECEF": [
        "mecef",
        "fichier des écritures comptables",
        "fichier des ecritures comptables",
        "fec"
    ],

    "COMPTABILITE": [
        "comptable",
        "comptabilité",
        "comptabilite",
        "syscohada",
        "plan des comptes",
        "écritures comptables",
        "ecritures comptables"
    ],

    "OHADA": [
        "ohada",
        "acte uniforme"
    ],

    "DOUANE": [
        "douane",
        "importation",
        "exportation"
    ],

    "INVESTISSEMENT": [
        "investissement",
        "investissements",
        "zones economiques speciales",
        "code des investissements"
    ],

    "PME": [
        "mpme",
        "mpe",
        "pme",
        "petites et moyennes entreprises"
    ],

    "ENTREPRISE": [
        "entreprise",
        "entreprises",
        "société",
        "societe",
        "personne morale"
    ],

    "E_SERVICES": [
        "e services",
        "e-services",
        "teledeclaration",
        "télédéclaration",
        "portail"
    ]
}

def extract_version(title):

    m = re.search(
        r"(19|20)\d{2}",
        title
    )

    return m.group(0) if m else None


def extract_country(title):

    t = title.upper()

    if "OHADA" in t:
        return "OHADA"

    if "CEDEAO" in t:
        return "CEDEAO"

    return "BJ"


def extract_document_type(title):

    t = title.lower()

    for doc_type, keywords in DOCUMENT_TYPE_RULES.items():

        if any(
            k in t
            for k in keywords
        ):
            return doc_type

    return "document"