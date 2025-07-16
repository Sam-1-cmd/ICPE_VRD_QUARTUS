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
# === GÉNÉRATION DE PDF ===
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

def generate_pdf(user_input, result_text):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- Chargement du logo Quartus ---
    logo_path = "https://www.galivel.com/media/full/nouveau_logo_quartus-5.jpg" 
    logo = ImageReader(logo_path)
    logo_width = 100  # en points
    logo_height = 40  # en points
    
    def _draw_header_footer(page_num):
        # En-tête
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Fiche d'analyse ICPE / VRD")
        # Logo en haut à droite
        c.drawImage(
            logo,
            width - 50 - logo_width, height - 50 - logo_height/2,
            width=logo_width, height=logo_height,
            mask='auto'
        )
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, f"Date : {datetime.now():%d/%m/%Y %H:%M}")
        
        # Pied de page
        footer_text = f"Page {page_num}"
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width / 2, 20, footer_text)
    
    # --- WRAP LINES ---
    def wrap_lines(text, max_width, font_name="Helvetica", font_size=10):
        """
        Coupe la chaîne `text` en plusieurs lignes pour tenir dans `max_width` pts.
        """
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = w if not cur else f"{cur} {w}"
            if c.stringWidth(test, font_name, font_size) <= max_width:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines
    
    # Contenu de la première page
    page_num = 1
    _draw_header_footer(page_num)
    
    # Section description
    y = height - 100
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "✍️ Modification décrite :")
    text_obj = c.beginText(50, y - 20)
    text_obj.setFont("Helvetica", 10)
    maxw = width - 100
    
    for raw_line in user_input.splitlines():
        for wrapped in wrap_lines(raw_line, maxw):
            text_obj.textLine(wrapped)
    c.drawText(text_obj)
    
    # Section analyse
    y_offset = text_obj.getY() - 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_offset, "✅ Analyse réglementaire :")
    
    result_text_obj = c.beginText(50, y_offset - 20)
    result_text_obj.setFont("Helvetica", 10)
    maxw2 = width - 100
    for raw_line in result_text.splitlines():
        for wrapped in wrap_lines(raw_line, maxw2):
            result_text_obj.textLine(wrapped)
    c.drawText(result_text_obj)
    
    # Fin de page 1
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# Intégration avec Streamlit
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
import streamlit as st

# --- PIED DE PAGE PROFESSIONNEL ---
st.markdown("""<style>
.footer {
  background-color: #f8f9fa;
  padding: 40px 0;
  font-family: sans-serif;
  color: #333;
}
.footer h4 {
  margin-bottom: 10px;
  font-size: 1rem;
}
.footer a {
  color: #333;
  text-decoration: none;
  font-size: 0.9rem;
}
.footer a:hover {
  text-decoration: underline;
}
.footer .social img {
  width: 24px;
  margin-right: 10px;
  vertical-align: middle;
}
.footer .bottom {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #ddd;
  font-size: 0.8rem;
  color: #666;
}
</style>""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,1,1], gap="small")
with col1:
    st.image("https://www.galivel.com/media/full/nouveau_logo_quartus-5.jpg", width=80)
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/c3/Logo-of-the-French-Government.png", width=80)
with col2:
    st.markdown("**LIENS UTILES**")
    st.markdown("""
    - [Accueil](#)
    - [Les risques](#)
    - [Recherche & Appui](#)
    - [Contactez-nous](#)
    """, unsafe_allow_html=True)
with col3:
    st.markdown("**SUIVEZ-NOUS**")
    social = {
        "Facebook": "https://image.flaticon.com/icons/png/512/733/733547.png",
        "YouTube":  "https://image.flaticon.com/icons/png/512/733/733646.png",
        "RSS":      "https://image.flaticon.com/icons/png/512/300/300221.png",
        "LinkedIn":"https://image.flaticon.com/icons/png/512/145/145807.png"
    }
    for name, url in social.items():
        st.markdown(f"<a href='#{name}' target='_blank'><img src='{url}' alt='{name}' /></a>", unsafe_allow_html=True)

st.markdown('<div class="bottom">© 2025 Quartus · Tous droits réservés.</div>', unsafe_allow_html=True)


