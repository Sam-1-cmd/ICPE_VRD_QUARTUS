import streamlit as st
import os
from PyPDF2 import PdfReader
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# === CONFIGURATION DE LA PAGE ===
st.set_page_config(page_title="ICPE / VRD Analyzer", layout="centered", page_icon="🛠️")

# === STYLE PERSONNALISÉ ===
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(to right, #f7f8fc, #e0e6f7);
        font-family: 'Arial', sans-serif;
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

# === BARRE LATÉRALE ===
st.sidebar.title("🧭 Navigation")
MODE = st.sidebar.radio("🧠 Mode d'analyse :", ["Démo hors ligne", "API OpenAI (GPT)"])

st.sidebar.markdown("📂 **Téléverse un document réglementaire**")
uploaded_file = st.sidebar.file_uploader("Fichier PDF", type=["pdf"], label_visibility="collapsed")

pdf_text = ""
if uploaded_file is not None:
    st.sidebar.success(f"✅ Fichier chargé : {uploaded_file.name}")
    try:
        reader = PdfReader(uploaded_file)
        pdf_text = "\n".join([page.extract_text() or "" for page in reader.pages])
        with st.expander("🧾 Voir le contenu du PDF importé"):
            st.write(pdf_text[:1000] + ("..." if len(pdf_text) > 1000 else ""))
    except Exception as e:
        st.sidebar.error(f"Erreur lors de la lecture du PDF : {e}")

# === EN-TÊTE AVEC LOGO ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://www.construction21.org/france/data/sources/users/20051/20230217094921-5quartuslogoversion1-noire.jpg", width=150)
with col2:
    st.markdown("## 🛠️ ICPE / VRD Analyzer")
    st.markdown("**Outil d'analyse réglementaire des projets VRD liés aux ICPE**")

st.markdown("---")

# === MESSAGE D'ACCUEIL ===
st.info("👋 Bienvenue ! Décrivez une intervention VRD dans la zone ci-dessous pour en évaluer l'impact réglementaire ICPE.")

# === SAISIE DU TEXTE À ANALYSER ===
st.markdown("### ✍️ Décrivez la modification de travaux VRD à analyser")
with st.expander("🔍 Besoin d'un exemple ?"):
    st.markdown("""
    **Exemple :** 
    Déplacement d'un bassin de rétention vers l'ouest, en dehors de la zone inondable, 
    pour libérer l'accès pompier. Le nouveau bassin aura une capacité de 60 000 m³.
    """)

user_input = st.text_area(
    "Saisie de la modification VRD :",
    placeholder="Décris ici ta modification (ouvrage, zone, raison, impact...)",
    height=200,
    label_visibility="visible"
)

# === ANALYSE LORS DU CLIC ===
result_text = ""
if st.button("🔍 Analyser la situation"):
    if not user_input.strip():
        st.warning("⚠️ Merci de décrire une intervention avant de lancer l'analyse.")
    else:
        if MODE == "Démo hors ligne":
            st.info("🧪 Mode démonstration local")
            result_text = """✅ La modification décrite concerne potentiellement un ouvrage hydraulique situé en zone ICPE.
Vérifiez la conformité avec l'arrêté du 11 avril 2017.
Si volume > 50 000 m³, cela peut activer la rubrique 1510.
Pensez à mettre à jour le Porter-à-Connaissance ICPE si nécessaire."""
            st.markdown(f"### ✅ Analyse simulée :\n{result_text}")
            
        elif MODE == "API OpenAI (GPT)":
            try:
                from dotenv import load_dotenv
                from openai import OpenAI
                
                load_dotenv()
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                # On inclut le texte du PDF s'il a été chargé
                context = f"Description de l'intervention : {user_input}"
                if pdf_text:
                    context += f"\n\nDocument de référence :\n{pdf_text[:2000]}"
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system", 
                            "content": "Tu es un expert en réglementation ICPE et VRD. Analyse la situation avec rigueur."
                        },
                        {
                            "role": "user", 
                            "content": context
                        }
                    ],
                    temperature=0.3  # Pour des réponses plus factuelles
                )
                result_text = response.choices[0].message.content
                st.success("✅ Réponse générée par GPT :")
                st.markdown(result_text)
            except Exception as e:
                st.error(f"❌ Erreur lors de l'appel API : {str(e)}")

# === GÉNÉRATION DE PDF ===
def generate_pdf(user_input, result_text):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # En-tête
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Fiche d'analyse ICPE / VRD")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Section description
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 100, "✍️ Modification décrite :")
    text = c.beginText(50, height - 120)
    text.setFont("Helvetica", 10)
    for line in user_input.split("\n"):
        text.textLine(line.strip())
    c.drawText(text)

    # Section analyse
    y_offset = text.getY() - 30  # Plus d'espace entre les sections
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_offset, "✅ Analyse réglementaire :")
    
    result_text_obj = c.beginText(50, y_offset - 20)
    result_text_obj.setFont("Helvetica", 10)
    
    # Gestion des lignes trop longues
    max_width = width - 100
    for line in result_text.split("\n"):
        if c.stringWidth(line, "Helvetica", 10) > max_width:
            words = line.split()
            new_line = []
            current_length = 0
            for word in words:
                word_length = c.stringWidth(word + " ", "Helvetica", 10)
                if current_length + word_length < max_width:
                    new_line.append(word)
                    current_length += word_length
                else:
                    result_text_obj.textLine(" ".join(new_line))
                    new_line = [word]
                    current_length = word_length
            if new_line:
                result_text_obj.textLine(" ".join(new_line))
        else:
            result_text_obj.textLine(line)
    
    c.drawText(result_text_obj)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

if user_input and result_text:
    pdf_file = generate_pdf(user_input, result_text)
    st.download_button(
        label="📥 Télécharger la fiche d'analyse PDF",
        data=pdf_file,
        file_name="fiche_analyse_ICPE_VRD.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# === PIED DE PAGE ===
st.markdown("---")
st.caption("🔖 Quartus · Projet ICPE / VRD · Version 1.0 · © 2025")
