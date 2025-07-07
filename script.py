import streamlit as st
import os
from PyPDF2 import PdfReader

# === CONFIGURATION DE LA PAGE ===
st.set_page_config(page_title="ICPE / VRD Analyzer", layout="centered", page_icon="🛠️")

# === STYLE PERSONNALISÉ ===
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(to right, #f7f8fc, #e0e6f7);
    }
    textarea {
        background-color: #ffffffcc !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }
    .stButton > button {
        background-color: #3d5afe;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5em 1.5em;
        transition: 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #304ffe;
        transform: scale(1.03);
    }
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# === SÉLECTION DU MODE ===
MODE = st.sidebar.radio("🧠 Mode d'analyse :", ["Démo hors ligne", "API OpenAI (GPT)"])

# === TÉLÉVERSEMENT PDF ===
st.sidebar.markdown("📂 Téléverse un document réglementaire (PDF)")
uploaded_file = st.sidebar.file_uploader("Fichier PDF", type=["pdf"])

if uploaded_file is not None:
    st.sidebar.success(f"✅ Fichier chargé : {uploaded_file.name}")
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        with st.expander("🧾 Voir le contenu du PDF importé"):
            st.write(text[:1000] + "...")
    except Exception as e:
        st.sidebar.error(f"Erreur lors de la lecture du PDF : {e}")

# === EN-TÊTE AVEC LOGO ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://www.mucem.org/sites/default/files/2022-08/logo-Morgane.gif", width=100)
with col2:
    st.markdown("## 🛠️ Outil d’analyse ICPE / VRD")
    st.markdown("Analyse réglementaire des modifications de travaux en zone ICPE.")

st.markdown("---")

# === SAISIE DU TEXTE À ANALYSER ===
st.subheader("✍️ Décrivez la modification de travaux VRD à analyser :")
user_input = st.text_area(
    "Saisie de la modification VRD :",
    placeholder="Exemple : Déplacement d’un bassin de rétention vers l’ouest à cause de contraintes incendie...",
    height=200
)

# === ANALYSE LORS DU CLIC ===
if st.button("🔍 Analyser la situation"):
    if not user_input:
        st.warning("⚠️ Merci de décrire une intervention avant de lancer l’analyse.")
    else:
        if MODE == "Démo hors ligne":
            st.info("🧪 Mode démonstration local")
            st.markdown(f"""
### ✅ Analyse simulée :

- La modification décrite concerne potentiellement un ouvrage hydraulique situé en zone ICPE.
- Vérifie la conformité avec **l'arrêté du 11 avril 2017** (bassins, rejets, etc.).
- Si volume > **50 000 m³**, cela peut activer la **rubrique 1510**.
- Pense à **mettre à jour le Porter-à-Connaissance ICPE** si le changement est significatif.

📘 Référence utile : Guide technique ICPE - Rubrique 2.1.5.0
""")
        elif MODE == "API OpenAI (GPT)":
            try:
                from dotenv import load_dotenv
                import openai
                load_dotenv()
                openai.api_key = os.getenv("OPENAI_API_KEY")
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Tu es un expert en réglementation ICPE et VRD. Sois rigoureux et clair."},
                        {"role": "user", "content": user_input}
                    ]
                )
                st.success("✅ Réponse générée par GPT :")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"❌ Erreur lors de l'appel API : {e}")

# === PIED DE PAGE ===
st.markdown("---")
st.caption("🔖 Quartus · Projet ICPE / VRD · Version 1.0 · © 2025")
