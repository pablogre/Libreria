import xlrd
import pymysql

# Open the workbook and define the worksheet
book = xlrd.open_workbook("PRECIOS.xls") # excel nombre de archivo
sheet = book.sheet_by_name("Hoja1") # Nombre de la hoja en el archivo de Excel

# Establecer una conexión MySQL
connection = pymysql.connect(host="localhost", user="root", passwd="cl1v2%2605", db="libreria")

# Obtener el objeto del cursor, utilizado para recorrer los datos de la base de datos fila por fila
cursor = connection.cursor()

# Crear instrucción SQL de inserción
#query = """INSERT INTO student (sno, sname) VALUES (%s, %s)"""
query = """INSERT INTO articulos (codigo, articulo, id_rubro, costo, precio1, precio2, iva, id_empresa, barras) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""

# Cree un bucle for para iterar a través de cada línea de datos en el archivo xls, comenzando desde la segunda línea para omitir el encabezado
'''
 El formato en excel:
 CODIGO BARRA	CODIGO	DESCRIPCION	                                                            COSTO	    PRECIO
7797630013588	1690158	ABECEDARIO DE GOMA EVA ADHESIVO KREKER EN BOLSA X 156 UNIDADES (1358)	$ 280,62	$   440
7797630003282	1690428	ABECEDARIO DE GOMA EVA C/IMAN KREKER  X 45 UNID.  (328)	                $ 977,60    $ 1.520
'''
for r in range(1, sheet.nrows):
    barras = str(sheet.cell(r, 0).value)
    codigo = sheet.cell(r, 1).value
    articulo = sheet.cell(r, 2).value
    id_rubro = 1
    costo = float(str(sheet.cell(r, 3).value))
    precio1 = float(str(sheet.cell(r, 4).value))
    precio2 = 0
    iva = 21.0
    id_empresa = 1
    values = (codigo, articulo, id_rubro, costo, precio1, precio2, iva, id_empresa, barras)
   
    
    cur = connection.cursor()
    query = 'SELECT * FROM articulos where id_empresa = %s and  barras like %s'
    params=[id_empresa, barras]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    if data:
        cur = connection.cursor()
        query = "update articulos set costo = %s, precio1 = %s where barras = %s and id_empresa = %s"
        params = [costo, precio1, barras, id_empresa]
        cur.execute(query, params)
        connection.commit()
    else:
        # Obtener el objeto del cursor, utilizado para recorrer los datos de la base de datos fila por fila
        cursor = connection.cursor()
        query = "INSERT INTO articulos (codigo, articulo, id_rubro, costo, precio1, precio2, iva, id_empresa, barras) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        # Ejecutar instrucción SQL
        cursor.execute(query, values)
        connection.commit()
        # Cerrar cursor
        cursor.close()
        
    print(barras, codigo, articulo, costo, precio1)
    

# Cerrar la conexión de la base de datos
connection.close()

# Imprimir resultado
print("")
print("Done! ")
print("")
columns = str(sheet.ncols)
rows = str(sheet.nrows)
print("Acabo de importar", columns, "Columna y", rows, "Fila de datos a MySQL!")



'''
from sqlalchemy import create_engine
import pandas as pd
db = 'libreria'
table = 'articulos'
path = 'C:/Users/HP/OneDrive/Desktop/PLATZI/PYTHON/LIBRERIA/precios.xlsx' 
url = 'mysql+mysqlconnector://root:cl1v2%2605@127.0.0.1/gestion'
engine = create_engine(url + db, echo = False)

df = pd.read_excel(path)

print('lectura ok')
df.to_sql(name = table, con = engine, if_exists = 'append', index = False)
'''
"""
Función: Importar datos de Excel a la base de datos MySQL
"""
