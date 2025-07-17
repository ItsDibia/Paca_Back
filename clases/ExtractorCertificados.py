import os
import re
import PyPDF2
from typing import List, Dict, Tuple
from pathlib import Path
import pandas as pd
import tempfile
import zipfile

class ExtractorCertificadosLleida:
    """Clase para extraer números de certificado y atención de archivos PDF."""
    
    def __init__(self):
        self.patron_certificado = r'(?:Identificador\s+del\s+certificado|Certificado|Identificación)[:\s]*(E\d+-S)'
        self.patron_asunto = r'(?:NOTIFICACION\s+ELECTRONICA\s+PACARIBE|Asunto|Atención)[\s\-:]*(\d{5,8})'

    def procesar_archivos(self, archivos_pdf: List[str], directorio_temporal: str) -> Tuple[str, Dict]:
        """
        Procesa una lista de archivos PDF y genera un Excel con los resultados.
        
        Args:
            archivos_pdf: Lista de rutas de archivos PDF
            directorio_temporal: Directorio temporal para trabajar
            
        Returns:
            Tuple con (ruta_excel_resultado, resumen_estadisticas)
        """
        # Crear directorio de salida
        directorio_salida = os.path.join(directorio_temporal, "resultados")
        os.makedirs(directorio_salida, exist_ok=True)
        
        # Procesar archivos
        resultados = []
        estadisticas = {
            "total": len(archivos_pdf),
            "exitosos": 0,
            "fallidos": 0,
            "sin_certificado": 0,
            "sin_asunto": 0
        }
        
        for ruta_pdf in archivos_pdf:
            try:
                nombre_archivo = Path(ruta_pdf).name
                certificado = self._extraer_certificado(ruta_pdf)
                asunto = self._extraer_asunto(ruta_pdf)
                
                if not certificado:
                    estadisticas["sin_certificado"] += 1
                if not asunto:
                    estadisticas["sin_asunto"] += 1
                
                if certificado or asunto:
                    estadisticas["exitosos"] += 1
                    resultados.append({
                        "Archivo": nombre_archivo,
                        "Certificado": certificado or "NO ENCONTRADO",
                        "Asunto": asunto or "NO ENCONTRADO"
                    })
                else:
                    estadisticas["fallidos"] += 1
                    
            except Exception as e:
                estadisticas["fallidos"] += 1
                resultados.append({
                    "Archivo": Path(ruta_pdf).name,
                    "Certificado": f"ERROR: {str(e)}",
                    "Asunto": ""
                })
        
        # Crear DataFrame y guardar Excel
        ruta_excel = os.path.join(directorio_salida, "resultados_certificados.xlsx")
        df = pd.DataFrame(resultados)
        df.to_excel(ruta_excel, index=False)
        
        # Crear ZIP (para consistencia con otros endpoints)
        ruta_zip = os.path.join(directorio_temporal, f"resultados_certificados.zip")
        with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(ruta_excel, os.path.basename(ruta_excel))
        
        return ruta_zip, estadisticas
    
    def _extraer_certificado(self, ruta_pdf: str) -> str:
        """Extrae el número de certificado de un PDF."""
        with open(ruta_pdf, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            texto = "\n".join(page.extract_text() or "" for page in reader.pages)
            
            match = re.search(self.patron_certificado, texto, re.IGNORECASE)
            if match:
                return match.group(1)
            
            # Buscar directamente el formato E123456789-S
            match = re.search(r'(E\d+-S)', texto)
            return match.group(1) if match else None
    
    def _extraer_asunto(self, ruta_pdf: str) -> str:
        """Extrae el número de asunto/atención de un PDF."""
        with open(ruta_pdf, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            texto = "\n".join(page.extract_text() or "" for page in reader.pages)
            
            match = re.search(self.patron_asunto, texto, re.IGNORECASE)
            if match:
                return match.group(1)
            
            # Buscar números de 5-8 dígitos después de "PACARIBE"
            match = re.search(r'PACARIBE[^\d]*(\d{5,8})', texto)
            return match.group(1) if match else None