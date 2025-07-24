import streamlit as st
import os
from PyPDF2 import PdfReader
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime

# —— NOUVEAUX IMPORTS POUR RAG LOCAL ——
import glob
import faiss
import numpy as np
import fitz
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

# === CONFIG PAGE ===
st.set_page_config(
    page_title="ICPE / VRD Analyzer",
    layout="centered",
    page_icon="🛠️",
    initial_sidebar_state="expanded",  # Sidebar ouverte par défaut
    menu_items={
        'Get Help': 'https://www.ecologie.gouv.fr/icpe',  # Lien vers l'aide
        'About': "Analyseur d'ICPE/VRD avec IA | © 2024"
    }
)

# === STYLE ===
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://cdn.dribbble.com/users/527451/screenshots/3115734/safetynow_frame1-drib.gif");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
        opacity: 0.8;  /* Réduit l'opacité du fond */
    }
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.95);  /* Blanc plus opaque */
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0px 0px 15px rgba(0, 0, 0, 0.1);  /* Ombre légère */
    }
    h1, h2, h3 {
        color: #2c3e50 !important;  /* Couleur de titre plus professionnelle */
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

# Extraction du texte brut du PDF
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

# === EN-TÊTE ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://www.construction21.org/france/data/sources/users/20051/20230217094921-5quartuslogoversion1-noire.jpg", width=150)
with col2:
    st.markdown("## 🛠️ ICPE / VRD Analyzer")
    st.markdown("**Outil d'analyse réglementaire des projets VRD liés aux ICPE**")

st.markdown("---")
st.info("👋 Bienvenue ! Décris ici ta modification VRD pour évaluer son impact réglementaire ICPE.")

# === SAISIE DE L'UTILISATEUR ===
st.markdown("### ✍️ Décris la modification VRD à analyser")
with st.expander("🔍 Besoin d'un exemple ?"):
    st.markdown("""
    **Exemple :**  
    Déplacement d'un bassin de rétention vers l'ouest, en dehors de la zone inondable,  
    pour libérer l'accès pompier. Le nouveau bassin aura une capacité de 60 000 m³.
    """)

user_input = st.text_area(
    "Saisie de la modification VRD :",
    placeholder="Décris ici ta modification (ouvrage, zone, raison, impact...)",
    height=200
)

# === FONCTIONS UTILES RAG LOCAL ===
def chunk_text(text: str, size: int = 1000, overlap: int = 200):
    """Découpe en chunks de `size` caractères avec chevauchement."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return chunks

@st.cache_resource(show_spinner=False)
def init_local_rag(text: str):
    """
    Construit :
      - la liste de chunks,
      - l'embeddeur et embeddings normalisés,
      - l'index FAISS,
      - le pipeline de génération Flan-T5-small (CPU).
    """
    # 1) chunking du PDF
    chunks = chunk_text(text)

    # 2) embeddings
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    embs = embedder.encode(chunks, convert_to_numpy=True, show_progress_bar=False)
    embs /= np.linalg.norm(embs, axis=1, keepdims=True)

    # 3) index FAISS (cosine via Inner-Product)
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)

    # 4) pipeline Flan-T5-small CPU
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
    model     = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small").to("cpu")
    generator = pipeline(
        "text2text-generation",
        model=model,
        tokenizer=tokenizer,
        device=-1
    )

    return chunks, embedder, index, generator

# === BOUTON ANALYSE ===
result_text = ""
if st.button("🔍 Analyser la situation"):
    if not user_input.strip():
        st.warning("⚠️ Décris d'abord ta modification VRD.")
    else:
        if MODE == "Démo hors ligne":
            if not pdf_text:
                st.error("⚠️ Téléverse un document PDF pour le mode hors ligne.")
            else:
                st.info("🧪 Mode démonstration **local RAG**")
                # --- build RAG pipeline on PDF ---
                chunks, embedder, index, generator = init_local_rag(pdf_text)
                # --- retrieval ---
                q_emb = embedder.encode([user_input], convert_to_numpy=True)
                q_emb /= np.linalg.norm(q_emb, axis=1, keepdims=True)
                _, ids = index.search(q_emb, 3)
                context = "\n\n".join(chunks[i] for i in ids[0])
                # --- prompt framing ---
                prompt = f"""
Tu es expert ICPE/VRD.
Pour chaque disposition légale applicable, réponds en deux parties :
1) Disposition légale (article + citation)
2) Proposition de solution concrète

