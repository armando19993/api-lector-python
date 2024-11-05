import PyPDF2
import json
import re
from typing import Dict, List

def pdf_to_json(pdf_path: str, output_path: str = None) -> Dict:
    """
    Lee un archivo PDF y lo convierte a formato JSON.
    
    Args:
        pdf_path (str): Ruta al archivo PDF
        output_path (str, optional): Ruta donde guardar el archivo JSON
    
    Returns:
        Dict: Diccionario con el contenido del PDF
    """
    # Diccionario para almacenar el contenido
    pdf_content = {
        "metadata": {},
        "pages": []
    }
    
    try:
        # Abrir el archivo PDF
        with open(pdf_path, 'rb') as file:
            # Crear el lector de PDF
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extraer metadata
            pdf_content["metadata"] = {
                "num_pages": len(pdf_reader.pages),
                "author": pdf_reader.metadata.get('/Author', ''),
                "creator": pdf_reader.metadata.get('/Creator', ''),
                "producer": pdf_reader.metadata.get('/Producer', ''),
                "subject": pdf_reader.metadata.get('/Subject', ''),
                "title": pdf_reader.metadata.get('/Title', '')
            }
            
            # Extraer texto de cada página
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # Limpiar el texto
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Agregar contenido de la página
                pdf_content["pages"].append({
                    "page_number": page_num + 1,
                    "content": text
                })
        
        # Guardar el JSON si se especifica una ruta de salida
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as json_file:
                json.dump(pdf_content, json_file, ensure_ascii=False, indent=4)
        
        return pdf_content
    
    except Exception as e:
        print(f"Error al procesar el PDF: {str(e)}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    # Cambia estas rutas según tus necesidades
    pdf_path = "sdfsdfsdf.pdf"
    json_path = "salida.json"
    
    # Convertir PDF a JSON
    resultado = pdf_to_json(pdf_path, json_path)
    
    if resultado:
        print("Conversión exitosa!")
        print(f"Número de páginas procesadas: {resultado['metadata']['num_pages']}")