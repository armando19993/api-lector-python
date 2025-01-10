from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json

# Configuración del driver
options = webdriver.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Inicializar el driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def element_to_dict(element):
    """
    Convierte un elemento DOM y sus hijos en un diccionario.
    """
    children = element.find_elements(By.XPATH, "./*")
    
    # Si no tiene hijos, devuelve el texto del elemento
    if not children:
        return element.text.strip()

    # Si tiene hijos, devuelve un diccionario con su estructura
    return {
        'tag': element.tag_name,
        'attributes': element.get_attribute('outerHTML'),
        'children': [element_to_dict(child) for child in children]
    }

try:
    # Navegar a la URL
    url = "https://catalogo-vpfe.dian.gov.co/document/Details?TrackId=3c82f17fdb4c959751b42c89da3e19ecdd9221541457a929b80aacd45779a37f93573dbdb130a922cf5693c0a11485a8"
    driver.get(url)

    # Esperar un tiempo para que se cargue el contenido dinámico
    driver.implicitly_wait(10)

    # Seleccionar el contenedor principal
    container = driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/div/div/div[2]/div")

    # Convertir la estructura a un diccionario
    container_dict = element_to_dict(container)

    # Convertir el diccionario a JSON
    container_json = json.dumps(container_dict, indent=4, ensure_ascii=False)

    # Imprimir el JSON generado
    print(container_json)

finally:
    # Cerrar el navegador
    driver.quit()