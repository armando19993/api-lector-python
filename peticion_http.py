from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import base64
import os
import re
app = Flask(__name__)


def scrape_document(document_key):
    url = f"https://catalogo-vpfe.dian.gov.co/document/Details?TrackId={document_key}"
    base_pdf_url = "https://catalogo-vpfe.dian.gov.co"
    response = requests.get(url)
    session = requests.Session()

    if response.status_code != 200:
        raise ValueError("No se pudo acceder a la página, código de estado: {response.status_code}")

    soup = BeautifulSoup(response.content, 'html.parser')

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
            # Usar expresiones regulares para extraer el tipo de documento, folio, fecha, y serie
            tipo_documento_match = re.search(r'^(.*?)(?:Folio:|Serie:)', datos_factura_texto)  # Captura todo antes de "Folio:" o "Serie:"
            folio_match = re.search(r'Folio:\s*(\d+)', datos_factura_texto)
            fecha_match = re.search(r'Fecha.*?:\s*(\d{2}-\d{2}-\d{4})', datos_factura_texto)
            serie_match = re.search(r'Serie:\s*(.*?)\s*Folio:', datos_factura_texto)  # Captura solo entre "Serie:" y "Folio:"

            if tipo_documento_match:
                datos_factura['tipo_documento'] = tipo_documento_match.group(1).strip()  # Valor de tipo de documento

            if serie_match:
                datos_factura['serie'] = serie_match.group(1).strip()  # Valor de Serie entre "Serie:" y "Folio:"

            if folio_match:
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

@app.route('/process', methods=['GET'])
def process_document():
    document_key = request.args.get('documentKey')
    if not document_key:
        return jsonify({"error": "documentKey is required"}), 400

    try:
        result = scrape_document(document_key)
        return jsonify(result)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Ocurrió un error inesperado", "detalle": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
