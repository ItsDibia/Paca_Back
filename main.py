from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from tempfile import mkdtemp
import os
import shutil
from typing import List
from clases.procesador import ProcesadorCartas
from clases.procesador_lleida import ProcesadorPDF
from clases.ExtractorCertificados import ExtractorCertificadosLleida
from clases.analizador_excel import AnalizadorExcel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/procesar_docx/")
async def procesar_archivo(archivo: UploadFile = File(...)):
    if not archivo.filename.endswith(".docx"):
        return JSONResponse(status_code=400, content={"error": "Solo se aceptan archivos .docx"})

    temporal = mkdtemp()
    ruta_docx = os.path.join(temporal, archivo.filename)

    with open(ruta_docx, "wb") as f:
        f.write(await archivo.read())

    try:
        procesador = ProcesadorCartas(ruta_docx)
        zip_path, resumen = procesador.procesar()

        return FileResponse(
            zip_path,
            filename=os.path.basename(zip_path),
            media_type="application/zip",
            headers={
                "Resumen-Procesados": str(resumen["procesados"]),
                "Resumen-Con-Numero": str(resumen["con_numero"]),
                "Resumen-Sin-Numero": str(resumen["sin_numero"])
            }
        )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        shutil.rmtree(temporal, ignore_errors=True)

# Agregar este endpoint a tu main.py

@app.post("/procesar_pdfs/")
async def procesar_pdfs(archivos: List[UploadFile] = File(...)):
    # Validar que todos los archivos sean PDF o ZIP
    for archivo in archivos:
        if not (archivo.filename.endswith((".pdf", ".zip"))):
            return JSONResponse(
                status_code=400, 
                content={"error": f"Solo se aceptan archivos .pdf o .zip. Archivo rechazado: {archivo.filename}"}
            )
    
    temporal = mkdtemp()
    archivos_guardados = []
    
    try:
        # Guardar archivos subidos
        for archivo in archivos:
            ruta_archivo = os.path.join(temporal, archivo.filename)
            with open(ruta_archivo, "wb") as f:
                f.write(await archivo.read())
            archivos_guardados.append(ruta_archivo)
        
        # Procesar archivos
        procesador = ProcesadorPDF()
        zip_path, resumen = procesador.procesar_archivos(archivos_guardados, temporal)
        
        return FileResponse(
            zip_path,
            filename=os.path.basename(zip_path),
            media_type="application/zip",
            headers={
                "Resumen-Total": str(resumen["total"]),
                "Resumen-Exitosos": str(resumen["exitosos"]),
                "Resumen-Fallidos": str(resumen["fallidos"]),
                "Resumen-Sin-Numero": str(resumen["sin_numero"])
            }
        )
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        shutil.rmtree(temporal, ignore_errors=True)
        
@app.post("/procesar_certificados/")
async def procesar_certificados(archivos: List[UploadFile] = File(...)):
    # Validar que todos los archivos sean PDF
    for archivo in archivos:
        if not archivo.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=400, 
                content={"error": f"Solo se aceptan archivos PDF. Archivo rechazado: {archivo.filename}"}
            )
    
    temporal = mkdtemp()
    archivos_guardados = []
    
    try:
        # Guardar archivos subidos
        for archivo in archivos:
            ruta_archivo = os.path.join(temporal, archivo.filename)
            with open(ruta_archivo, "wb") as f:
                f.write(await archivo.read())
            archivos_guardados.append(ruta_archivo)
        
        # Procesar archivos
        extractor = ExtractorCertificadosLleida()
        zip_path, resumen = extractor.procesar_archivos(archivos_guardados, temporal)
        
        return FileResponse(
            zip_path,
            filename=os.path.basename(zip_path),
            media_type="application/zip",
            headers={
                "Resumen-Total": str(resumen["total"]),
                "Resumen-Exitosos": str(resumen["exitosos"]),
                "Resumen-Fallidos": str(resumen["fallidos"]),
                "Resumen-Sin-Certificado": str(resumen["sin_certificado"]),
                "Resumen-Sin-Asunto": str(resumen["sin_asunto"])
            }
        )
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        shutil.rmtree(temporal, ignore_errors=True)
        
