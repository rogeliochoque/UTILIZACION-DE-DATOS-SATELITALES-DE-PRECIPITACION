import os
import requests
import time

# ==============================
# CONFIGURACIÓN
# ==============================
# Pon el ID de la carpeta 'Daily' que está dentro de 'NRT'
API_KEY = "AIzaSyASwh56x1hnCIVAap5riM_kH55MHPsee4E"
FOLDER_ID = "1aehP6YDNOO73ab3tvTZet2Sh5uPdG9I_" 

CARPETA_DESCARGA = r"D:\diarios_11_03_2026\nc"
ANHOS_A_DESCARGAR = ["2021", "2022"]
PAUSA_ARCHIVO = 1.5

if not os.path.exists(CARPETA_DESCARGA):
    os.makedirs(CARPETA_DESCARGA)

# ==============================
# LISTAR ARCHIVOS
# ==============================

def listar_archivos():
    archivos = []
    page_token = None
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    print(f"\nConectando con Google Drive (Folder: {FOLDER_ID})...")

    while True:
        url = "https://googleapis.com"
        params = {
            'q': f"'{FOLDER_ID}' in parents and trashed = false",
            'fields': "nextPageToken, files(id, name)",
            'key': API_KEY,
            'pageSize': 1000
        }
        if page_token:
            params['pageToken'] = page_token

        r = requests.get(url, params=params, headers=headers)
        
        # Si no devuelve 200, algo anda mal con la Key o el ID
        if r.status_code != 200:
            print(f"Error del servidor Google: {r.status_code}")
            print(f"Respuesta: {r.text}")
            return []

        try:
            data = r.json()
            batch = data.get("files", [])
            archivos.extend(batch)
            print(f"Encontrados {len(archivos)} archivos en la lista total...")
            
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        except Exception as e:
            print(f"Error procesando el JSON: {e}")
            break

    # Filtrar por año
    lista_filtrada = [
        (a["id"], a["name"]) for a in archivos 
        if any(a["name"].startswith(anho) for anho in ANHOS_A_DESCARGAR)
    ]
    
    lista_filtrada.sort(key=lambda x: x[1])
    return lista_filtrada

# ==============================
# DESCARGAR
# ==============================

def descargar(file_id, nombre):
    url = "https://google.com"
    session = requests.Session()
    
    # Intento inicial
    res = session.get(url, params={'id': file_id}, stream=True)
    
    # Buscar token de confirmación de virus
    token = None
    for k, v in res.cookies.items():
        if k.startswith('download_warning'):
            token = v
            break

    if token:
        res = session.get(url, params={'id': file_id, 'confirm': token}, stream=True)

    ruta = os.path.join(CARPETA_DESCARGA, nombre)
    with open(ruta, "wb") as f:
        for chunk in res.iter_content(chunk_size=1024*1024): # 1MB chunks
            if chunk: f.write(chunk)
    
    return ruta

# ==============================
# EJECUCIÓN
# ==============================

print("\n--- INICIANDO PROCESO MSWEP 2021-2022 ---")

archivos_validos = listar_archivos()

if not archivos_validos:
    print("\n[!] No se pudo obtener la lista. Revisa el FOLDER_ID o si la API KEY sigue activa.")
else:
    print(f"\n[+] Total a descargar: {len(archivos_validos)}")
    for i, (fid, name) in enumerate(archivos_validos, 1):
        print(f"[{i}/{len(archivos_validos)}] Descargando: {name}...", end=" ", flush=True)
        try:
            descargar(fid, name)
            print("HECHO")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(PAUSA_ARCHIVO)

print("\n--- FIN DEL PROGRAMA ---")
