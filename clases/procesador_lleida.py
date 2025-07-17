# clases/procesador_pdf.py

import os
import re
import PyPDF2
import shutil
import zipfile
import tempfile
from datetime import datetime
from typing import List, Tuple, Dict
import concurrent.futures


class ProcesadorPDF:
    def __init__(self):
        """Inicializa el procesador con los patrones de búsqueda."""
        self.patrones_atencion = [
            r'Atención N°\s*(\d+)',
            r'Atención\s+No\.\s*(\d+)',
            r'ATENCION\s*[:#]?\s*(\d+)',
            r'Atención\s*[:#]?\s*(\d+)',
            r'Radicado\s*[:#]?\s*(\d+)',
            r'RADICADO\s*[:#]?\s*(\d+)',
            r'[:#]\s*(\d{5,8})',  # Números de 5-8 dígitos después de : o #
            r'Nro\.\s*(\d+)',
            r'Asunt\w*:?\s*NOTIFICACION\s*ELECTRONICA\s*PACARIBE\s*-\s*(\d+)'
        ]
    
    def procesar_archivos(self, archivos_entrada: List[str], directorio_temporal: str) -> Tuple[str, Dict]:
        """
        Procesa una lista de archivos PDF/ZIP y los renombra según los números de atención.
        
        Args:
            archivos_entrada: Lista de rutas de archivos PDF/ZIP
            directorio_temporal: Directorio temporal para trabajar
            
        Returns:
            Tuple con (ruta_zip_resultado, resumen_estadisticas)
        """
        # Crear directorio de salida
        directorio_salida = os.path.join(directorio_temporal, "pdfs_procesados")
        os.makedirs(directorio_salida, exist_ok=True)
        
        # Recopilar todos los archivos PDF
        archivos_pdf = self._recopilar_archivos_pdf(archivos_entrada, directorio_temporal)
        
        # Contadores para estadísticas
        estadisticas = {
            "total": len(archivos_pdf),
            "exitosos": 0,
            "fallidos": 0,
            "sin_numero": 0
        }
        
        # Procesar archivos en paralelo
        max_workers = min(32, os.cpu_count() + 4) if os.cpu_count() else 8
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Enviar trabajos al executor
            future_to_pdf = {
                executor.submit(self._procesar_pdf_individual, pdf, directorio_salida): pdf
                for pdf in archivos_pdf
            }
            
            # Procesar resultados
            for future in concurrent.futures.as_completed(future_to_pdf):
                pdf_original = future_to_pdf[future]
                try:
                    resultado = future.result()
                    if resultado["exitoso"]:
                        if resultado["numero_encontrado"]:
                            estadisticas["exitosos"] += 1
                        else:
                            estadisticas["sin_numero"] += 1
                    else:
                        estadisticas["fallidos"] += 1
                except Exception as e:
                    estadisticas["fallidos"] += 1
                    print(f"Error procesando {pdf_original}: {str(e)}")
        
        # Crear ZIP con los resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(directorio_temporal, f"pdfs_renombrados_{timestamp}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(directorio_salida):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, directorio_salida)
                    zipf.write(file_path, arcname)
        
        return zip_path, estadisticas
    
    def _recopilar_archivos_pdf(self, archivos_entrada: List[str], directorio_temporal: str) -> List[str]:
        """
        Recopila todos los archivos PDF de las fuentes proporcionadas.
        
        Args:
            archivos_entrada: Lista de archivos PDF/ZIP
            directorio_temporal: Directorio temporal
            
        Returns:
            Lista de rutas de archivos PDF
        """
        archivos_pdf = []
        
        for archivo in archivos_entrada:
            if archivo.lower().endswith('.pdf'):
                archivos_pdf.append(archivo)
            elif archivo.lower().endswith('.zip'):
                # Extraer archivos del ZIP
                archivos_pdf.extend(self._extraer_pdfs_de_zip(archivo, directorio_temporal))
        
        return archivos_pdf
    
    def _extraer_pdfs_de_zip(self, ruta_zip: str, directorio_temporal: str) -> List[str]:
        """
        Extrae archivos PDF de un ZIP.
        
        Args:
            ruta_zip: Ruta del archivo ZIP
            directorio_temporal: Directorio temporal
            
        Returns:
            Lista de rutas de archivos PDF extraídos
        """
        archivos_pdf = []
        directorio_extraccion = os.path.join(directorio_temporal, "zip_extraido")
        os.makedirs(directorio_extraccion, exist_ok=True)
        
        try:
            with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
                zip_ref.extractall(directorio_extraccion)
            
            # Buscar archivos PDF en el directorio extraído
            for root, dirs, files in os.walk(directorio_extraccion):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        archivos_pdf.append(os.path.join(root, file))
        
        except Exception as e:
            print(f"Error al extraer ZIP {ruta_zip}: {str(e)}")
        
        return archivos_pdf
    
    def _procesar_pdf_individual(self, ruta_pdf: str, directorio_salida: str) -> Dict:
        """
        Procesa un archivo PDF individual.
        
        Args:
            ruta_pdf: Ruta del archivo PDF
            directorio_salida: Directorio de salida
            
        Returns:
            Diccionario con información del resultado
        """
        try:
            # Extraer número de atención
            numero_atencion = self._extraer_numero_atencion(ruta_pdf)
            
            if numero_atencion:
                # Renombrar con número de atención
                nombre_salida = f"PQR_{numero_atencion}_333.pdf"
                numero_encontrado = True
            else:
                # Mantener nombre original con prefijo
                nombre_original = os.path.basename(ruta_pdf)
                nombre_salida = f"SIN_NUMERO_{nombre_original}"
                numero_encontrado = False
            
            # Copiar archivo a la carpeta de salida
            ruta_salida = os.path.join(directorio_salida, nombre_salida)
            
            # Manejar duplicados
            contador = 1
            ruta_final = ruta_salida
            while os.path.exists(ruta_final):
                nombre_base, extension = os.path.splitext(nombre_salida)
                nombre_salida_numerado = f"{nombre_base}_{contador}{extension}"
                ruta_final = os.path.join(directorio_salida, nombre_salida_numerado)
                contador += 1
            
            shutil.copy2(ruta_pdf, ruta_final)
            
            return {
                "exitoso": True,
                "numero_encontrado": numero_encontrado,
                "numero_atencion": numero_atencion,
                "nombre_salida": os.path.basename(ruta_final),
                "ruta_original": ruta_pdf
            }
        
        except Exception as e:
            return {
                "exitoso": False,
                "error": str(e),
                "ruta_original": ruta_pdf
            }
    
    def _extraer_numero_atencion(self, ruta_pdf: str) -> str:
        """
        Extrae el número de atención de un archivo PDF.
        
        Args:
            ruta_pdf: Ruta del archivo PDF
            
        Returns:
            Número de atención encontrado o None
        """
        try:
            with open(ruta_pdf, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if len(reader.pages) > 0:
                    # Extraer texto de la primera página
                    texto = reader.pages[0].extract_text()
                    
                    # Buscar número de atención usando los patrones
                    for patron in self.patrones_atencion:
                        match = re.search(patron, texto, re.IGNORECASE)
                        if match:
                            return match.group(1)
                
                # Si no se encontró en el contenido, buscar en el nombre del archivo
                nombre_archivo = os.path.basename(ruta_pdf)
                match = re.search(r'(\d{5,8})', nombre_archivo)
                if match:
                    return match.group(1)
        
        except Exception as e:
            print(f"Error al extraer número de atención de {ruta_pdf}: {str(e)}")
        
        return None