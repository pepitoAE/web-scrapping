import requests
from bs4 import BeautifulSoup
import boto3
import uuid
import os

def lambda_handler(event, context):
    # URL de la página web del IGP indicada en el taller
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    response = requests.get(url)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la página del IGP'
        }

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla en la página web'
        }

    # Extraer los encabezados limpiando los espacios
    headers = [header.text.strip() for header in table.find_all('th')]

    # Extraer exactamente las últimas 10 filas (omitimos el header que es el índice 0)
    rows = []
    for row in table.find_all('tr')[1:11]: 
        cells = row.find_all('td')
        # Mapeamos cada celda con su encabezado correspondiente
        row_data = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                row_data[headers[i]] = cell.text.strip()
                
        if row_data:
            rows.append(row_data)

    # Conectar a DynamoDB
    dynamodb = boto3.resource('dynamodb')
    nombre_tabla = os.environ.get('TABLE_NAME', 'TablaSismosIGP')
    db_table = dynamodb.Table(nombre_tabla)

    # Limpiar tabla previa
    scan = db_table.scan()
    with db_table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(
                Key={
                    'id': each['id']
                }
            )

    # Insertar los 10 sismos nuevos
    for i, row in enumerate(rows, start=1):
        row['#'] = i
        row['id'] = str(uuid.uuid4())
        db_table.put_item(Item=row)

    return {
        'statusCode': 200,
        'body': rows
    }
