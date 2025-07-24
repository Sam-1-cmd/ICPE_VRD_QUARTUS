import streamlit as st
import os
from PyPDF2 import PdfReader
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime

# —— IMPORTS POUR RAG LOCAL ——
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

# === CONFIGURATION DE LA PAGE ===
st.set_page_config(page_title="ICPE / VRD Analyzer", layout="centered", page_icon="🛠️")

# === STYLE ===
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://cdn.dribbble.com/users/527451/screenshots/3115734/safetynow_frame1-drib.gif");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }
    .main .block-container {
        background-color: rgba(255,255,255,0.9);
        border-radius: 15px;
        padding: 2rem;
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

# Extraction du texte du PDF
pdf_text = ""
if uploaded_file:
    st.sidebar.success(f"✅ Fichier chargé : {uploaded_file.name}")
    try:
        reader = PdfReader(uploaded_file)
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        st.sidebar.error(f"Erreur lors de la lecture du PDF : {e}")

# === EN-TÊTE ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://www.construction21.org/france/data/sources/users/20051/20230217094921-5quartuslogoversion1-noire.jpg", width=150)
with col2:
    st.markdown("## 🛠️ ICPE / VRD Analyzer")
    st.markdown("**Analyse réglementaire experte des projets VRD sous ICPE**")

st.markdown("---")
st.info("👋 Bienvenue ! Décris ici ta modification VRD pour évaluer son impact réglementaire ICPE.")

# === SAISIE DE L'UTILISATEUR ===
st.markdown("### ✍️ Décris la modification VRD à analyser")
user_input = st.text_area(
    "Saisie de la modification VRD :",
    placeholder="Décris ici ta modification (ouvrage, zone, raison, impact...)",
    height=200
)

# === FONCTIONS POUR RAG LOCAL ===
def chunk_text(text: str, size: int = 1000, overlap: int = 200):
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return chunks

@st.cache_resource
def init_local_rag(text: str):
    chunks = chunk_text(text)
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    embs = embedder.encode(chunks, convert_to_numpy=True)
    embs /= np.linalg.norm(embs, axis=1, keepdims=True)
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")
    model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-small").to("cpu")
    generator = pipeline("text2text-generation", model=model, tokenizer=tokenizer, device=-1)
    return chunks, embedder, index, generator

# === ANALYSE ===
result_text = ""
if st.button("🔍 Analyser la situation"):
    if not user_input.strip():
        st.warning("⚠️ Décris d'abord ta modification VRD.")
    else:
        # Message système pour forcer le français
        system_instruction = (
            "Tu es un expert réglementaire ICPE et VRD. RÉPONDS UNIQUEMENT EN FRANÇAIS,"
            " sans anglicismes ni traduction. Ne reformule pas la question.")
        if MODE == "Démo hors ligne":
            if not pdf_text:
                st.error("⚠️ Téléverse un PDF pour le mode hors ligne.")
            else:
                chunks, embedder, index, generator = init_local_rag(pdf_text)
                q_emb = embedder.encode([user_input], convert_to_numpy=True)
                q_emb /= np.linalg.norm(q_emb, axis=1, keepdims=True)
                _, ids = index.search(q_emb, 3)
                context = "\n\n".join(chunks[i] for i in ids[0])
                prompt = f"""
{system_instruction}

Contexte :
{context}

Question :
{user_input}

Pour chaque disposition légale applicable, réponds en deux parties :
1) Disposition légale (article et citation)
2) Proposition de solution concrète adaptée.
"""
                with st.spinner("⌛ Génération en cours…"):
                    out = generator(prompt, max_new_tokens=256, num_beams=4)
                    result_text = out[0]["generated_text"].strip()
        else:
            try:
                from dotenv import load_dotenv
                from openai import OpenAI
                load_dotenv()
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_input}
                ]
                if pdf_text:
                    messages.insert(1, {"role": "user", "content": f"Document de référence :\n{pdf_text[:2000]}"})
                response = client.chat.completions.create(
                    model="gpt-4", messages=messages, temperature=0.0, max_tokens=512
                )
                result_text = response.choices[0].message.content.strip()
            except Exception as e:
                st.error(f"❌ Erreur API : {e}")
        if result_text:
            st.success("✅ Analyse réalisée :")
            st.markdown(result_text)

# === GÉNÉRATION PDF ===
if user_input and result_text:
    def generate_pdf(user_input, result_text):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        w, h = A4
        logo = ImageReader("https://www.galivel.com/media/full/nouveau_logo_quartus-5.jpg")
        def wrap(text, width):
            words, lines = text.split(), []
            cur = ""
            for w in words:
                test = f"{cur} {w}".strip()
                if c.stringWidth(test) < width:
                    cur = test
                else:
                    lines.append(cur); cur = w
            lines.append(cur)
            return lines
        def header_footer(page):
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, h-50, "Fiche d'analyse ICPE / VRD")
            c.drawImage(logo, w-150, h-80, width=100, height=40)
            c.setFont("Helvetica", 10)
            c.drawString(50, h-70, f"Date : {datetime.now():%d/%m/%Y %H:%M}")
            c.setFont("Helvetica-Oblique", 8)
            c.drawCentredString(w/2, 20, f"Page {page}")
        header_footer(1)
        y = h-100
        c.setFont("Helvetica-Bold", 12); c.drawString(50, y, "✍️ Modification décrite :")
        text_obj = c.beginText(50, y-20); text_obj.setFont("Helvetica", 10)
        for line in wrap(user_input, w-100): text_obj.textLine(line)
        c.drawText(text_obj)
        y2 = text_obj.getY()-30
        c.setFont("Helvetica-Bold", 12); c.drawString(50, y2, "✅ Analyse réglementaire :")
        res_obj = c.beginText(50, y2-20); res_obj.setFont("Helvetica", 10)
        for line in wrap(result_text, w-100): res_obj.textLine(line)
        c.drawText(res_obj)
        c.showPage(); c.save(); buffer.seek(0)
        return buffer
    pdf_bytes = generate_pdf(user_input, result_text)
    st.download_button(
        "📥 Télécharger la fiche PDF", data=pdf_bytes,
        file_name="fiche_analyse_ICPE_VRD.pdf", mime="application/pdf"
    )

# === PIED DE PAGE ===
st.markdown('<div class="bottom">© 2025 Quartus · Tous droits réservés.</div>', unsafe_allow_html=True)
