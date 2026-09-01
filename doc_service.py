"""

Génération du document Word à partir d'un template uploadé
et d'un objet RapportRecette.
"""

from __future__ import annotations

import io
import logging
from typing import BinaryIO

from docxtpl import DocxTemplate

from models import RapportRecette

logger = logging.getLogger(__name__)


def construire_contexte(rapport: RapportRecette) -> dict:
    """
    Convertit l'objet RapportRecette en dictionnaire compatible Jinja2.
    """

    contexte = rapport.model_dump()

    if contexte.get("anomalies_bloquantes") is None:
        contexte["anomalies_bloquantes"] = any(
            a["severite"] == "Bloquante"
            for a in contexte["anomalies"]
        )

    return contexte


def generer_document_en_memoire(
    template_file: BinaryIO,
    rapport: RapportRecette,
) -> io.BytesIO:
    """
    Génère un document Word en mémoire.

    Parameters
    ----------
    template_file :
        Fichier .docx envoyé via st.file_uploader()

    rapport :
        Objet RapportRecette validé.

    Returns
    -------
    BytesIO
        Document Word prêt à être téléchargé.
    """

    logger.info("Chargement du template Word...")

    # Remet le curseur au début du fichier
    template_file.seek(0)

    # Lecture en mémoire
    contenu = io.BytesIO(template_file.read())

    # Chargement du template
    doc = DocxTemplate(contenu)

    # Construction du contexte Jinja2
    contexte = construire_contexte(rapport)

    logger.info("Remplissage du template...")

    # Injection des données
    doc.render(contexte)

    logger.info("Création du document...")

    # Sauvegarde en mémoire
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)

    logger.info("Document généré avec succès.")

    return output