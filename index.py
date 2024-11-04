from flask import Flask, request, jsonify
import requests
import time
from bs4 import BeautifulSoup
import re
import os
import base64

app = Flask(__name__)

# Información de la API de CapSolver y sitio objetivo
api_key = "CAP-C074AD157978C38EDC1782522ED8DC85"
site_key = "0x4AAAAAAAg1WuNb-OnOa76z"
site_url = "https://catalogo-vpfe.dian.gov.co/User/SearchDocument"
base_pdf_url = "https://catalogo-vpfe.dian.gov.co"

# Función para obtener el token CSRF desde el HTML de la página
def obtener_csrf_token(session, url):
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find("input", {"name": "__RequestVerificationToken"})
    return csrf_token.get("value") if csrf_token else None

# Función para resolver el CAPTCHA con CapSolver
def resolver_captcha():
    payload = {
        "clientKey": api_key,
        "task": {
            "type": 'AntiTurnstileTaskProxyLess',
            "websiteKey": site_key,
            "websiteURL": site_url
        }
    }
    res = requests.post("https://api.capsolver.com/createTask", json=payload)
    resp = res.json()
    task_id = resp.get("taskId")
    if not task_id:
        print("Error al crear la tarea de CAPTCHA:", res.text)
        return None

    # Espera a que el CAPTCHA esté resuelto
    while True:
        time.sleep(1)
        payload = {"clientKey": api_key, "taskId": task_id}
        res = requests.post("https://api.capsolver.com/getTaskResult", json=payload)
        resp = res.json()
        status = resp.get("status")
        if status == "ready":
            return resp.get("solution", {}).get('token')
        elif status == "failed" or resp.get("errorId"):
            print("Error al resolver el CAPTCHA:", res.text)
            return None

