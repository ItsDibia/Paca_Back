# procesador.py

import os
import re
import fitz
import uuid
import zipfile
from docx2pdf import convert


class ProcesadorCartas:
    def __init__(self, ruta_docx):
        self.ruta_docx = ruta_docx
        self.ruta_pdf = self._convertir_a_pdf()
        self.directorio_temporal = f"salida_{uuid.uuid4().hex}"
        os.makedirs(self.directorio_temporal, exist_ok=True)
        self.resultados = {
            "procesados": 0,
            "con_numero": 0,
            "sin_numero": 0
        }

    def _convertir_a_pdf(self):
        ruta_pdf = self.ruta_docx.replace(".docx", ".pdf")
        convert(self.ruta_docx)
        if not os.path.exists(ruta_pdf):
            raise FileNotFoundError("❌ No se generó el archivo PDF.")
        return ruta_pdf

    def _extraer_numero_atencion(self, texto):
        """
        Busca patrones como:
        PAC-DR-25-2-654321
        PAC DR 25 2 398871
        Y extrae los últimos 6 dígitos si empiezan con 3.
        """
        patron = r"PAC[-\s]*DR[-\s]*25[-\s]*2[-\s]*(\d{6})"
        match = re.search(patron, texto)
        if match:
            numero = match.group(1).strip()
            if numero.startswith("3"):
                return numero
        return None

    def _dividir_pdf_en_cartas(self):
        doc = fitz.open(self.ruta_pdf)
        total = doc.page_count

        if total % 4 != 0:
            raise ValueError("❌ El documento debe tener un múltiplo de 4 páginas.")

        desconocidos = 0

        for i in range(0, total, 4):
            subdoc = fitz.open()
            texto_concatenado = ""

            for j in range(4):
                pagina = doc.load_page(i + j)
                texto_concatenado += pagina.get_text()
                subdoc.insert_pdf(doc, from_page=i + j, to_page=i + j)

            numero = self._extraer_numero_atencion(texto_concatenado)

            if numero:
                nombre = f"PQR-{numero}.pdf"
                self.resultados["con_numero"] += 1
            else:
                desconocidos += 1
                nombre = f"PQR-Unknown-{desconocidos}.pdf"
                self.resultados["sin_numero"] += 1

            salida = os.path.join(self.directorio_temporal, nombre)
            subdoc.save(salida)
            self.resultados["procesados"] += 1

        doc.close()

    def _comprimir_en_zip(self):
        zip_nombre = f"{self.directorio_temporal}.zip"
        with zipfile.ZipFile(zip_nombre, "w", zipfile.ZIP_DEFLATED) as zipf:
            for archivo in os.listdir(self.directorio_temporal):
                ruta = os.path.join(self.directorio_temporal, archivo)
                zipf.write(ruta, arcname=archivo)
        return zip_nombre

    def procesar(self):
        self._dividir_pdf_en_cartas()
        zip_path = self._comprimir_en_zip()
        return zip_path, self.resultados
