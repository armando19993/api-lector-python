from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
import base64
import os

# Configuración del driver
options = webdriver.ChromeOptions()
# options.add_argument('--headless')  # Ejecutar sin interfaz gráfica
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Inicializar el driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # Navegar a la URL
    url = "https://catalogo-vpfe.dian.gov.co/document/Details?TrackId=3c82f17fdb4c959751b42c89da3e19ecdd9221541457a929b80aacd45779a37f93573dbdb130a922cf5693c0a11485a8"
    driver.get(url)

    # Esperar un tiempo para que se cargue el contenido dinámico
    driver.implicitly_wait(10)

    # Buscar el elemento contenedor principal
    contenedor = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[3]/div/div[1]/div[3]/p")
    tipo_documento = contenedor.find_element(By.CLASS_NAME, "tipo-doc").text
    texto_completo = contenedor.text

    # Procesar el texto para obtener datos adicionales
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

    # Descargar y convertir el PDF a base64
    response = requests.get(link_descarga)
    pdf_path = "documento.pdf"
    with open(pdf_path, "wb") as pdf_file:
        pdf_file.write(response.content)
    with open(pdf_path, "rb") as pdf_file:
        pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
    os.remove(pdf_path)

    # Información del emisor
    emisor_elemento = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[3]/div/div[2]/div[1]/p")
    datos_emisor = emisor_elemento.text

    # Información del receptor
    receptor_elemento = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[3]/div/div[2]/div[2]/p")
    datos_receptor = receptor_elemento.text

    # Total e IVA
    total_iva_elemento = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[1]/div[3]/div/div[2]/div[3]/p[2]")
    total_iva = total_iva_elemento.text

    # Legítimo tenedor
    legitimo_tenedor_elemento = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[2]/div[2]/div[2]/span")
    legitimo_tenedor = legitimo_tenedor_elemento.text.strip()

    # Listado de eventos
    tbody = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div/div[6]/div[2]/table/tbody")
    rows = tbody.find_elements(By.TAG_NAME, "tr")
    eventos = []
    for row in rows:
        codigo = row.find_element(By.XPATH, "./td[1]").text.strip()
        descripcion = row.find_element(By.XPATH, "./td[2]").text.strip()
        eventos.append({"codigo": codigo, "descripcion": descripcion})

    # Imprimir resultados
    print("Tipo de documento:", tipo_documento)
    print("Serie:", serie)
    print("Folio:", folio)
    print("Fecha de emisión:", fecha_emision)
    print("Link de descarga:", link_descarga)
    print("PDF Base64:", pdf_base64)
    print("Datos del emisor:", datos_emisor)
    print("Datos del receptor:", datos_receptor)
    print("Total e IVA:", total_iva)
    print("Legítimo tenedor:", legitimo_tenedor)
    print("Eventos:")
    for evento in eventos:
        print(f"Código: {evento['codigo']}, Descripción: {evento['descripcion']}")

finally:
    # Cerrar el navegador
    driver.quit()