# Función para extraer todo el contenido en los selectores especificados
def extraer_contenido_selector(html, document_key, session):
    soup = BeautifulSoup(html, 'html.parser')

    # Selecciona el contenedor específico
    contenedor = soup.select_one("#html-gdoc > div:nth-child(3) > div > div:nth-child(2)")
    datos_factura_element = soup.select_one("#html-gdoc > div:nth-child(3) > div > div:nth-child(1) > div.col-md-4 > p")
    legitimo_tenedor_element = soup.select_one("#home > div > div.container-fluid > div:nth-child(2) > div.col-md-4.row-fe-states > span")
    pdf_link_element = datos_factura_element.select_one("a") if datos_factura_element else None

    # Nuevo elemento eventos
    eventos = []

    # Verificar si existe el elemento de la tabla de eventos
    tabla_eventos = soup.select_one("#container1 > div.table-responsive > table > tbody")
    if tabla_eventos:
        for tr in tabla_eventos.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 3:
                evento = {
                    "codigo": tds[0].get_text(strip=True),
                    "descripcion": tds[1].get_text(strip=True),
                    "fecha": tds[2].get_text(strip=True)
                }
                eventos.append(evento)

    # Si el contenedor existe, extrae el texto y los datos internos
    if contenedor:
        contenido_texto = contenedor.get_text(separator="\n", strip=True)

        # Extraer los datos de la factura
        datos_factura_texto = datos_factura_element.get_text(strip=True) if datos_factura_element else None
        datos_factura = {}

        if datos_factura_texto:
            # Usar expresiones regulares para extraer los valores
            serie_match = re.search(r'^(.*?)Serie:\s*(\w+)', datos_factura_texto)
            folio_match = re.search(r'Folio:\s*(\d+)', datos_factura_texto)
            # Modificar la expresión regular para la fecha
            fecha_match = re.search(r'Fecha.*?:\s*(\d{2}-\d{2}-\d{4})', datos_factura_texto)

            if serie_match:
                datos_factura['tipo_documento'] = serie_match.group(1).strip()  # Texto antes de Serie:
                datos_factura['serie'] = serie_match.group(2).strip()  # Valor de Serie

            if folio_match:
                # Extraer la serie como lo que está antes de "Folio:"
                folio_start_index = datos_factura_texto.find('Serie:') + len('Serie:') + 1
                folio_end_index = datos_factura_texto.find('Folio:')
                datos_factura['serie'] = datos_factura_texto[folio_start_index:folio_end_index].strip()  # Texto antes de Folio

                datos_factura['folio'] = folio_match.group(1).strip()  # Valor de Folio

            if fecha_match:
                datos_factura['fecha'] = fecha_match.group(1).strip()  # Valor de Fecha

        # Dividir contenido_texto en secciones
        secciones = {}
        lineas = contenido_texto.split('\n')

        current_section = None
        for linea in lineas:
            if "DATOS DEL EMISOR" in linea:
                current_section = "emisor"
                secciones[current_section] = {}
            elif "DATOS DEL RECEPTOR" in linea:
                current_section = "receptor"
                secciones[current_section] = {}
            elif "TOTALES E IMPUESTOS" in linea:
                current_section = "totales"
                secciones[current_section] = {}
            elif current_section == "emisor" and "NIT:" in linea:
                secciones[current_section]['NIT'] = linea.split("NIT:")[-1].strip()
            elif current_section == "emisor" and "Nombre:" in linea:
                secciones[current_section]['Nombre'] = linea.split("Nombre:")[-1].strip()
            elif current_section == "receptor" and "NIT:" in linea:
                secciones[current_section]['NIT'] = linea.split("NIT:")[-1].strip()
            elif current_section == "receptor" and "Nombre:" in linea:
                secciones[current_section]['Nombre'] = linea.split("Nombre:")[-1].strip()
            elif current_section == "totales" and "IVA:" in linea:
                secciones[current_section]['IVA'] = linea.split("IVA:")[-1].strip()
            elif current_section == "totales" and "Total:" in linea:
                secciones[current_section]['Total'] = linea.split("Total:")[-1].strip()

        # Extraer el legítimo tenedor y eliminar "Legítimo Tenedor actual: "
        legitimo_tenedor = legitimo_tenedor_element.get_text(strip=True) if legitimo_tenedor_element else None
        if legitimo_tenedor:
            legitimo_tenedor = legitimo_tenedor.replace("Legítimo Tenedor actual: ", "").strip()

        # Descargar el PDF
        pdf_base64 = None
        if pdf_link_element and pdf_link_element['href']:
            pdf_link = base_pdf_url + pdf_link_element['href']
            pdf_response = session.get(pdf_link)
            if pdf_response.status_code == 200:
                # Convertir PDF a Base64
                pdf_base64 = base64.b64encode(pdf_response.content).decode('utf-8')

        return {
            "datos_factura": datos_factura,
            "secciones": secciones,  # Añadir las secciones extraídas aquí
            "legitimo_tenedor": legitimo_tenedor,  # Añadir el legítimo tenedor aquí
            "eventos": eventos,  # Añadir los eventos aquí
            "pdf_base64": pdf_base64  # Añadir PDF en Base64 aquí
        }
    else:
        return {
            "error": "No se encontró el selector especificado en el HTML."
        }

# Ruta principal de la API para procesar el DocumentKey
@app.route('/process', methods=['GET'])
def process_document():
    document_key = request.args.get('documentKey')
    if not document_key:
        return jsonify({"error": "El parámetro 'documentKey' es requerido."}), 400

    session = requests.Session()
    csrf_token = obtener_csrf_token(session, site_url)
    if not csrf_token:
        return jsonify({"error": "No se pudo obtener el token CSRF."}), 500

    captcha_token = resolver_captcha()
    if not captcha_token:
        return jsonify({"error": "No se pudo resolver el CAPTCHA."}), 500

    payload = {
        "__RequestVerificationToken": csrf_token,
        "cf-turnstile-response": captcha_token,
        "DocumentKey": document_key
    }

    response = session.post(site_url, data=payload)
    if response.status_code == 200:
        # Extraer datos específicos y devolver en formato JSON
        data = extraer_contenido_selector(response.text, document_key, session)
        return jsonify(data)
    else:
        return jsonify({"error": f"Error en la solicitud POST: {response.status_code}"}), response.status_code

# Ejecutar la API en el puerto 5000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
