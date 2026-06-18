import os
import pdfplumber
import subprocess
from PyPDF2 import PdfReader, PdfWriter

# ================= CONFIG =================
CARPETA_PDFS = "pdfs"
SALIDA = "FACTURAS_EXTRAIDAS"
os.makedirs(SALIDA, exist_ok=True)

GS_PATH = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"

# ================= INPUT =================

entrada = input("✍️ Escribe los códigos de facturas (separados por coma):\n> ")

FACTURAS = [x.strip() for x in entrada.split(",") if x.strip()]

if not FACTURAS:
    print("❌ No ingresaste facturas")
    exit()

facturas_set = set(FACTURAS)
encontradas = {}
no_encontradas = set(facturas_set)

# PDF FINAL (unido)
writer_global = PdfWriter()

print("\n🔍 Buscando facturas...\n")

# ================= SCAN =================

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

                        writer = PdfWriter()

                        # 📄 página actual
                        writer.add_page(reader.pages[i])
                        writer_global.add_page(reader.pages[i])

                        # 📄 página siguiente
                        if i + 1 < len(reader.pages):
                            writer.add_page(reader.pages[i + 1])
                            writer_global.add_page(reader.pages[i + 1])

                        # guardar individual
                        salida_pdf = os.path.join(SALIDA, f"{factura}.pdf")
                        with open(salida_pdf, "wb") as f:
                            writer.write(f)

                        encontradas[factura] = salida_pdf
                        no_encontradas.discard(factura)

                        print(f"✅ Encontrada: {factura}")

    except:
        continue

# ================= GUARDAR PDF GLOBAL =================

pdf_unido = os.path.join(SALIDA, "TODAS_LAS_FACTURAS.pdf")

with open(pdf_unido, "wb") as f:
    writer_global.write(f)

# ================= COMPRESIÓN =================

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

size_mb = os.path.getsize(pdf_unido) / 1024 / 1024

if size_mb > 10:
    pdf_comprimido = pdf_unido.replace(".pdf", "_comprimido.pdf")
    pdf_unido = comprimir_pdf(pdf_unido, pdf_comprimido)

# ================= RESULTADO =================

print("\n📋 RESULTADO FINAL:\n")

print(f"✅ Encontradas: {len(encontradas)}")
print(f"❌ No encontradas: {len(no_encontradas)}")

if no_encontradas:
    print("\n❌ Faltantes:")
    for f in no_encontradas:
        print(f" - {f}")

print(f"\n📄 PDF unido generado: {pdf_unido}")
print(f"📁 Carpeta: {SALIDA}")


print("\n🚀 PROCESO TERMINADO")