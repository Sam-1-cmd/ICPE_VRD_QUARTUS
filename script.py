import streamlit as st
import os
from PyPDF2 import PdfReader
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import requests
from dotenv import load_dotenv
from openai import OpenAI

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
    .stMarkdown h3 {
        color: #2c3e50;
    }
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
            
        # Chargement et traitement du PDF pour la recherche sémantique
        with st.spinner("Indexation du document..."):
            with open("temp_upload.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            loader = PyPDFLoader("temp_upload.pdf")
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            docs = text_splitter.split_documents(documents)
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vectordb = FAISS.from_documents(docs, embeddings)
            vectordb.save_local("faiss_index")
            
    except Exception as e:
        st.sidebar.error(f"Erreur lors de la lecture du PDF : {e}")
    finally:
        if os.path.exists("temp_upload.pdf"):
            os.remove("temp_upload.pdf")

# === EN-TÊTE AVEC LOGO ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://www.mucem.org/sites/default/files/2022-08/logo-Morgane.gif", width=90)
with col2:
    st.markdown("## 🛠️ ICPE / VRD Analyzer")
    st.markdown("**Outil d'analyse réglementaire des projets VRD liés aux ICPE**")

st.markdown("---")

# === MESSAGE D'ACCUEIL ===
st.info("👋 Bienvenue ! Décrivez une intervention VRD dans la zone ci-dessous pour en évaluer l'impact réglementaire ICPE selon l'arrêté ministériel du 11 avril 2017.")

# === SAISIE DU TEXTE À ANALYSER ===
st.markdown("### ✍️ Décrivez la modification de travaux VRD à analyser")
with st.expander("🔍 Voir un exemple"):
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
            
            # Recherche sémantique si document chargé
            if uploaded_file is not None:
                try:
                    vectordb = FAISS.load_local("faiss_index", HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
                    docs_similaires = vectordb.similarity_search(user_input, k=3)
                    
                    with st.expander("📚 Extraits pertinents du document"):
                        for i, d in enumerate(docs_similaires):
                            st.markdown(f"**Extrait {i+1} :**")
                            st.write(d.page_content)
                            st.markdown("---")
                except Exception as e:
                    st.warning(f"⚠️ Impossible d'effectuer la recherche sémantique : {str(e)}")
            
        elif MODE == "API OpenAI (GPT)":
            try:
                load_dotenv()
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                # On inclut le texte du PDF s'il a été chargé
                context = f"Description de l'intervention : {user_input}"
                if pdf_text:
                    context += f"\n\nDocument de référence :\n{pdf_text[:2000]}"
                
                with st.spinner("Analyse en cours..."):
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system", 
                                "content": """Tu es un expert en réglementation ICPE et VRD. 
                                Analyse la situation avec rigueur en te basant sur l'arrêté du 11 avril 2017.
                                Structure ta réponse avec :
                                1. Classification ICPE potentielle
                                2. Conformité réglementaire
                                3. Recommandations"""
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

def generate_pdf(user_input, result_text):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # En-tête avec logo
    try:
        response = requests.get("https://www.mucem.org/sites/default/files/2022-08/logo-Morgane.gif", timeout=10)
        if response.status_code == 200:
            logo = ImageReader(BytesIO(response.content))
            c.drawImage(logo, 50, height - 100, width=60, height=60, mask='auto')
    except Exception:
        pass  # Continue sans logo si problème

    # Titre et informations
    c.setFont("Helvetica-Bold", 16)
    c.drawString(120, height - 50, "Fiche d'analyse ICPE / VRD")
    c.setFont("Helvetica", 10)
    c.drawString(120, height - 70, f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Référence réglementaire
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, height - 105, "Référence : Arrêté ministériel du 11 avril 2017 applicable aux ICPE")

    # Section Modification
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 140, "✍️ Modification décrite :")
    text = c.beginText(50, height - 160)
    text.setFont("Helvetica", 10)
    for line in user_input.split("\n"):
        text.textLine(line.strip())
    c.drawText(text)

    # Section Analyse
    y_offset = text.getY() - 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_offset, "✅ Analyse réglementaire :")
    
    result_text_obj = c.beginText(50, y_offset - 20)
    result_text_obj.setFont("Helvetica", 10)
    
    # Gestion des sauts de ligne et longueurs
    max_width = width - 100
    for line in result_text.split("\n"):
        if c.stringWidth(line, "Helvetica", 10) > max_width:
            words = line.split()
            current_line = []
            current_length = 0
            for word in words:
                word_length = c.stringWidth(word + " ", "Helvetica", 10)
                if current_length + word_length < max_width:
                    current_line.append(word)
                    current_length += word_length
                else:
                    result_text_obj.textLine(" ".join(current_line))
                    current_line = [word]
                    current_length = word_length
            if current_line:
                result_text_obj.textLine(" ".join(current_line))
        else:
            result_text_obj.textLine(line)
    c.drawText(result_text_obj)

    # Pied de page amélioré
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(50, 50, width - 50, 50)
    
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(50, 35, "📄 Fiche générée automatiquement - Projet Quartus Logistique - Analyse ICPE/VRD")
    c.drawRightString(width - 50, 35, f"Page 1/1 | {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# === BOUTON DE TÉLÉCHARGEMENT ===
if user_input and result_text:
    pdf_file = generate_pdf(user_input, result_text)
    st.download_button(
        label="📥 Télécharger la fiche d'analyse PDF",
        data=pdf_file,
        file_name=f"fiche_analyse_ICPE_VRD_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# === PIED DE PAGE ===
st.markdown("---")
st.caption("🔖 Quartus · Projet ICPE / VRD · Version 1.1 · © 2025")
