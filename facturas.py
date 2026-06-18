import os
import re
import pandas as pd
import pdfplumber
import subprocess
from PyPDF2 import PdfReader, PdfWriter
from collections import defaultdict

# ================= CONFIG =================
CARPETA_PDFS = "pdfs"
EXCEL = "datos.xlsx"
SALIDA = "GRUPOS_EMPRESARIALES"
os.makedirs(SALIDA, exist_ok=True)

COL_FACTURA = "Factura"
COL_GRUPO = "Grupo empresarial"

GS_PATH = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"

# ================= REGLAS =================

INVALIDOS = {
    "#N/A", "N/A", "NA", "NAN", "NONE", "NO", "0", "",
    "-", "--", ".", "NULL", "SIN GRUPO"
}

def limpiar(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).strip().upper()
    texto = re.sub(r"\s+", " ", texto)

    if texto in INVALIDOS:
        return ""

    # elimina líneas solo símbolos
    if re.fullmatch(r'[^A-Z0-9 ]+', texto):
        return ""

    return texto

def limpiar_ruta(nombre):
    nombre = str(nombre)
    nombre = re.sub(r'[\\/*?:"<>|]', "_", nombre)
    return nombre.strip()[:120]

# ================= EXCEL =================

print("📊 Leyendo Excel...")

df = pd.read_excel(EXCEL)

df[COL_FACTURA] = df[COL_FACTURA].astype(str)
df[COL_GRUPO] = df[COL_GRUPO].apply(limpiar)

# 🔥 SOLO GRUPOS VALIDOS
df = df[df[COL_GRUPO] != ""]

grupos_validos = df[COL_GRUPO].unique()

print(f"🏢 Grupos válidos detectados: {len(grupos_validos)}")

facturas = set(df[COL_FACTURA].tolist())

encontradas = defaultdict(list)
no_encontradas = set(facturas)

# ================= SCAN PDFs (OPTIMIZADO) =================

print("⚡ Escaneando PDFs...")

for archivo in os.listdir(CARPETA_PDFS):
    if not archivo.endswith(".pdf"):
        continue

    ruta = os.path.join(CARPETA_PDFS, archivo)

    try:
        with pdfplumber.open(ruta) as pdf:
            reader = PdfReader(ruta)

            for i, page in enumerate(pdf.pages):
                texto = (page.extract_text() or "").replace(" ", "").replace("\n", "")

                for factura in list(no_encontradas):
                    if factura in texto:

                        # 📄 página actual
                        encontradas[factura].append((ruta, i, reader))

                        # 📄 página siguiente (IMPORTANTE)
                        if i + 1 < len(reader.pages):
                            encontradas[factura].append((ruta, i + 1, reader))

                        no_encontradas.discard(factura)

    except:
        continue

print(f"✅ Encontradas: {len(encontradas)}")
print(f"❌ No encontradas: {len(no_encontradas)}")

# ================= PDF HELPERS =================

def guardar_pdf(writer, ruta):
    with open(ruta, "wb") as f:
        writer.write(f)

def comprimir_pdf(entrada, salida):
    try:
        subprocess.run([
            GS_PATH,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={salida}",
            entrada
        ], check=True)
        return salida
    except:
        return entrada

# ================= GENERAR SOLO GRUPOS VALIDOS =================

print("\n🚀 Generando PDFs por grupos empresariales válidos...\n")

for grupo in grupos_validos:

    grupo_limpio = limpiar_ruta(grupo)
    data = df[df[COL_GRUPO] == grupo]

    writer_final = PdfWriter()
    contador = 0

    seen_pages = set()  # 🔥 evita duplicados

    for _, fila in data.iterrows():
        factura = str(fila[COL_FACTURA])

        if factura in encontradas:

            for ruta, i, reader in encontradas[factura]:

                key = (ruta, i)
                if key in seen_pages:
                    continue

                seen_pages.add(key)

                writer_final.add_page(reader.pages[i])
                contador += 1

    if contador == 0:
        continue

    carpeta = os.path.join(SALIDA, grupo_limpio)
    os.makedirs(carpeta, exist_ok=True)

    salida_pdf = os.path.join(carpeta, f"{grupo_limpio}.pdf")
    guardar_pdf(writer_final, salida_pdf)

    # compresión si es grande
    size_mb = os.path.getsize(salida_pdf) / 1024 / 1024

    if size_mb > 10:
        salida_pdf = comprimir_pdf(
            salida_pdf,
            salida_pdf.replace(".pdf", "_comprimido.pdf")
        )

    print(f"📦 Generado: {grupo_limpio}")

# ================= REPORTE FINAL =================

print("\n📋 FACTURAS NO ENCONTRADAS:\n")

if no_encontradas:
    df_no = pd.DataFrame(list(no_encontradas), columns=["Factura"])
    df_no.to_excel("facturas_no_encontradas.xlsx", index=False)
    print("📁 Excel generado: facturas_no_encontradas.xlsx")
else:
    print("🎉 Todas las facturas fueron encontradas")

print("\n🚀 PROCESO TERMINADO")