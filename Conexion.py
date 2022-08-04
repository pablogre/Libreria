import pymysql.cursors 

def conexion():
    c = pymysql.connect(host='127.0.0.1' ,
                             user= 'root', 
                             password= 'cl1v2%2605', 
                             db= 'libreria',
                             charset='utf8mb4'
                             )
    return c	

def sql(query,params):
    connection = conexion()
    cur = connection.cursor()
    sql = query 
    cur.execute(sql,params)
    data = cur.fetchall()
    cur.close()
    connection.close()
    return data

