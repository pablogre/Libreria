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
query = """INSERT INTO rubros (rubro) VALUES (%s)"""

# Cree un bucle for para iterar a través de cada línea de datos en el archivo xls, comenzando desde la segunda línea para omitir el encabezado
'''
 El formato en excel:
 CODIGO BARRA	CODIGO	DESCRIPCION	                                                            COSTO	    PRECIO
7797630013588	1690158	ABECEDARIO DE GOMA EVA ADHESIVO KREKER EN BOLSA X 156 UNIDADES (1358)	$ 280,62	$   440
7797630003282	1690428	ABECEDARIO DE GOMA EVA C/IMAN KREKER  X 45 UNID.  (328)	                $ 977,60    $ 1.520
'''
id_empresa = 1
for r in range(1, sheet.nrows):
    #salteo si esta vacio el codigo
    if str(sheet.cell(r, 0).value) != "":
        continue

    rubro = str(sheet.cell(r, 1).value)

    values = (rubro, id_empresa)
   
    
    cur = connection.cursor()
    query = 'SELECT * FROM rubros where id_empresa = %s and  rubro like %s'
    params=[id_empresa, rubro]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
   
    if data:
        cur = connection.cursor()
        query = "update rubros set rubro = %s where rubro = %s and id_empresa = %s"
        params = [rubro, rubro, id_empresa]
        cur.execute(query, params)
        connection.commit()
    else:
        # Obtener el objeto del cursor, utilizado para recorrer los datos de la base de datos fila por fila
        cursor = connection.cursor()
        query = "INSERT INTO rubros (rubro, id_empresa) VALUES (%s, %s)"
        # Ejecutar instrucción SQL
        cursor.execute(query, values)
        connection.commit()
        # Cerrar cursor
        cursor.close()
        print(rubro)
        
   
    

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
