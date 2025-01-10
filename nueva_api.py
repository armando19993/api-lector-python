from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
import base64
import os

app = Flask(__name__)

def scrape_document(document_key):
    # Configuración del driver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        # Navegar a la URL
        url = f"https://catalogo-vpfe.dian.gov.co/document/Details?TrackId={document_key}"
        driver.get(url)

        driver.implicitly_wait(10)

        # Obtener elementos clave
        contenedor = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[3]/div/div[1]/div[3]/p")
        tipo_documento = contenedor.find_element(By.CLASS_NAME, "tipo-doc").text
        texto_completo = contenedor.text

        serie, folio, fecha_emision, link_descarga = None, None, None, None
        for linea in texto_completo.split("\n"):
            if "Serie:" in linea:
                serie = linea.split(": ")[1].strip()
            elif "Folio:" in linea:
                folio = linea.split(": ")[1].strip()
            elif "Fecha de emisión" in linea:
                fecha_emision = linea.split(": ")[1].strip()

        link_element = contenedor.find_element(By.CLASS_NAME, "downloadPDFUrl")
        link_descarga = link_element.get_attribute("href")

        # Descargar y codificar PDF
        response = requests.get(link_descarga)
        pdf_path = "documento.pdf"
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(response.content)
        with open(pdf_path, "rb") as pdf_file:
            pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
        os.remove(pdf_path)

        # Datos del emisor
        emisor_elemento = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[3]/div/div[2]/div[1]/p")
        datos_emisor_texto = emisor_elemento.text
        datos_emisor = {
            "NIT": datos_emisor_texto.split("\n")[1].split(": ")[1].strip(),
            "Nombre": datos_emisor_texto.split("\n")[2].split(": ")[1].strip()
        }

        # Datos del receptor
        receptor_elemento = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[3]/div/div[2]/div[2]/p")
        datos_receptor_texto = receptor_elemento.text
        datos_receptor = {
            "NIT": datos_receptor_texto.split("\n")[1].split(": ")[1].strip(),
            "Nombre": datos_receptor_texto.split("\n")[2].split(": ")[1].strip()
        }

        # Total e IVA
        total_iva_elemento = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[3]/div/div[2]/div[3]/p[2]")
        total_iva_texto = total_iva_elemento.text
        total = None
        iva = None
        for linea in total_iva_texto.split("\n"):
            if "IVA:" in linea:
                iva = linea.split(": $")[1].replace(",", "").strip()
            elif "Total:" in linea:
                total = linea.split(": $")[1].replace(",", "").strip()

        # Legítimo tenedor
        legitimo_tenedor_elemento = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[2]/div[2]/div[2]/span")
        legitimo_tenedor_texto = legitimo_tenedor_elemento.text
        legitimo_tenedor = legitimo_tenedor_texto.split(": ")[1].strip()

        # Eventos
        tbody = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[6]/div[2]/table/tbody")
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        eventos = []
        for row in rows:
            codigo = row.find_element(By.XPATH, "./td[1]").text.strip()
            descripcion = row.find_element(By.XPATH, "./td[2]").text.strip()
            eventos.append({"codigo": codigo, "descripcion": descripcion})

        # Respuesta formateada
        result = {
            "datos_factura": {
                "tipo_documento": tipo_documento,
                "serie": serie,
                "folio": folio,
                "fecha": fecha_emision,
            },
            "secciones": {
                "emisor": datos_emisor,
                "receptor": datos_receptor,
                "totales": {
                    "IVA": iva,
                    "Total": total,
                },
            },
            "pdf_base64": pdf_base64,
            "legitimo_tenedor": legitimo_tenedor,
            "eventos": eventos,
        }

        return result

    finally:
        driver.quit()


@app.route('/process', methods=['GET'])
def process_document():
    document_key = request.args.get('documentKey')
    if not document_key:
        return jsonify({"error": "documentKey is required"}), 400

    try:
        result = scrape_document(document_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
