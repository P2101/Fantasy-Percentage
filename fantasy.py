import requests
from bs4 import BeautifulSoup

def main():
    # URL base del sitio que quieres explorar
    base_url = 'https://www.futbolfantasy.com/laliga/equipos/'
    
    # Lista de equipos en el formato que CREES que usa la web
    # (tendrás que investigar cuál es el correcto, por ejemplo: 'barcelona', 'real-madrid', etc.)
    equipos = [
        'alaves',           # Alavés
        'athletic',         # Athletic Club
        'atletico',         # Atlético de Madrid
        'barcelona',        # FC Barcelona
        'celta',            # Celta de Vigo
        'deportivo',        # RC Deportivo de La Coruña
        'elche',            # Elche CF
        'espanyol',         # RCD Espanyol
        'getafe',           # Getafe CF
        'levante',          # Levante UD
        'malaga',           # Málaga CF
        'osasuna',          # CA Osasuna
        'racing',           # Racing de Santander
        'rayo-vallecano',             # Rayo Vallecano
        'betis',            # Real Betis
        'real-madrid',      # Real Madrid
        'real-sociedad',    # Real Sociedad
        'sevilla',          # Sevilla FC
        'valencia',         # Valencia CF
        'villarreal'        # Villarreal CF
    ]    
    
    for equipo in equipos:
        url_completa = base_url + equipo
        print(f"Intentando acceder a: {url_completa}")
        
        response = requests.get(url_completa)
        
        if response.status_code == 200:
            print(f"  ¡Éxito! Página encontrada para {equipo}.")
            # Aquí iría tu código para procesar el contenido de 'response.text'
        elif response.status_code == 404:
            print(f"  Error 404: Página no encontrada para {equipo}.")
        else:
            print(f"  Error {response.status_code}: No se pudo acceder a {equipo}.")
            
        print("-" * 20)
        
        html = BeautifulSoup(response.text, 'html.parse')
        
        print(html)

if __name__ == '__main__':
    main()