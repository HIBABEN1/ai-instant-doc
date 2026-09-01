"""

Cœur "intelligence" du pipeline utilisant Llama 3 via Ollama.
Transforme des données brutes (notes, Jira, Excel) en un objet Pydantic `RapportRecette`.

Étapes :
1. Instanciation du client ChatOllama (Llama 3).
2. Contrainte de la sortie via `with_structured_output(RapportRecette)`.
3. Envoi du System Prompt et Human Message.
4. Boucle de correction (Repair Prompt) en cas d'erreur de validation.
"""

import os
import logging
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import ValidationError
from langchain_core.exceptions import OutputParserException
from models import RapportRecette

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert en analyse de campagnes de recette logicielle. 
Ton rôle est d'extraire et structurer les informations des données brutes (notes, tickets Jira, fichiers Excel) 
en un rapport de recette validé et complet. 
Réponds toujours en JSON valide et respecte strictement la structure demandée."""

def _construire_client_llm():
    """Détecte si on utilise Groq (Cloud) ou Ollama (Local)."""
    
    # On regarde si une clé Groq existe dans l'environnement
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        # MODE CLOUD (Pour ton site internet)
        return ChatGroq(
            model_name="llama-3.2-3b-preview",
            groq_api_key=api_key,
            temperature=0
        )
    else:
        # MODE LOCAL (Pour ton PC avec Ollama)
        return ChatOllama(
            model="llama3.2",
            base_url="http://localhost:11434",
            format="json",
            temperature=0
        )

def extraire_rapport(texte_brut: str, max_tentatives: int = 3) -> RapportRecette:
    """Transforme un texte brut en `RapportRecette` validé via Llama 3.

    Args:
        texte_brut: contenu textuel normalisé de toutes les sources.
        max_tentatives: nombre d'essais en cas d'erreur de formatage.

    Returns:
        Instance de RapportRecette validée et calculée.
    """
    llm = _construire_client_llm()

    # Configuration du format de sortie structuré basé sur le modèle Pydantic
    llm_structure = llm.with_structured_output(RapportRecette)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Voici les données brutes de la campagne de recette :\n\n{texte_brut}"),
    ]

    derniere_erreur: Exception | None = None

    for tentative in range(1, max_tentatives + 1):
        try:
            logger.info("Extraction Llama 3 (Ollama) - tentative %s/%s", tentative, max_tentatives)
            
            # Appel au modèle
            rapport: RapportRecette = llm_structure.invoke(messages)

            # Re-validation Pydantic pour s'assurer de l'intégrité de l'objet
            # (nécessaire car le LLM peut renvoyer un dictionnaire ou un objet selon l'appel)
            if not isinstance(rapport, RapportRecette):
                rapport = RapportRecette.model_validate(rapport)
            
            # Calcul automatique des champs dérivés (ex: anomalies_bloquantes)
            rapport.calculer_champs_derives()
            
            logger.info("Extraction réussie avec succès.")
            return rapport

        except (ValidationError, OutputParserException, Exception) as erreur:
            derniere_erreur = erreur
            logger.warning("Échec de validation (tentative %s) : %s", tentative, erreur)

            # Boucle de réparation : on fournit l'erreur technique au LLM pour correction
            messages.append(
                HumanMessage(
                    content=(
                        "Ta réponse précédente est invalide. "
                        f"Erreur de validation Pydantic :\n{erreur}\n\n"
                        "Corrige ta réponse en respectant strictement le format JSON et les valeurs autorisées."
                    )
                )
            )

    raise ValueError(
        f"Échec de l'extraction après {max_tentatives} tentatives. "
        f"Dernière erreur enregistrée : {derniere_erreur}"
    )
