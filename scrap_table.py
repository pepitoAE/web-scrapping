import requests
import boto3
import uuid
import os

def lambda_handler(event, context):
    # API interna del IGP para obtener los reportes sísmicos en formato JSON
    url = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajax/listar"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {
                'statusCode': response.status_code,
                'body': f'Error al acceder a la API del IGP. Status: {response.status_code}'
            }
        
        datos = response.json()
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error al realizar la petición a la API: {str(e)}'
        }

    # Obtener únicamente los últimos 10 sismos reportados
    sismos = datos[:10] if isinstance(datos, list) else []

    if not sismos:
        return {
            'statusCode': 404,
            'body': 'No se encontraron datos de sismos en el API'
        }

    # Conectar a DynamoDB
    dynamodb = boto3.resource('dynamodb')
    nombre_tabla = os.environ.get('TABLE_NAME', 'TablaSismosIGP')
    db_table = dynamodb.Table(nombre_tabla)

    # Limpiar la tabla de registros previos
    scan = db_table.scan()
    with db_table.batch_writer() as batch:
        for item in scan.get('Items', []):
            batch.delete_item(
                Key={
                    'id': item['id']
                }
            )

    # Insertar los 10 registros procesados en DynamoDB
    registros_guardados = []
    for i, sismo in enumerate(sismos, start=1):
        item = {
            'id': str(uuid.uuid4()),
            '#': str(i),
            'fecha_utc': str(sismo.get('fecha_utc', '')),
            'hora_utc': str(sismo.get('hora_utc', '')),
            'latitud': str(sismo.get('latitud', '')),
            'longitud': str(sismo.get('longitud', '')),
            'profundidad': str(sismo.get('profundidad', '')),
            'magnitud': str(sismo.get('magnitud', '')),
            'referencia': str(sismo.get('referencia', ''))
        }
        db_table.put_item(Item=item)
        registros_guardados.append(item)

    return {
        'statusCode': 200,
        'body': registros_guardados
    }