Contexte :
{context}

Question :
{user_input}

Réponse :
"""
                # --- génération ---
                with st.spinner("⌛ Génération de la réponse…"):
                    out = generator(prompt, max_new_tokens=256, num_beams=4, early_stopping=True)
                    result_text = out[0]["generated_text"].strip()
                st.success("✅ Réponse RAG locale :")
                st.markdown(result_text)

        elif MODE == "API OpenAI (GPT)":
            # conserve ta logique OpenAI existante
            try:
                from dotenv import load_dotenv
                from openai import OpenAI

                load_dotenv()
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
                        {"role": "user", "content": context}
                    ],
                    temperature=0.3
                )
                result_text = response.choices[0].message.content
                st.success("✅ Réponse générée par GPT :")
                st.markdown(result_text)
            except Exception as e:
                st.error(f"❌ Erreur lors de l'appel API : {e}")

# === GÉNÉRATION DE LA FICHE PDF ===
if user_input and result_text:
    def generate_pdf(user_input, result_text):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        logo = ImageReader("https://www.galivel.com/media/full/nouveau_logo_quartus-5.jpg")
        logo_w, logo_h = 100, 40

        def wrap_lines(text, max_width):
            words = text.split()
            lines = []; cur = ""
            for w in words:
                test = w if not cur else f"{cur} {w}"
                if c.stringWidth(test) <= max_width:
                    cur = test
                else:
                    lines.append(cur); cur = w
            if cur: lines.append(cur)
            return lines

        # page 1 header/footer
        def draw_header_footer(page_num):
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "Fiche d'analyse ICPE / VRD")
            c.drawImage(logo, width - 150, height - 80, width=logo_w, height=logo_h, mask="auto")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 70, f"Date : {datetime.now():%d/%m/%Y %H:%M}")
            c.setFont("Helvetica-Oblique", 8)
            c.drawCentredString(width/2, 20, f"Page {page_num}")

        # écrire le contenu
        draw_header_footer(1)
        y = height - 100
        c.setFont("Helvetica-Bold", 12); c.drawString(50, y, "✍️ Modification décrite :")
        text_obj = c.beginText(50, y - 20); text_obj.setFont("Helvetica", 10)
        for line in wrap_lines(user_input, width-100):
            text_obj.textLine(line)
        c.drawText(text_obj)

        y2 = text_obj.getY() - 30
        c.setFont("Helvetica-Bold", 12); c.drawString(50, y2, "✅ Analyse réglementaire :")
        res_obj = c.beginText(50, y2 - 20); res_obj.setFont("Helvetica", 10)
        for line in wrap_lines(result_text, width-100):
            res_obj.textLine(line)
        c.drawText(res_obj)

        c.showPage(); c.save()
        buffer.seek(0)
        return buffer

    pdf_bytes = generate_pdf(user_input, result_text)
    st.download_button(
        label="📥 Télécharger la fiche PDF",
        data=pdf_bytes,
        file_name="fiche_analyse_ICPE_VRD.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# === PIED DE PAGE ===
st.markdown(
    """
    <div style="text-align: center; margin-top: 2rem; font-size: 0.8em;">
        © 2024 ICPE/VRD Analyzer | Conforme à la 
        <a href="https://www.legifrance.gouv.fr/affichCode.do?idSectionTA=LEGISCTA000006136105&cidTexte=LEGITEXT000006074220">
            loi n°2023-XX
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
