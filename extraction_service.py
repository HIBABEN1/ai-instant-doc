"""
Cœur intelligence du pipeline.

Utilise Groq Cloud en production et Ollama en local.

Pipeline :

Données brutes
      ↓
   ChatGroq
      ↓
Structured Output
      ↓
RapportRecette
      ↓
Validation Pydantic
"""

import os
import logging

import streamlit as st

from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import ValidationError
from langchain_core.exceptions import OutputParserException

from models import RapportRecette


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
Tu es un expert en analyse de campagnes de recette logicielle.

Ton rôle est d'extraire et structurer les informations des données
brutes provenant de notes, tickets Jira et fichiers Excel.

Tu dois produire un rapport de recette complet et cohérent.

Respecte strictement la structure Pydantic demandée.
Ne crée aucune information qui n'est pas présente dans les données.
"""


def _construire_client_llm():
    """
    Détecte automatiquement Groq Cloud ou Ollama Local.
    """

    # 1. Récupération de la clé Groq
 

    api_key = None

    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass


    if not api_key:
        api_key = os.environ.get("GROQ_API_KEY")



    if api_key:

        logger.info("LLM sélectionné : Groq Cloud")

        return ChatGroq(
            model="openai/gpt-oss-120b",
            groq_api_key=api_key,
            temperature=0
        )



    logger.info("LLM sélectionné : Ollama Local")

    return ChatOllama(
        model="llama3.2",
        base_url="http://localhost:11434",
        format="json",
        temperature=0
    )


def extraire_rapport(
    texte_brut: str,
    max_tentatives: int = 3
) -> RapportRecette:

    """
    Transforme les données brutes en RapportRecette.
    """

    llm = _construire_client_llm()

    # Structured output Pydantic
    llm_structure = llm.with_structured_output(
        RapportRecette
    )

    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT
        ),
        HumanMessage(
            content=(
                "Voici les données brutes de la campagne "
                "de recette :\n\n"
                f"{texte_brut}"
            )
        ),
    ]

    derniere_erreur = None


    for tentative in range(
        1,
        max_tentatives + 1
    ):

        try:

            logger.info(
                "Extraction LLM - tentative %s/%s",
                tentative,
                max_tentatives
            )

            # Appel LLM
            rapport = llm_structure.invoke(
                messages
            )

            # --------------------------------------------------
            # Validation Pydantic
            # --------------------------------------------------

            if not isinstance(
                rapport,
                RapportRecette
            ):

                rapport = RapportRecette.model_validate(
                    rapport
                )



            rapport.calculer_champs_derives()

            logger.info(
                "Extraction réussie."
            )

            return rapport

        except Exception as erreur:

            derniere_erreur = erreur

            logger.warning(
                "Échec tentative %s : %s",
                tentative,
                erreur
            )



            messages.append(
                HumanMessage(
                    content=(
                        "Ta réponse précédente est invalide.\n\n"
                        f"Erreur : {erreur}\n\n"
                        "Corrige ta réponse et respecte "
                        "strictement la structure demandée."
                    )
                )
            )


    raise ValueError(
        f"Échec de l'extraction après "
        f"{max_tentatives} tentatives. "
        f"Dernière erreur : {derniere_erreur}"
    )
