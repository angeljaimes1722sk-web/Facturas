import os
import re
import io
import tempfile
import base64

from collections import defaultdict

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from PyPDF2 import PdfReader, PdfWriter
import pdfplumber
import pandas as pd

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================

COL_FACTURA = "Factura"
COL_GRUPO = "Grupo empresarial"

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
    if re.fullmatch(r'[^A-Z0-9 ]+', texto):
        return ""
    return texto

def limpiar_ruta(nombre):
    nombre = str(nombre)
    nombre = re.sub(r'[\\/*?:"<>|]', "_", nombre)
    return nombre.strip()[:120]

# ================= INDEX =================

@app.route("/")
def index():
    return render_template("index.html")

# ================= BUSCAR POR CÓDIGOS =================

@app.route("/buscar-codigos", methods=["POST"])
def buscar_codigos():
    codigos_raw = request.form.get("codigos", "")
    facturas = [x.strip() for x in codigos_raw.split(",") if x.strip()]

    if not facturas:
        return jsonify({"error": "No ingresaste facturas"}), 400

    facturas_set = set(facturas)
    no_encontradas = set(facturas_set)
    encontradas = {}
    writer_global = PdfWriter()

    # Guardar PDFs subidos en temp para procesarlos
    temp_dir = tempfile.mkdtemp()
    temp_paths = []

    try:
        for file in request.files.getlist("pdfs"):
            if not file.filename.endswith(".pdf"):
                continue
            temp_path = os.path.join(temp_dir, file.filename)
            file.save(temp_path)
            temp_paths.append(temp_path)

        for ruta in temp_paths:
            try:
                reader = PdfReader(ruta)

                with pdfplumber.open(ruta) as pdf:
                    for i, page in enumerate(pdf.pages):
                        texto = (page.extract_text() or "").replace(" ", "").replace("\n", "")

                        for factura in list(no_encontradas):
                            if factura in texto:
                                writer = PdfWriter()

                                # Página actual
                                writer.add_page(reader.pages[i])
                                writer_global.add_page(reader.pages[i])

                                # Página siguiente
                                if i + 1 < len(reader.pages):
                                    writer.add_page(reader.pages[i + 1])
                                    writer_global.add_page(reader.pages[i + 1])

                                # Guardar individual en memoria
                                buf = io.BytesIO()
                                writer.write(buf)
                                buf.seek(0)
                                encontradas[factura] = base64.b64encode(buf.read()).decode("utf-8")

                                no_encontradas.discard(factura)

            except Exception as e:
                continue

        # Generar PDF global
        pdf_global_buf = io.BytesIO()
        writer_global.write(pdf_global_buf)
        pdf_global_buf.seek(0)
        pdf_global_base64 = base64.b64encode(pdf_global_buf.read()).decode("utf-8")

        return jsonify({
            "encontradas": list(encontradas.keys()),
            "detalles": encontradas,
            "pdf_global": pdf_global_base64,
            "no_encontradas": list(no_encontradas)
        })

    finally:
        # Limpiar temp
        for p in temp_paths:
            try:
                os.remove(p)
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass

# ================= BUSCAR POR GRUPOS =================

@app.route("/buscar-grupos", methods=["POST"])
def buscar_grupos():
    excel_file = request.files.get("excel")
    if not excel_file:
        return jsonify({"error": "No se subió Excel"}), 400

    temp_dir = tempfile.mkdtemp()
    temp_paths = []

    try:
        # Leer Excel
        df = pd.read_excel(excel_file)
        df[COL_FACTURA] = df[COL_FACTURA].astype(str)
        df[COL_GRUPO] = df[COL_GRUPO].apply(limpiar)
        df = df[df[COL_GRUPO] != ""]

        grupos_validos = df[COL_GRUPO].unique()
        facturas = set(df[COL_FACTURA].tolist())
        no_encontradas = set(facturas)
        encontradas = defaultdict(list)

        for file in request.files.getlist("pdfs"):
            if not file.filename.endswith(".pdf"):
                continue
            temp_path = os.path.join(temp_dir, file.filename)
            file.save(temp_path)
            temp_paths.append(temp_path)

        for ruta in temp_paths:
            try:
                with pdfplumber.open(ruta) as pdf:
                    for i, page in enumerate(pdf.pages):
                        texto = (page.extract_text() or "").replace(" ", "").replace("\n", "")

                        for factura in list(no_encontradas):
                            if factura in texto:
                                encontrada = (ruta, i)
                                encontradas[factura].append(encontrada)

                                # Página siguiente
                                if i + 1 < len(pdf.pages):
                                    encontradas[factura].append((ruta, i + 1))

                                no_encontradas.discard(factura)

            except Exception:
                continue

        # Construir resultado por grupo
        grupos_resultado = {}
        seen_pages = set()

        for grupo in grupos_validos:
            grupo_limpio = limpiar_ruta(grupo)
            data = df[df[COL_GRUPO] == grupo]
            facturas_grupo = []

            for _, fila in data.iterrows():
                factura = str(fila[COL_FACTURA])
                if factura in encontradas:
                    pages_info = []
                    for ruta, i in encontradas[factura]:
                        key = (ruta, i)
                        if key not in seen_pages:
                            seen_pages.add(key)
                            pages_info.append(i)
                    if pages_info:
                        facturas_grupo.append({"codigo": factura, "paginas": pages_info})

            if facturas_grupo:
                grupos_resultado[grupo] = facturas_grupo

        return jsonify({
            "grupos": grupos_resultado,
            "total_grupos": len(grupos_resultado),
            "no_encontradas": list(no_encontradas)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        for p in temp_paths:
            try:
                os.remove(p)
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass

if __name__ == "__main__":
    app.run(debug=True, port=5000)
