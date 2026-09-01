import streamlit as st
import sys
import os

# Ajout du dossier parent au chemin pour pouvoir importer les services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extraction_service import extraire_rapport
from doc_service import generer_document_en_memoire

# Configuration de la page
st.set_page_config(
    page_title="Capgemini | AI-Instant-Doc",
    page_icon="📝",
    layout="wide"
)

# -------------------------
# En-tête
# -------------------------
st.title("📄 AI-Instant-Doc")
st.subheader("Génération instantanée de Compte-Rendu de Recette par IA (Llama 3 + Ollama)")

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.image("logo_capgemini.png", width=200)

    st.info(
        "Cet outil utilise Llama 3 exécuté localement via Ollama afin de garantir la confidentialité des données."
    )

    st.markdown("## 📄 Template Word")

    template_file = st.file_uploader(
        "Choisissez votre modèle Word (.docx)",
        type=["docx"],
        help="Le document doit contenir les balises Jinja2 ({{ }}, {% %}) utilisées par AI-Instant-Doc."
    )

# -------------------------
# Interface
# -------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1️⃣ Données d'entrée")

    notes_brutes = st.text_area(
        "Collez ici vos notes de recette, exports Jira ou données Excel :",
        height=400,
        placeholder="""Exemple :

Projet Pegasus

50 cas de test exécutés
48 OK
2 anomalies

JIRA-101
Login impossible
Sévérité : Bloquante
Statut : Ouverte
"""
    )

    generer_btn = st.button(
        "🚀 Générer le Compte-Rendu",
        use_container_width=True
    )

with col2:

    st.markdown("### 2️⃣ Résultat")

    if generer_btn:

        if not template_file:
            st.warning("Veuillez d'abord téléverser un template Word (.docx).")

        elif not notes_brutes.strip():
            st.warning("Veuillez saisir les données de recette.")

        else:

            try:

                with st.spinner("🧠 Analyse des données par Llama 3..."):

                    rapport = extraire_rapport(notes_brutes)

                st.success("Extraction réussie ✅")

                with st.expander("Voir les données structurées"):

                    st.json(rapport.model_dump())

                with st.spinner("📄 Génération du document Word..."):

                    document = generer_document_en_memoire(
                        template_file,
                        rapport
                    )

                st.download_button(
                    "📥 Télécharger le Compte-Rendu",
                    data=document,
                    file_name="CR_Recette_Genere.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

                st.balloons()

            except Exception as e:
                st.error(f"Erreur : {e}")

    else:
        st.info("Téléversez un template Word puis saisissez vos données pour commencer.")