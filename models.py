"""

Schémas Pydantic utilisés comme "contrat de sortie" pour le LLM (Azure OpenAI).

Ces modèles jouent un double rôle dans le pipeline AI-Instant-Doc :
1. Ils contraignent la réponse du LLM (via `with_structured_output`) à respecter
   exactement cette structure : impossible pour le modèle de halluciner un champ
   inattendu ou de renvoyer un format libre.
2. Le nom de chaque champ correspond exactement à une balise Jinja2 du template
   Word (ex. `nom_projet` -> {{ nom_projet }} dans le .docx), ce qui évite toute
   étape de mapping manuel supplémentaire entre le JSON et le document final.
"""

from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sous-modèle : une ligne du tableau "anomalies" dans le CR / PV
# ---------------------------------------------------------------------------
class Anomalie(BaseModel):
    """Représente une anomalie (bug) détectée pendant la campagne de recette.

    Chaque instance correspond à UNE ligne du tableau dynamique dans le Word
    (balise `{%tr for a in anomalies %} ... {% endtr %}` dans doc_service.py).
    """

    id: str = Field(
        ...,
        description="Identifiant de l'anomalie tel qu'il apparaît dans Jira (ex. 'JIRA-1234'). "
                     "Si aucun identifiant n'est présent dans la source, générer un identifiant "
                     "séquentiel du type 'ANO-01'.",
    )
    description: str = Field(
        ...,
        description="Description courte et factuelle de l'anomalie, reformulée de manière professionnelle.",
    )
    severite: Literal["Bloquante", "Majeure", "Mineure", "Cosmétique"] = Field(
        ...,
        description="Niveau de sévérité de l'anomalie. Choisir la valeur la plus proche si "
                     "la source utilise un vocabulaire différent (ex. 'Critical' -> 'Bloquante').",
    )
    statut: Literal["Ouverte", "En cours", "Corrigée", "Fermée", "Reportée"] = Field(
        ...,
        description="Statut courant de l'anomalie au moment de la rédaction du rapport.",
    )


# ---------------------------------------------------------------------------
# Modèle principal : le rapport de recette complet
# ---------------------------------------------------------------------------
class RapportRecette(BaseModel):
    """Structure complète attendue en sortie du LLM pour générer le CR de Recette
    ou le PV de Validation.

    ATTENTION : les noms de champs doivent rester strictement synchronisés avec
    les balises Jinja2 du template Word (voir doc_service.py).
    """

    nom_projet: str = Field(..., description="Nom du projet ou du client concerné par la recette.")
    date_recette: str = Field(
        ...,
        description="Date de la recette au format JJ/MM/AAAA. Si plusieurs dates sont mentionnées, "
                     "retenir la date de fin de campagne.",
    )
    nom_testeur: str = Field(..., description="Nom du chargé de recette / testeur ayant réalisé la campagne.")
    perimetre_teste: str = Field(
        ...,
        description="Résumé synthétique (2-3 phrases) du périmètre fonctionnel couvert par la recette.",
    )

    nombre_cas_test_total: int = Field(..., description="Nombre total de cas de test exécutés.")
    nombre_cas_test_ok: int = Field(..., description="Nombre de cas de test passés avec succès.")

    anomalies: List[Anomalie] = Field(
        default_factory=list,
        description="Liste exhaustive des anomalies détectées, dans l'ordre où elles apparaissent dans la source.",
    )

    conclusion_generale: str = Field(
        ...,
        description="Conclusion synthétique de la recette (statut global : Go / Go avec réserves / No-Go), "
                     "rédigée dans un style professionnel adapté à un document contractuel.",
    )

    # Champ calculé côté service (pas demandé au LLM) mais utile pour les
    # conditions Jinja2 du template ({% if anomalies_bloquantes %} ... {% endif %})
    anomalies_bloquantes: Optional[bool] = Field(
        default=None,
        description="Calculé automatiquement : True si au moins une anomalie a la sévérité 'Bloquante'.",
    )

    def calculer_champs_derives(self) -> "RapportRecette":
        """Recalcule les champs dérivés (non demandés au LLM) à partir des données validées.

        Appelée systématiquement après validation Pydantic, avant l'injection dans le Word,
        pour ne jamais dépendre du LLM sur une information déductible de manière fiable en Python.
        """
        self.anomalies_bloquantes = any(a.severite == "Bloquante" for a in self.anomalies)
        return self
