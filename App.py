from flask import Blueprint,Flask, render_template, request, redirect, url_for, flash, session, jsonify
from Resumenes import *
from random import randint
from Conexion import *
from mail import send_mail
from datetime import datetime, date
from pdfExample import gen_pdf_int,gen_pdf_fisc,gen_pdf_reci
import time
import datetime
import os
import pymysql.cursors 
import json

app = Flask(__name__,static_url_path='/static')
app.register_blueprint(resumenes)
app.secret_key = "Secret Key"


#connection=conexion()


#This is the index route where we are going to
#query on all our employee data

@app.route('/login') 
@app.route('/')
def login():
    return render_template('login.html')


@app.route('/val_log', methods=['GET','POST'])
def val_log():
    if request.method == 'POST':
        session['id_empresa'] = 0
        session['razon_soc'] = ''

        cuit = request.form['cuit']
        clave = request.form['clave']    
        print(cuit)
        print(clave)
        #connection=conexion()
        #cur = connection.cursor()
        query = 'select * from empresas where cuit = %s and clave = %s'
        params = [cuit, clave]
        data = sql(query,params)
        #cur.execute(query,params)
        #data = cur.fetchone()
        print(data)
        #connection.commit()
        #cur.close
        #connection.close()
        if data:
            session['id_empresa'] = data[0][0]
            session['razon_soc'] = data[0][1]
            session['usuario'] = randint(0, 100000)
            session['fe_hoy'] = date.today()

            #return render_template('mensaje.html',mensaje='A FAVOR DE LEANDRO...' )   
            return render_template('factufacil.html')
        else:
            flash('Sus Datos No Estan Registrados')    
            return render_template('login.html')


@app.route('/cancelar', methods = ['GET','POST'])            
def cancelar():
     return render_template('factufacil.html')


@app.route('/menu', methods = ['GET','POST'])
def menu():
     print('<h1> MENU </h1>')

# Rutina para validar CUIT
def esCUITValida(cuit):
    """
    Funcion destinada a la validación de CUIT
    """
    # Convertimos el valor a una cadena
    cuit = str(cuit)
    # Aca removemos guiones, espacios y puntos para poder trabajar
    cuit = cuit.replace("-", "") # Borramos los guiones
    cuit = cuit.replace(" ", "") # Borramos los espacios
    cuit = cuit.replace(".", "") # Borramos los puntos
    # Si no tiene 11 caracteres lo descartamos
    if len(cuit) != 11:
        return False, cuit
    # Solo resta analizar si todos los caracteres son numeros
    if not cuit.isdigit():
        return False, cuit
    # Después de estas validaciones podemos afirmar
    #   que contamos con 11 números
    # Acá comienza la magia
    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    aux = 0
    for i in range(10):
        aux += int(cuit[i]) * base[i]
    aux = 11 - (aux % 11)
    if aux == 11:
        aux = 0
    elif aux == 10:
        aux = 9
    if int(cuit[10]) == aux:
        return True, cuit
    else:
        return False, cuit


@app.route('/clientes', methods = ['GET','POST'])
def clientes():
    if not session.get('id_empresa'):
        return render_template('login.html')
    
    id_empresa = session['id_empresa']
    
    connection=conexion()
    cur = connection.cursor()
    cur.execute('SELECT * FROM cdiva order by codigo')
    data_iva = cur.fetchall()
    cur.close()


    filtro = '%'
    if request.method == 'POST':
        filtro = filtro + request.form['buscar'].strip()+filtro

    cur = connection.cursor()
    query = '''
            select c.*, 
            SUM(ifnull(d.debe,0.00) - ifnull(d.haber,0.00)) as saldo 
            from clientes c
            inner JOIN (
                select b.id_cliente as clie, sum(
                 case when b.id_tipo_comp=3 then importe * -1
                 else importe end 
                ) as debe , 0 as haber,b.id_empresa 
                from facturas_mpagos a 
                inner join facturas b on a.id_factura=b.id_factura where a.m_pago='CTA-CTE.' 
                group by b.id_cliente, b.id_empresa
            UNION 
                select r.id_cliente,0,sum(total),id_empresa  
                from recibos r group by id_cliente, id_empresa
            union 
            select m.id,0,0,m.id_empresa from clientes m    
            ) as d 
            on  d.clie=c.id and c.id_empresa=d.id_empresa
            where c.cliente like %s and c.id_empresa = %s and d.id_empresa = c.id_empresa and d.clie = c.id
            group by c.id 
            order by c.cliente
            '''
    params=[filtro, id_empresa]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
            
    session['clientes_sel'] = 0
    connection.close()

    if request.method == 'POST':
        return render_template("search_cli.html", clientes = data, civa = data_iva)
    else:   
        return render_template("clientes.html", clientes = data, civa = data_iva)
 
 
 
#this route is for inserting data to database via html forms
@app.route('/insert_cli', methods = ['POST'])
def insert_cli():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        try:
            cliente = request.form['cliente']
            dni = request.form['dni']
            cliente = cliente.upper()
            domicilio = request.form['domicilio']
            domicilio = domicilio.upper()
            telefonos = request.form['telefonos']
            email = request.form['email']
            cuit = request.form['cuit']
            iva = request.form['iva']
            localidad = request.form['localidad']
            localidad = localidad.upper()
            cp = request.form['cp']
            id_empresa = session['id_empresa']
            print(iva)
            if iva != '5': # 5 Consumidor Final
                ### valido cuit del cliente
                esbueno =  esCUITValida(cuit)
                if not esbueno[0]:
                    flash('ERROR El C.U.I.T. : '+ esbueno[1] + " ES INVALIDO REGISTRO CANCELADO !!")
                    return redirect(url_for('clientes'))
                else:
                    ### busco si el cuit ya existe
                    if len(cuit) > 0:
                        connection=conexion()
                        cur = connection.cursor()
                        query = """
                                SELECT cliente
                                FROM clientes 
                                where cuit = %s and id_empresa = %s
                        """
                        params = [cuit, id_empresa]
                        cur.execute(query,params)
                        data = cur.fetchone()
                        connection.commit()
                        connection.close()
                        if data !=  None:
                            for row in data:
                                cliente = data
                                flash('ERROR El C.U.I.T. PERTENECE A: '+ cliente[0] + " REGISTRO CANCELADO !!")
                                return redirect(url_for('cliente'))
            
            connection=conexion()           
            cur = connection.cursor()
            query = "INSERT INTO clientes (cliente, domicilio, telefonos, email, cuit, iva, localidad, cp, id_empresa, dni) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            params = [cliente, domicilio, telefonos, email, cuit, iva, localidad, cp, id_empresa, dni]
            cur.execute(query, params)
            connection.commit()
            connection.close()
            flash('Cliente Agregado Correctamente')
        except:
             flash('YA EXISTE, VERIFIQUE CÓDIGO O CLIENTE  OPERACION CANCELADA ')

    #esta var es para saber si viene de clientes_sel.html 
    if  session['clientes_sel'] == 0:
        return redirect(url_for('clientes'))
    else:
        session['clientes_sel'] = 0
        return redirect(url_for('sele_clie_fa'))   

 
#this is our update route where we are going to update our employee
@app.route('/update_cli', methods = ['GET', 'POST'])
def update_cli():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        id = request.form['id']
        cliente = request.form['cliente']
        cliente = cliente.upper()
        dni = request.form['dni']
        domicilio = request.form['domicilio']
        domicilio = domicilio.upper()
        telefonos = request.form['telefonos']
        email = request.form['email']
        cuit = request.form['cuit']
        iva = request.form['iva']
        localidad = request.form['localidad']
        localidad = localidad.upper()
        cp = request.form['cp']
        print(iva)
        if iva != '5': # 5 Consumidor Final
            ### valido cuit del cliente
            esbueno =  esCUITValida(cuit)
            print(esbueno)
            if not esbueno[0]:
                flash('ERROR El C.U.I.T. : '+ esbueno[1] + " ES INVALIDO REGISTRO CANCELADO !!")
                return redirect(url_for('clientes'))
            else:
                ### busco si el cuit ya existe
                if len(cuit) > 0:
                    connection=conexion()
                    cur = connection.cursor()
                    query = """
                            SELECT cliente , id
                            FROM clientes 
                            where cuit = %s and id <> %s and id_empresa = %s
                    """
                    params = [cuit, id, session['id_empresa']]
                    cur.execute(query,params)
                    data = cur.fetchone()
                    
                    connection.close()
                    print(data)
                    #time.sleep(5) ## detiene el sistema 5 segundos
                    if data !=  None:
                        for row in data:
                            print(data[0])
                            print(data[1])
                            print('id: ' + id)
                            cliente = data
                        
                            flash('ERROR El C.U.I.T. PERTENECE A: '+ cliente[0] + " NO SE MODIFICO EL REGISTRO !!")
                            return redirect(url_for('clientes'))
            
        connection=conexion()
        cur = connection.cursor()
        query= """ 
                UPDATE clientes
                SET cliente = %s,
                domicilio = %s,
                telefonos = %s,
                email = %s,
                cuit = %s,
                iva = %s,
                localidad = %s,
                cp = %s,
                dni = %s
                WHERE id = %s
                """
        params = [cliente, domicilio, telefonos, email, cuit, iva, localidad, cp, dni, id]        
        cur.execute(query, params)
        connection.commit()
        flash('Registro modificado con Exito !')
        connection.close()

        return redirect(url_for('clientes'))
    
    
 
 
#This route is for deleting our clientes
@app.route('/delete_cli/<id>', methods = ['GET', 'POST'])
def delete_cli(id):
    if not session.get('id_empresa'):
        return render_template('login.html')
    
    connection=conexion()
    cur = connection.cursor()
    cur.execute('DELETE FROM clientes WHERE id = {0}'.format(id))
    connection.commit()
    flash('Registro borrado !')
    connection.close()
    return redirect(url_for('clientes'))
 
@app.route('/registrar', methods=['GET','POST'])
def registrar():
    return render_template('registro.html')

@app.route('/registro', methods=['GET','POST'])
def registro():
    if request.method == 'POST':
        cuit = request.form['cuit'].upper()
        razon = request.form['razon'].upper()
        direccion = request.form['direccion'].upper()
        email = request.form['email'].lower()
        clave =  request.form['clave'].upper()
        fe_ini_act = request.form['fe_ini_act']
        nro_iibb = request.form['nro_iibb']
        esbueno =  esCUITValida(cuit)
        if not esbueno[0]:
            print (esbueno[1], "No parece ser un CUIT valido, por favor vuelva a ingresarlo")
            flash('ERROR El C.U.I.T. : '+ esbueno[1] + " ES INVALIDO REGISTRO CANCELADO !!")
            return render_template('registro.html')
        else:
            ### busco si el cuit ya existe
            if len(cuit) > 0:
                connection=conexion()
                cur = connection.cursor()
                query = """
                        SELECT razon_soc
                        FROM empresas
                        where cuit = %s
                """
                params = [cuit]
                cur.execute(query,params)
                data = cur.fetchone()
                connection.commit()
                connection.close()
                if data !=  None:
                    for row in data:
                        empresa = data
                        flash('ERROR El C.U.I.T. PERTENECE A: '+ empresa[0] + " REGISTRO CANCELADO !!")
                        return render_template('registro.html')
        
            connection=conexion()
            cur = connection.cursor()
            query = 'insert into empresas (cuit, razon_soc, direccion, email, clave, fe_ini_act, nro_iibb)  values(%s, %s, %s, %s, %s, %s, %s)'
            params = [cuit, razon, direccion, email, clave, fe_ini_act, nro_iibb]
            cur.execute(query,params)
            connection.commit()
            cur.close
            connection.close()
            flash('Felicitaciones... ya esta Registrado !!!')
            return redirect(url_for('login'))


@app.route('/rubros', methods = ['GET','POST'])
def rubros():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_empresa = session['id_empresa']

    filtro = '%'
    if request.method == 'POST':
        filtro = filtro + request.form['buscar'] + filtro
    
    connection=conexion()
    query = 'SELECT * FROM rubros where rubro like %s and id_empresa = %s order by rubro'
    params = [filtro, id_empresa]
    cur = connection.cursor()
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    connection.close()
    if request.method == 'POST':
        return render_template("search_rub.html", rubros = data)
    else:
        return render_template("rubros.html", rubros = data)
 


@app.route('/insert_ru', methods = ['GET','POST'])
def insert_ru():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
       
        try:
            connection = conexion()
            rubro = request.form['rubro']
            id_empresa = session['id_empresa']
            cur = connection.cursor()
            query = 'insert into rubros (rubro, id_empresa)  values(%s, %s)'
            params = [rubro.upper(),id_empresa]
            cur.execute(query,params)
            connection.commit()
            cur.close()
            connection.close()
            flash('Rubro Agregado Correctamente')
        except:

            flash('YA EXISTE ESE RUBRO OPERACION CANCELADA ')

        return redirect(url_for('rubros'))
 


@app.route('/update_ru', methods = ['GET','POST'])
def update_ru():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        id_rub = request.form['id_rub']
        rubro = request.form['rubro']

        print(id_rub)
        connection=conexion()
        cur = connection.cursor()
        query = 'update rubros set rubro = %s where id_rubro = %s'
        params = [rubro.upper(), id_rub]
        cur.execute(query,params)
        connection.commit()
        cur.close()
        connection.close()

        flash('Registro modificado con Exito !')
 
        return redirect(url_for('rubros'))

#This route is for deleting our Rubros
@app.route('/delete_ru/<id>', methods = ['GET', 'POST'])
def delete_id(id):
    if not session.get('id_empresa'):
        return render_template('login.html')

    connection=conexion()
    cur = connection.cursor()
    cur.execute('DELETE FROM rubros WHERE id_rubro = {0}'.format(id))
    connection.commit()
    cur.close()
    connection.close()

    flash('Registro borrado !')
  
    return redirect(url_for('rubros'))


@app.route('/articulos', methods = ['GET','POST'])
def articulos():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_empresa = session['id_empresa']
    
    ########## Rubros
    connection=conexion()
    cur = connection.cursor()
    query = 'select * from rubros where id_empresa = %s order by rubro'
    params = [id_empresa]
    cur.execute(query, params)
    rub = cur.fetchall()
    cur.close()
    print(rub)

    ########## MARCAS
    cur = connection.cursor()
    query = 'select * from marcas where id_empresa = %s order by marca'
    params = [id_empresa]
    cur.execute(query, params)
    marcas = cur.fetchall()
    cur.close()

    ########## Proveedores
    cur = connection.cursor()
    query = 'select * from proveedores where id_empresa = %s order by proveedor'
    params = [id_empresa]
    cur.execute(query, params)
    proveedores = cur.fetchall()
    cur.close()

    ### proximo codigo de art ultimo + 1
    cur = connection.cursor()
    query = "select convert( max(codigo)+1, char) as codigo from articulos where id_empresa = %s"
    params = [id_empresa]
    cur.execute(query, params)
    ult = cur.fetchone()
    cur.close()

    filtro = '%'
    if request.method == 'POST':
        filtro = filtro + request.form['buscar'].strip()+filtro

    cur = connection.cursor()

    query = '''
                 SELECT id_art, codigo, barras, articulo, id_rubro, id_marca, id_prov, convert(costo, char) as costo, convert(margen1, char) as margen1, convert(precio1, char) as precio1,  convert(margen2, char) as margen2, convert(precio2,char) as precio2, convert(stock, char) as stock, convert(st_min, char) as st_min, convert(iva,char) as iva, DATE_FORMAT(fe_ult, '%%d/%%m/%%Y') as fe_ult, id_empresa  FROM articulos where id_empresa = %s and articulo like %s or codigo like %s or barras like %s  order by articulo limit 100
            '''

    params=[id_empresa, filtro, filtro, filtro]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    alicuotas = ['0.00', '10.50', '21.00', '27.00']
    connection.close()

    fecha = date.today()

    if request.method == 'POST':
        return render_template("search_art.html", articulos = data, rubros = rub, ali_iva = alicuotas, ultimo = ult, marcas = marcas, proveedores = proveedores, fecha = fecha)
    else:   
        return render_template("articulos.html", articulos = data, rubros = rub, ali_iva = alicuotas, ultimo = ult, marcas = marcas, proveedores = proveedores, fecha = fecha)
 

@app.route('/edit_arti_ajax', methods = ['GET','POST'])
def  _ajax():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_art = request.form['id_art']

    ### rubros
    id_empresa = session['id_empresa']
    connection=conexion()
    cur = connection.cursor()
    query = 'select * from rubros where id_empresa = %s order by rubro'
    params = [id_empresa]
    cur.execute(query, params)
    rub = cur.fetchall()
    cur.close()
    
    ########## MARCAS
    cur = connection.cursor()
    query = 'select * from marcas where id_empresa = %s order by marca'
    params = [id_empresa]
    cur.execute(query, params)
    marcas = cur.fetchall()
    cur.close()

    ########## Proveedores
    cur = connection.cursor()
    query = 'select * from proveedores where id_empresa = %s order by proveedor'
    params = [id_empresa]
    cur.execute(query, params)
    proveedores = cur.fetchall()
    cur.close()

    ### proximo codigo de art ultimo + 1
    cur = connection.cursor()
    query = "select max(codigo)+1 as codigo from articulos where id_empresa = %s"
    params = [id_empresa]
    cur.execute(query, params)
    ult = cur.fetchone()
    cur.close()
    
    ### articulos
    cur = connection.cursor()
    query = '''
             SELECT id_art, codigo, barras, articulo, id_rubro, id_marca, id_prov, convert(costo, char) as costo, convert(margen1, char) as margen1, convert(precio1, char) as precio1,  convert(margen2, char) as margen2, convert(precio2,char) as precio2, convert(stock, char) as stock, convert(st_min, char) as st_min, convert(iva,char) as iva, 
             DATE_FORMAT(fe_ult, '%%d/%%m/%%Y') as fe_ult, id_empresa  FROM articulos where id_empresa = %s and id_art = %s
             '''
    params=[id_empresa, id_art] 
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    print(data)

    ### alicuotas iva
    alicuotas = ['0.00', '10.50', '21.00', '27.00']

    connection.close()
    jok = {"type": "ok", "articulos": data, "rubros":rub, "ali_iva": alicuotas, "ultimo": ult, "marcas": marcas, "proveedores": proveedores}
    return jsonify(jok) 
    

 
@app.route('/mod_arti_ajax/<parametro>', methods = ['GET', 'POST'])
def mod_arti_ajax(parametro):
    if not session.get('id_empresa'):
        return render_template('login.html')
    print('mod_arti_ajax')
    if request.method == 'POST': 
        id_art = request.form['id_art']
        codigo = request.form['codigo']
        barras = request.form['barras']
        articulo = request.form['articulo']
        articulo = articulo.upper()
        id_rubro = request.form['id_rubro']
        id_marca = request.form['id_marca']
        id_prov = request.form['id_prov']
        costo = request.form['costo']
        margen1 = request.form['margen1']
        precio1 = request.form['precio1']
        margen2 = request.form['margen2']
        precio2 = request.form['precio2']
        stock = request.form['stock']
        st_min = request.form['st_min']
        iva = request.form['iva']
        fe_ult = request.form['fe_ult']
        id_empresa = session['id_empresa']
        connection=conexion()
        cur = connection.cursor()
        print("id_rubro",id_rubro)
        print("id_marca",id_marca)
        print("id_prov",id_prov)
        print("fecha:", fe_ult)
        if parametro == "1" :
            try:
                cur.execute("""
                        UPDATE articulos
                        SET codigo = %s,
                            barras = %s,
                            articulo = %s,
                            id_rubro = %s,
                            id_marca = %s,
                            id_prov = %s,
                            costo = %s,
                            margen1 = %s,
                            precio1 = %s,
                            margen2 = %s,
                            precio2 = %s,
                            stock = %s,
                            st_min = %s,
                            iva = %s,
                            fe_ult = %s
                        WHERE id_art = %s
                    """, (codigo, barras, articulo, id_rubro, id_marca, id_prov, costo, margen1, precio1, margen2, precio2, stock, st_min, iva, fe_ult, id_art))
                
                jok = {"type": "ok", "status":200  } 
                flash('Registro Modificado con Exito !')
                connection.commit()
                connection.close()    
            except:
                 flash('Error al Grabar modificación !')
        else:
            try: 
                connection=conexion()
                cur = connection.cursor()
                query = 'insert into articulos (codigo, barras, articulo, id_rubro, id_marca, id_prov, costo, margen1, precio1, margen2, precio2, stock, st_min, iva, fe_ult, id_empresa) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
                params = [codigo, barras, articulo, id_rubro, id_marca, id_prov, costo, margen1, precio1, margen2, precio2, stock, st_min, iva, fe_ult, id_empresa]
                print(params)
                cur.execute(query,params) 
                flash('Artículo Agregado Correctamente')
                connection.commit()
                connection.close()   
                jok = {"type": "ok", "status":200  } 
            except:
                flash('YA EXISTE, VERIFIQUE CÓDIGO OPERACION CANCELADA ')   
        
        return jsonify(jok)  
 


#this route is for inserting data to database via html forms
@app.route('/insert_art/', methods = ['POST'])
def insert_art():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        #try:
            print(request.form['id_rubro'])
            codigo = request.form['codigo']
            barras = request.form['barras']
            articulo = request.form['articulo']
            articulo = articulo.upper()
            id_rubro = request.form['id_rubro']
            id_marca = request.form['id_marca']
            id_prov = request.form['id_prov']
            costo = request.form['costo']
            margen1 = request.form['margen1']
            precio1 = request.form['precio1']
            margen2 = request.form['margen2']
            precio2 = request.form['precio2']
            stock = request.form['stock']
            st_min = request.form['st_min']
            iva = request.form['iva']
            id_empresa = session['id_empresa']

            connection=conexion()
            cur = connection.cursor()
            query = 'insert into articulos (codigo, barras, articulo, id_rubro, id_marca, id_prov, costo, margen1, precio1, margen2, precio2, stock, st_min, iva, id_empresa) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
            params = [codigo, barras, articulo, id_rubro, id_marca, id_prov, costo, margen1, precio1, margen2, precio2, stock, st_min, iva, id_empresa]
            print(params)
            cur.execute(query,params)
            connection.commit()
            connection.close()

            flash('Artículo Agregado Correctamente')
        #except:
            flash('YA EXISTE, VERIFIQUE CÓDIGO OPERACION CANCELADA ')

            # parametro viene de articulos_fa 
            if request.form['parametro'] == '1':
                return redirect(url_for('articulos_fa'))
            else:    
                return redirect(url_for('articulos'))


 
#this is our update route where we are going to update our articulos
@app.route('/update_art', methods = ['GET', 'POST'])
def update_art():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        id_art = request.form['id_art']
        codigo = request.form['codigo']
        articulo = request.form['articulo']
        articulo = articulo.upper()
        id_rubro = request.form['id_rubro']
        costo = request.form['costo']
        precio1 = request.form['precio1']
        precio2 = request.form['precio2']
        stock = request.form['stock']
        st_min = request.form['st_min']
        iva = request.form['iva']
    
        connection=conexion()
        cur = connection.cursor()
        cur.execute("""
            UPDATE articulos
            SET codigo = %s,
                articulo = %s,
                id_rubro = %s,
                costo = %s,
                precio1 = %s,
                precio2 = %s,
                stock = %s,
                st_min = %s,
                iva = %s
            WHERE id_art = %s
        """, (codigo, articulo, id_rubro, costo, precio1, precio2,stock, st_min, iva, id_art))
        flash('Registro modificado con Exito !')
        connection.commit()
        connection.close()
         
        return redirect(url_for('articulos'))

 
#Borrar articulos
# @app.route('/delete_art/<id>', methods = ['GET', 'POST'])
# def delete_art(id):
#     if not session.get('id_empresa'):
#         return render_template('login.html')

#     connection=conexion()
#     cur = connection.cursor()
#     cur.execute('DELETE FROM articulos WHERE id_art = {0}'.format(id))
#     connection.commit()
#     flash('Registro borrado !')
#     connection.close()

#     return redirect(url_for('articulos'))

@app.route('/delete_art_ajax', methods = ['GET', 'POST'])
def delete_art():
    if not session.get('id_empresa'):
        return render_template('login.html')
    id = request.form['id_art']
    connection=conexion()
    cur = connection.cursor()
    cur.execute('DELETE FROM articulos WHERE id_art = {0}'.format(id))
    connection.commit()
    flash('Registro borrado !')
    connection.close()

    jok = {"type": "ok", "status":200  }
    return jsonify(jok) 



@app.route('/articulos_fa', methods = ['GET', 'POST'])
def articulos_fa():
    if not session.get('id_empresa'):
        return render_template('login.html')
   
    # Borra los comprobantes que quedaron sin finalizar
    id_empresa = session['id_empresa']
    #Fecha actual
    fecha = date.today()
    connection=conexion()
    cur = connection.cursor()
    query = "delete from factura_tmp where fecha < %s and id_empresa = %s"
    params = [fecha, id_empresa]
    cur.execute(query, params)
    connection.commit()
   
    query = "delete from m_pagos_tmp where fecha < %s and id_empresa = %s"
    params = [fecha, id_empresa]
    cur.execute(query, params)
    connection.commit()
    cur.close()

    cur = connection.cursor()
    query = 'select * from rubros where id_empresa = %s order by rubro '
    params = [id_empresa]
    cur.execute(query, params)
    rub = cur.fetchall()
    cur.close()

    filtro = '%'
    if request.method == 'POST':
        filtro = filtro + request.form['buscar'].strip()+filtro

    cur = connection.cursor()
    #query = 'SELECT * FROM articulos where id_empresa = %s and articulo like %s order by articulo'
    #params=[id_empresa, filtro]
    query = 'SELECT * FROM articulos where id_empresa = %s and articulo like %s or codigo like %s or barras like %s  order by articulo limit 100'

    query = 'SELECT id_art, codigo, barras, articulo, id_rubro, id_marca, id_prov, convert(costo, char) as costo, convert(margen1, char) as margen1, convert(precio1, char) as precio1,  convert(margen2, char) as margen2, convert(precio2,char) as precio2, convert(stock, char) as stock, convert(st_min, char) as st_min, convert(iva,char) as iva, id_empresa  FROM articulos where id_empresa = %s and articulo like %s or codigo like %s or barras like %s  order by articulo limit 100' 

    params=[id_empresa, filtro, filtro, filtro]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    print(data)

     ### proximo codigo de art ultimo + 1
    cur = connection.cursor()
    query = "select max(codigo)+1 as codigo from articulos where id_empresa = %s"
    params = [id_empresa]
    cur.execute(query, params)
    ult = cur.fetchone()
    cur.close()
    connection.close()

    print(articulos)
    if request.method == 'POST':
        print('----search_art2----')
        return render_template("search_art3.html", articulos = data, rubros = rub)
    else:   
        return render_template("articulos_fa.html", articulos = data, rubros = rub, ultimo = ult)

#VISUALIZAR ARTICULOS EN COMPROBANTE TEMPORAL
@app.route('/view_art_tmp/', methods = ['GET', 'POST'])
def view_art_tmp():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_empresa = session['id_empresa']
    usuario = session['usuario']
    
    connection=conexion()
    cur = connection.cursor()
    query = "select * from factura_tmp where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()

    cur = connection.cursor()
    query = "select round( ifnull(sum( precio * cantidad *  (100-dto)/100 ) , 0),2) as importe from factura_tmp where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    data2 = cur.fetchall()
    connection.close()

    session['clie_comp'] = 0
    session['cliente'] = ''
    session['dni'] = 0

    return render_template('articulos_tmp.html', articulos = data, total = data2)



#INSERT ARTICULOS EN COMPROBANTE TEMPORAL
@app.route('/insert_art_tmp/', methods = ['GET', 'POST'])
def insert_art_tmp():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        id_empresa = session['id_empresa']
        usuario = request.form['usuario']
        id_art = request.form['id_art']  
        articulo = request.form['articulo']
        precio = request.form['precio']
        cantidad = request.form['Cantidad'] 
        iva = request.form['iva']
        dto = request.form['dto']
        #Fecha actual
        fecha = date.today()
        if cantidad == 0 or cantidad == "":
            flash(" LA CANTIDAD Y PRECIO NO PUEDEN SER CERO OPERACION CANCELADA")
            return redirect(url_for('view_art_tmp'))

        connection=conexion()
        cur = connection.cursor()
        query = "insert into factura_tmp (id_empresa, usuario, id_art, articulo, precio, cantidad, iva, dto, fecha) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        params = [id_empresa, usuario, id_art, articulo, precio, cantidad, iva, dto, fecha]
        cur.execute(query, params)
        connection.commit()
        cur.close()
        connection.close()

        return redirect(url_for('view_art_tmp'))



@app.route('/insert_art_tmp_ajax/', methods = ['GET', 'POST'])
def insert_art_tmp_ajax():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        id_empresa = session['id_empresa']
        usuario = request.form['usuario']
        id_art = request.form['id_art']  
        articulo = request.form['articulo']
        precio = request.form['precio']
        cantidad = request.form['cantidad'] 
        iva = request.form['iva']
        dto = request.form['dto']
        #Fecha actual
        fecha = date.today()
        if cantidad == 0 or cantidad == "":
            flash(" LA CANTIDAD Y PRECIO NO PUEDEN SER CERO OPERACION CANCELADA")
            #return redirect(url_for('view_art_tmp'))
            jok = {"type": "Error"}
            return jsonify(jok) 

        connection=conexion()
        cur = connection.cursor()
        query = "insert into factura_tmp (id_empresa, usuario, id_art, articulo, precio, cantidad, iva, dto, fecha) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        params = [id_empresa, usuario, id_art, articulo, precio, cantidad, iva, dto, fecha]
        cur.execute(query, params)
        connection.commit()
        cur.close()
        connection.close()

        jok = {"type": "ok"}
        return jsonify(jok) 
        #return redirect(url_for('view_art_tmp'))




# Borra el item de factura_tmp
@app.route('/delete_art_tmp/<id_tmp>', methods =['GET', 'POST'] )
def delete_art_tmp(id_tmp):
        connection=conexion()
        cur = connection.cursor()
        cur.execute('DELETE FROM factura_tmp WHERE id_tmp = {0}'.format(id_tmp))
        connection.commit()
        cur.close()
        connection.close()
        return redirect(url_for('view_art_tmp'))

# Borra todos los items de factura_tmp
@app.route('/anular_fa/', methods =['GET', 'POST'] )
def anular_fa():
    id_empresa = session['id_empresa']
    usuario = session['usuario']

    connection=conexion()
    cur = connection.cursor()
    query = "delete from factura_tmp where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    connection.commit()
    cur.close()

    #borro los medios de pago
    cur = connection.cursor()
    query = "delete from m_pagos_tmp where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    connection.commit()
    cur.close()
    connection.close()

    return redirect(url_for('view_art_tmp'))

# Selecciona el cliente a facturar
@app.route('/sele_clie_fa/', methods =['GET', 'POST'] )
def sele_clie_fa():
    if not session.get('id_empresa'):
        return render_template('login.html')
                                  
    session['clientes_sel'] = 1 # para dar de alta el cliente y saber de donde lo estoy llamando 1 es de aca 0 es de clientes
    id_empresa = session['id_empresa']

    connection=conexion()
    cur = connection.cursor()
    cur.execute('SELECT * FROM cdiva order by codigo')
    data_iva = cur.fetchall()
    cur.close()


    filtro = '%'
    if request.method == 'POST':
        filtro = filtro + request.form['buscar'].strip()+filtro

    cur = connection.cursor()
    query = 'SELECT * FROM clientes where cliente like %s and id_empresa = %s order by cliente'
    params=[filtro, id_empresa]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    connection.close()

    if request.method == 'POST':
        return render_template("search_cli_sel.html", clientes = data, civa = data_iva)
    else:   
        return render_template("clientes_sel.html", clientes = data, civa = data_iva)

# Cliente seleccionado para realizar el comprobante lo guardo en  session['clie_comp']
@app.route('/clie_comp/<id>', methods =['GET', 'POST'] )
def clie_comp(id):
    session['clie_comp'] = id
    id_cliente = id
    id_empresa = session['id_empresa']
    usuario = session['usuario']
    dni = session['dni']
    cliente = session['cliente']

    connection=conexion()
    cur = connection.cursor()
    query = 'update  factura_tmp set id_cliente =  %s  where  id_empresa = %s and usuario = %s'
    params=[id_cliente, id_empresa, usuario]
    cur.execute(query, params)
    connection.commit()
    cur.close()
    connection.close()
    return redirect(url_for('m_pagos'))

@app.route('/m_pagos', methods = ['GET','POST'] )
def m_pagos(): 
    # medios de pagos seleccionados
    id_empresa = session['id_empresa']
    usuario = session['usuario']

    connection=conexion()
    cur = connection.cursor()
    query = "select * from m_pagos_tmp where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    data1 = cur.fetchall()
    cur. close()

    #total de medios de pago
    cur = connection.cursor()
    query = "select ifnull(sum(importe),0) as total from m_pagos_tmp where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    data2 = cur.fetchall()
    cur. close()

    if int(session['clie_comp']) > 0 :
        clie_comp =  session['clie_comp'] #es el id del cliente seleccionado para realizar el comp.
        # cliente
        cur = connection.cursor()
        query = "select * from clientes where id = %s"
        params = [clie_comp]
        cur.execute(query, params)
        data3 = cur.fetchall()
        cur. close()
    else:
        if int(session['dni']) > 0 :
            cliente = session['cliente']
            dni = session['dni']
        else :     
            cliente = request.form['cliente']
            dni = request.form['dni']
            session['cliente']=cliente
            session['dni']=dni
            cur = connection.cursor()
            query = 'update factura_tmp set cliente = %s, dni = %s  where  id_empresa = %s and usuario = %s'
            params=[cliente, dni, id_empresa, usuario]
            cur.execute(query, params)
            connection.commit()
            cur.close()

        data3=[[0,cliente,'','','','',5,'','',id_empresa,dni]]

    # total de items a cobrar
    cur = connection.cursor()
    query = "select round( ifnull(sum( precio * cantidad *  (100-dto)/100 ) ,0) ,2) as importe from factura_tmp where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    data4 = cur.fetchall()

    cur. close()
    connection.close()

    return render_template('m_pagos.html', m_pagos = data1, total_mp = data2, clientes = data3, total_fa = data4 )

@app.route('/insert_mp', methods = ['GET','POST'] )
def insert_mp():
    if request.method == 'POST':
        m_pago = request.form['m_pago']
        importe = float(request.form['importe'])
        obs = request.form['obs']
        #Fecha actual
        fecha = date.today()
        usuario = session['usuario']
        id_empresa = session['id_empresa']

        connection=conexion()
        cur = connection.cursor()
        query = "insert into m_pagos_tmp (m_pago, importe, id_empresa, usuario, fecha, obs) values(%s,%s,%s,%s,%s,%s)"
        params = [m_pago, importe, id_empresa, usuario, fecha, obs]
        cur.execute(query, params)
        connection.commit()
        print(cur.lastrowid)
        cur.close()
        connection.close()
       
    return redirect(url_for('m_pagos'))

@app.route('/delete_mp_tmp/<int:id>', methods = ['GET','POST'] )
def delete_mp_tmp(id):
    print(id)
    connection=conexion()
    cur = connection.cursor()
    query = "delete from m_pagos_tmp where id_mpago = %s"
    params = [id]
    cur.execute(query, params)
    connection.commit()
    cur.close()
    connection.close()

    return redirect(url_for('m_pagos'))

@app.route('/val_mp/<t_mp>/<t_fa>/<id_cliente>', methods = ['GET','POST'])
def val_mp(t_mp, t_fa, id_cliente):
    if t_mp != t_fa :
        flash("EXISTEN DIFERENCIA ENTRE EL TOTAL A CANCELAR Y EL TOTAL DE MEDIOS DE PAGO,  OERACION CANCELADA ")
        return redirect(url_for('m_pagos'))
    else:
        total = t_fa
        if request.method == 'POST':
            id_empresa = session['id_empresa']
            usuario = session['usuario']
            #Fecha actual
            fecha = date.today()
            tipo_comp = request.form['ti_comp']
            obs_comp = request.form['obs_comp']
            #Si es interno o Remito
            if tipo_comp == "4" or  tipo_comp == "5":
                puerto = 1
                #Saco el ultimo interno 
                connection=conexion()
                cur = connection.cursor()
                query = "select ifnull( max(numero),0)+1 as numero from facturas where id_empresa = %s and id_tipo_comp = %s"
                params = [id_empresa, tipo_comp]
                cur.execute(query, params)
                data = cur.fetchall()
                cur.close()
                numero = data[0]
                dni = session['dni']
                cliente  = session['cliente']
                letra = 'I'
                
                # print('Inserto en facturas')
                #Inserto en facturas
                # Cuando grabas un INTERNO Tenes poner en FACTURAS.tipo_comp va en cero y FACTURAS.id_tipo_comp=4
                cur = connection.cursor()
                query = "insert into facturas (id_cliente, fecha, total, puerto, numero, id_empresa, tipo_comp, letra, dni, cliente, id_tipo_comp) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                params = [id_cliente, fecha, total , puerto, numero, id_empresa, 0, letra, dni, cliente, tipo_comp]
                cur.execute(query, params)
                connection.commit()
                
                #Saco el id_factura agregado
                id_factura = cur.lastrowid
                cur.close()    

                #Inserto en factura_item
                cur = connection.cursor()
                query = "select * from factura_tmp where id_empresa = %s and usuario = %s"
                params = [id_empresa, usuario]
                cur.execute(query, params)
                data = cur.fetchall()
                cur.close() 
               
                for row in data:
                    id_art = row[2]
                    articulo = row[3]
                    costo = 0
                    precio = row[4]
                    iva = row[6]
                    cantidad = row[7]
                    dto = row[5]
                    # print(row[3])
                    cur = connection.cursor()
                    query = "insert into factura_items (id_factura, id_art, articulo, costo, precio, iva, cantidad, dto) values(%s, %s, %s, %s, %s, %s, %s, %s)"
                    params = [id_factura, id_art, articulo, costo, precio, iva, cantidad, dto]
                    cur.execute(query, params)
                    connection.commit()
                    cur.close()    
                    
                    ##### Descuento el stock
                    cur = connection.cursor()
                    query = "update articulos set stock = stock - %s where id_art= %s and id_empresa = %s"
                    params = [cantidad, id_art, id_empresa]
                    cur.execute(query, params)
                    connection.commit()
                    cur.close()    

                #Inserto en facturas_mpagos 
                cur = connection.cursor()
                query = "select * from m_pagos_tmp where id_empresa = %s and usuario = %s"
                params = [id_empresa, usuario]
                cur.execute(query, params)
                data = cur.fetchall()
                cur.close() 
               
                for row in data:
                    m_pago = row[0]
                    importe = row[1]
                    id_empresa = id_empresa
                    fecha = fecha
                    obs = row[6]
                    id_factura = id_factura
    
                    cur = connection.cursor()
                    query = "insert into facturas_mpagos (m_pago, importe, id_empresa, fecha, obs, id_factura) values(%s, %s, %s, %s, %s, %s)"
                    params = [m_pago, importe, id_empresa, fecha, obs, id_factura]
                    cur.execute(query, params) 
                    connection.commit() 
                    cur.close()

                # imprimir interno 
                # print(id_factura)
                
                data1 = gen_pdf_int( id_factura )
                print(data1)
                fileName  = data1[0]
                email = data1[1]
                connection.close()
                return render_template('ver_comp.html', fileName= fileName, email = email)    

            else:    
                connection=conexion()
                cur = connection.cursor()
                session['bandera'] = randint(0,1000000)
                bandera =  session['bandera']
                query = "update factura_tmp set estado = 'E', tipo_comp = %s, bandera = %s where id_empresa = %s and usuario = %s"
                params = [tipo_comp, bandera, id_empresa, usuario]
                cur.execute(query, params)
                connection.commit()
                cur.close()
                cont01=0
                while cont01 < 4 :
                    time.sleep(3) ## detiene el sistema 3 segundos              				
                    #verifico si proceso la fact. electronica
                    cur = connection.cursor()              
                    query = "select obs from  factura_tmp  where id_empresa = %s and usuario = %s limit 1"
                    params = [id_empresa, usuario]
                    cur.execute(query, params)
                    data = cur.fetchone()
                    cur.close()
                   
                    print(data)
                    if not data is None:  #Quiere decir el registro de factura_tmp sigue alli
                        print('entre por not is none ')
                        if (data[0]) =='':
                            print('sume 1 ')
                           
                            #quiere decir  que no hay nada en observaciones..entonces puede que tarde en pasar ..vuelvo a intetar
                            cont01+=1                            
                        else: #quiere decir que hay algun menseje para mostrar de afip lo mando
                            cont01=17 #fuerzo la salida proque hay error
                    else: # si no hay nada entonces el proceso ya paso a la tabla facturas SALgo 
                        cont01=18
                if cont01==17 : 
                    #quiere decir que hay algo en observaciones de afip puestro
                    return render_template('mensaje.html',mensaje=data[0] )
                else:
                    if cont01==4: 
                        #quiere decir que ya intento 4 veces y no paso nada entonces mostramos tambien un mensaje
                        return render_template('mensaje.html',mensaje='No hay respuesta de afip. intente luego')
                    else:
                        if cont01==18:
                            print('ok')#PASO OK
                        else:
                            return render_template('mensaje.html',mensaje='Error No Contemplado en la aplicacion llamar al monje')


                #select dela factura con id_empresa,id_usuario,bandera
                #si encuentra {genera pdf etc..} idfactura_letra_puerto_numero.pdf

                cur = connection.cursor()
                query = "select id_factura from facturas where bandera = %s and  id_empresa = %s and usuario = %s"

                params = [bandera, id_empresa, usuario]
                cur.execute(query, params)
                data = cur.fetchall()
                cur.close()
                connection.close()
                print(data)

                if data:
                    id_fac = data[0][0]
                    print("id factura:",id_fac)
                    data1 = gen_pdf_fisc(id_fac)
                    print(data1)
                    fileName  = data1[0]
                    email = data1[1]
                    return render_template('ver_comp.html', fileName= fileName, email = email)    
                else:
                    return render_template('login.html') 

                
                #else     
                    #preguntar por el factura_tmp.obs. si tiene algo 
                        # seguro tiene error de afip
                    #Si no tiene nada es porque no paso aun por afip    



@app.route('/estado/', methods = ['GET','POST'])
def estado():
    id_empresa = session['id_empresa']
    usuario = session['id_usuario']
    
    connection=conexion()
    cur = connection.cursor()
    query = "update factura_tmp set estado = 'E' where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    connection.commit()
    cur.close()
    connection.close()
    
    return render_template('procesando.html')


@app.route('/cta_cte/<id>', methods = ['GET','POST'])
def cta_cte(id):
    connection=conexion()
    cur = connection.cursor()
    hasta = datetime.datetime.utcnow()
    desde = hasta - datetime.timedelta(days=60)
    id_empresa = session['id_empresa']

    if request.method == 'POST':
        desde = datetime.datetime.strptime(request.form['desde'], '%Y-%m-%d')
        hasta =datetime.datetime.strptime(request.form['hasta'], '%Y-%m-%d')
   
    # cliente
    query = '''
                select clientes.id, clientes.cliente from clientes where  clientes.id = %s
            '''
    params = [id]
    cur.execute(query, params)
    cliente = cur.fetchall()
    # ifnull(sum(case when facturas.id_tipo_comp = 3 then facturas_mpagos.importe * -1 else facturas_mpagos.importe end),0) - (select ifnull(sum(recibos.total),0)  from recibos 
    # saldo ant   select ifnull(sum(facturas_mpagos.importe),0)- (select ifnull(sum(recibos.total),0)  from recibos 
    query = '''
                select ifnull(sum(case when facturas.id_tipo_comp = 3 then facturas_mpagos.importe * -1 else facturas_mpagos.importe end),0) - (select ifnull(sum(recibos.total),0)  from recibos 
                where id_cliente = %s and recibos.fecha < %s and id_empresa = %s) as rec, facturas.id_cliente 
                from facturas_mpagos 
                left join facturas on facturas.id_factura = facturas_mpagos.id_factura 
                where facturas_mpagos.m_pago = 'CTA-CTE.' and facturas.id_cliente= %s and facturas_mpagos.fecha < %s and facturas.id_empresa = %s
            '''
    params = [id, desde, id_empresa, id, desde, id_empresa]
    cur.execute(query, params)
    ant = cur.fetchall()

    # movimientos
    query = '''
            select T1.*,clientes.id,clientes.cliente from (
            select facturas.fecha ,
            concat(CASE WHEN facturas.id_tipo_comp = 1 THEN 'FC '
            WHEN facturas.id_tipo_comp = 2 THEN 'ND '
            WHEN facturas.id_tipo_comp = 3 THEN 'NC '
            WHEN facturas.id_tipo_comp = 4 THEN 'IN '
            END  ,  facturas.letra,' ',lpad(facturas.puerto,5,'0'),'-',lpad(facturas.numero,8,'0')) as nro,
            case when facturas.id_tipo_comp = 3 then facturas_mpagos.importe * -1
            else facturas_mpagos.importe end, facturas.id_factura,facturas.id_cliente,facturas.id_empresa
            from facturas_mpagos 
            left join facturas on facturas.id_factura = facturas_mpagos.id_factura 
            left join clientes on clientes.id = facturas.id_cliente
            where facturas_mpagos.m_pago = 'CTA-CTE.' 
            UNION 
            select recibos.fecha, concat('REC ','00001-',lpad(recibos.numero,8,'0')), recibos.total * -1,
            recibos.id ,recibos.id_cliente,recibos.id_empresa
            from recibos ) as T1, clientes
            where T1.id_cliente = clientes.id and T1.fecha BETWEEN %s and %s  and T1.id_cliente= %s and T1.id_empresa = %s
            order by T1.fecha
            '''
    params = [desde, hasta, id, id_empresa]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    connection.close()
    return render_template('cta_cte.html', ctacte = data, sal_ant=ant, desde=desde.strftime("%Y-%m-%d"), hasta=hasta.strftime("%Y-%m-%d"), id=id, cliente = cliente)



@app.route('/ver_fact', methods = ['GET','POST'])
def ver_fact():
    if request.method == 'POST':
        id_factura = request.form['id_factura']
        tipo = request.form['tipo']
        print('id_factura:', id_factura)
        print('tipo:', tipo)
        
        filename  = ''
        email = '' 
        if tipo == 'REC':
            query = "select m_pago, obser, concat('REC ','00001-',lpad(recibos.numero,8,'0')) as nro, total, id  from recibos where id = %s"
        else:
            if tipo == 'IN ':
                data1 = gen_pdf_int( id_factura )
            else:
                data1 = gen_pdf_fisc( id_factura )
            if data1:
                print(data1)
                filename  = data1[0]
                email = data1[1]
             
            query = '''
                    select DATE_FORMAT(facturas.fecha, '%%d/%%m/%%Y') as fecha, concat(CASE WHEN facturas.id_tipo_comp = 1 THEN 'FC '
                    WHEN facturas.id_tipo_comp = 2 THEN 'NC '
                    WHEN facturas.id_tipo_comp = 3 THEN 'ND '
                    WHEN facturas.id_tipo_comp = 4 THEN 'IN '
                    END  ,  facturas.letra,' ',lpad(facturas.puerto,5,'0'),'-',lpad(facturas.numero,8,'0')) as nro,
                    factura_items.articulo, factura_items.cantidad, factura_items.dto, factura_items.precio, factura_items.id_factura 
                    from factura_items 
                    left join facturas on facturas.id_factura = factura_items.id_factura
                    where factura_items.id_factura = %s
                    '''
        connection=conexion()
        cur = connection.cursor()
        params = [id_factura]
        cur.execute(query, params)
        data = cur.fetchall()
        cur.close()
        connection.close()
        return render_template('fac_detalle.html', detalle = data, tipo = tipo, id_factura = id_factura, filename = filename, email = email)


@app.route('/insert_mp2/<id>', methods = ['GET','POST'] )
def insert_mp2(id):
    if request.method == 'POST':
        id = id
        m_pago = request.form['m_pago']
        importe = float(request.form['importe'])
        obs = request.form['obs']
        #Fecha actual
        fecha = date.today()
        usuario = session['usuario']
        id_empresa = session['id_empresa']
       
        #Saco nro de recibo
        connection=conexion()
        cur = connection.cursor()
        query = "select ifnull( (max(numero) + 1),1) as numero from recibos where id_empresa = %s"
        params = [id_empresa]
        cur.execute(query, params)
        data = cur.fetchall()
        numero = data[0]
        cur.close()

        #Guardo pago en Tabla Recibos
        cur = connection.cursor()
        query = "insert into recibos (m_pago, total, numero, id_cliente, id_empresa, fecha, obser) values(%s,%s,%s,%s,%s,%s,%s)"
        params = [m_pago, importe, numero, id, id_empresa, fecha, obs]
        cur.execute(query, params)
        connection.commit()
        print(cur.lastrowid)
        cur.close()
        connection.close()
        return redirect(url_for('cta_cte',id=id))


@app.route('/delete_reci/<id_fac>/<id_clie>/<comp>', methods = ['GET','POST'] )
def delete_reci(id_fac,id_clie,comp):
    if request.method == 'POST':
        if comp[0:3] == 'REC':
            connection=conexion()
            cur = connection.cursor()
            query = "delete from recibos where id = %s"
            params = [id_fac]
            cur.execute(query, params)
            connection.commit()
            cur.close()
            connection.close()
        elif comp[0:2] == 'IN':
            connection=conexion()
            cur = connection.cursor()
            query = "delete from facturas where id_factura = %s"
            params = [id_fac]
            cur.execute(query, params)
            connection.commit()
           
            query = "delete from factura_items where id_factura = %s"
            params = [id_fac]
            cur.execute(query, params)
            connection.commit()

            query = "delete from facturas_mpagos where id_factura = %s"
            params = [id_fac]
            cur.execute(query, params)
            connection.commit()
            cur.close()
            connection.close()


        return redirect(url_for('cta_cte',id=id_clie))


@app.route('/envio_mail', methods = ['GET','POST'] )
def envio_mail():
    print("estoy en envio mail")
    if request.method == 'POST':
        filename = request.form['filename']
        email = request.form['email']
        try:
            send_mail(filename,  email)
            return 'CORREO ENVIADO CON EXITO !!!'
        except:
            return "HUBO UN ERROR, EL CORREO NO FUE ENVIADO !!!"
   
@app.route('/envio_mail2/<file_name>/<email>', methods = ['GET','POST'] )
def envio_mail2(file_name, email):
    print("estoy en envio mail")
    print(file_name, " --- ", email)
    try:
        send_mail(file_name,  email)
        return render_template('mensaje.html',mensaje='CORREO ENVIADO CON EXITO !!!' ) 
        #return 'CORREO ENVIADO CON EXITO !!!'
    except:
        return render_template('mensaje.html',mensaje='HUBO UN ERROR, EL CORREO NO FUE ENVIADO !!!' ) 
        #return "HUBO UN ERROR, EL CORREO NO FUE ENVIADO !!!"
    

    #return render_template('ver_comp.html', fileName= fileName, email= email)   


@app.route('/ver_comp', methods = ['GET','POST'] )
def ver_comp():
     fileName = '1_B00013_00000003.pdf'
     return render_template('ver_comp.html', fileName= fileName)    


@app.route('/listas', methods = ['GET','POST'] )
def listas():
    return render_template('listas.html')   


@app.route('/salir', methods = ['GET','POST'] )
def salir():
    session.clear()
    return redirect(url_for('login'))    


@app.route('/marcas', methods = ['GET','POST'])
def marcas():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_empresa = session['id_empresa']

    filtro = '%'
    if request.method == 'POST':
        filtro = filtro + request.form['buscar'] + filtro
    
    print(filtro)
    
    connection=conexion()
    query = 'SELECT * FROM marcas where marca like %s and id_empresa = %s order by marca'
    params = [filtro, id_empresa]
    cur = connection.cursor()
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    connection.close()
    if request.method == 'POST':
        return render_template("search_marca.html", marcas = data)
    else:
        return render_template("marcas.html", marcas = data)
 


@app.route('/insert_marca', methods = ['GET','POST'])
def insert_marca():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        try:
            connection = conexion()
            marca = request.form['marca']
            id_empresa = session['id_empresa']
            cur = connection.cursor()
            query = 'insert into marcas (marca, id_empresa) values(%s, %s)'
            params = [marca.upper(),id_empresa]
            
            print(params)
            cur.execute(query,params)
            connection.commit()
            cur.close()

            flash('Marca Agregada Correctamente')
        except:
            flash('YA EXISTE ESA MARCA OPERACION CANCELADA ')

    return redirect(url_for('marcas'))
 


@app.route('/update_marcas', methods = ['GET','POST'])
def update_marca():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        id_marca = request.form['id_marca']
        marca = request.form['marca']

        print(id_marca)
        connection=conexion()
        cur = connection.cursor()
        query = 'update marcas set marca = %s where id_marca = %s'
        params = [marca.upper(), id_marca]
        cur.execute(query,params)
        connection.commit()
        cur.close()
        connection.close()

        flash('Registro modificado con Exito !')
 
        return redirect(url_for('marcas'))

#This route is for deleting our Marcas
@app.route('/delete_marca/<id>', methods = ['GET', 'POST'])
def delete_id_marca(id):
    if not session.get('id_empresa'):
        return render_template('login.html')

    connection=conexion()
    cur = connection.cursor()
    cur.execute('DELETE FROM marcas WHERE id_marca = {0}'.format(id))
    connection.commit()
    cur.close()
    connection.close()

    flash('Registro borrado !')
  
    return redirect(url_for('marcas'))

 
@app.route('/nuevo_precio', methods = ['GET','POST'])
def nuevo_precio():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_empresa = session['id_empresa']
    
    ########## Rubros
    connection=conexion()
    cur = connection.cursor()
    query = 'select * from rubros where id_empresa = %s order by rubro'
    params = [id_empresa]
    cur.execute(query, params)
    rub = cur.fetchall()
    cur.close()
    print(rub)

    ########## MARCAS
    cur = connection.cursor()
    query = 'select * from marcas where id_empresa = %s order by marca'
    params = [id_empresa]
    cur.execute(query, params)
    marcas = cur.fetchall()
    cur.close()

    ########## Proveedores
    cur = connection.cursor()
    query = 'select * from proveedores where id_empresa = %s order by proveedor'
    params = [id_empresa]
    cur.execute(query, params)
    proveedores = cur.fetchall()
    cur.close()

    
    return render_template("nuevo_precio.html", rubros = rub, marcas = marcas, proveedores = proveedores)

@app.route('/update_precio', methods = ['GET', 'POST'])
def update_precio():
    if not session.get('id_empresa'):
        return render_template('login.html')
  
    if request.method == 'POST':
     
        id_rubro = request.form['id_rubro']
        id_marca = request.form['id_marca']
        id_proveedor = request.form['id_proveedor']
        porcentaje = request.form['porcentaje']
        condi1 = ""
        condi2 = ""
        condi3 = ""
        param = []
        param.append(porcentaje)
        print("porcentaje:", porcentaje)
        print("id_rubro:", id_rubro)
        print("id_marca:", id_marca)
        print("id_prov:", id_proveedor)
        
        if id_rubro != '0':
            condi1 =  " id_rubro = %s"
            param.append(id_rubro)
        if id_marca != '0':
            if len(condi1) > 0:
                condi2 =  " and id_marca = %s"
                param.append(id_marca)
            else:
                condi2 =  " id_marca = %s"
                param.append(id_marca)    
        if id_proveedor != '0':
            if len(condi2) > 0:
                condi3 =  " and id_prov = %s"
                param.append(id_proveedor)    
            else:
                condi3 =  " id_prov = %s"
                param.append(id_proveedor)    
         
        print("condi:",condi1 + condi2 + condi3)  
        print('param:',param) 
    
        
        query = "update articulos set costo = costo * (1 + %s /100) where " + condi1 + condi2 + condi3
       
        print('query:', query)
        
        connection=conexion()
        cur = connection.cursor() 
        cur.execute(query,param)
        connection.commit()
        cur.close()
        connection.close() 
        print('lo ejecuto')
        
        jok = {"type": "ok", "status":200  }
        return jsonify(jok) 


@app.route('/proveedores', methods = ['GET','POST'])
def proveedores():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_empresa = session['id_empresa']
    connection=conexion()
    cur = connection.cursor()
    query = 'select * from proveedores where id_empresa = %s order by id_prov ASC'
    params = [id_empresa]
    cur.execute(query, params)
    rub = cur.fetchall()
    cur.close()

    filtro = '%'
    if request.method == 'POST':
        filtro = filtro + request.form['buscar'].strip()+filtro

    cur = connection.cursor()
    query = 'SELECT * FROM proveedores where id_empresa = %s and proveedor like %s order by id_prov ASC limit 100'
    params=[id_empresa, filtro]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    connection.close()

    if request.method == 'POST':
        return render_template("search_proveedor.html", proveedores = data)
    else:   
        return render_template("proveedores.html", proveedores = data)
 

@app.route('/edit_proveedor_ajax', methods = ['GET','POST'])
def edit_proveedor_ajax():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_proveedor = request.form['id_proveedor']
    ### rubros
    id_empresa = session['id_empresa']
    connection=conexion()

    
    ### articulos
    cur = connection.cursor()
    query = 'SELECT id_prov, proveedor, direccion, email, telefono, obs, id_empresa FROM proveedores where id_empresa = %s and id_prov = %s'
    params=[id_empresa, id_proveedor] 
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    print(data)


    connection.close()
    jok = {"type": "ok", "proveedor": data}
    return jsonify(jok) 
    
@app.route('/abm_proveedor_ajax', methods = ['GET', 'POST'])
def abm_proveedor_ajax():
    if not session.get('id_empresa'):
        return render_template('login.html')
  
    if request.method == 'POST':
        id_proveedor = request.form['id_proveedor']
        proveedor = request.form['proveedor']
        direccion = request.form['direccion']
        email = request.form['email']
        proveedor = proveedor.upper()
        telefono = request.form['telefono']
        obs = request.form['obs']
        print("provreedor: ", id_proveedor)
        connection=conexion()
        cur = connection.cursor()
        cur.execute("""
            UPDATE proveedores
            SET proveedor = %s,
                direccion = %s,
                email = %s,
                telefono = %s,
                obs = %s
            WHERE id_prov = %s
        """, (proveedor, direccion, email, telefono, obs, id_proveedor))
        flash('Registro modificado con Exito !')
        connection.commit()
        connection.close()
         
        jok = {"type": "ok", "status":200  }
        return jsonify(jok) 
 


#this route is for inserting data to database via html forms
@app.route('/insert_proveedor', methods = ['POST'])
def insert_proveedor():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
            try:
                proveedor = request.form['proveedor']
                direccion = request.form['direccion']
                proveedor = proveedor.upper()
                email = request.form['email']
                telefono = request.form['telefono']
                obs = request.form['obs']
                id_empresa = session['id_empresa']

                connection=conexion()
                cur = connection.cursor()
                query = 'insert into proveedores (proveedor, direccion, email, telefono, obs, id_empresa) VALUES (%s,%s,%s,%s,%s,%s)'
                params = [proveedor, direccion, email, telefono, obs, id_empresa]
                print(params)
                cur.execute(query,params)
                connection.commit()
                connection.close()

                flash('Proveedor Agregado Correctamente')
            except:
                flash('YA EXISTE, VERIFIQUE CÓDIGO OPERACION CANCELADA ')

            return redirect(url_for('proveedores'))
 
#this is our update route where we are going to update our articulos
@app.route('/update_proveedor', methods = ['GET', 'POST'])
def update_proveedor():
    if not session.get('id_empresa'):
        return render_template('login.html')

    if request.method == 'POST':
        id_proveedor = request.form['id_proveedor']
        proveedor = request.form['e_proveedor']
        direccion = request.form['e_direccion']
        proveedor = proveedor.upper()
        email = request.form['e_email']
        telefono = request.form['e_telefono']
        obs = request.form['e_obs']
    
        connection=conexion()
        cur = connection.cursor()
        cur.execute("""
            UPDATE proveedores
            SET proveedor = %s,
                direccion = %s,
                email = %s,
                telefono = %s,
                obs = %s
            WHERE id_prov = %s
        """, (proveedor, direccion, email, telefono, obs, id_proveedor))
        flash('Registro modificado con Exito !')
        connection.commit()
        connection.close()
         
        return redirect(url_for('proveedores'))

 


@app.route('/delete_proveedor_ajax', methods = ['GET', 'POST'])
def delete_proveedor():
    if not session.get('id_empresa'):
        return render_template('login.html')
    id = request.form['id_proveedor']
    connection=conexion()
    cur = connection.cursor()
    cur.execute('DELETE FROM proveedores WHERE id_prov = {0}'.format(id))
    connection.commit()
    flash('Registro borrado !')
    connection.close()

    jok = {"type": "ok", "status":200  }
    return jsonify(jok) 


##/////////////////////////////////////////////////////////////////////////////////////////////////////////
@app.route('/cargar_stock', methods = ['GET', 'POST'])
def cargar_stock():
    if not session.get('id_empresa'):
        return render_template('login.html')
    
    connection = conexion()
    id_empresa = session.get('id_empresa')
    ########## Proveedores
    cur = connection.cursor()
    query = 'select * from proveedores where id_empresa = %s order by proveedor'
    params = [id_empresa]
    cur.execute(query, params)
    proveedores = cur.fetchall()
    cur.close()
       

    ########## articulos
    cur = connection.cursor()
    query = '''
        select id_art, codigo, barras, articulo, costo, DATE_FORMAT(fe_ult, '%%Y/%%m/%%d') as fe_ult, id_prov from articulos where id_empresa = %s order by articulo
    '''
    params = [id_empresa]
    cur.execute(query, params)
    articulos = cur.fetchall()
    cur.close()
   
    return render_template('/cargar_stock.html', proveedores=proveedores, articulos=articulos)   

@app.route('/cargar_stock2', methods = ['GET', 'POST'])
def cargar_stock2():
    if not session.get('id_empresa'):
        return render_template('login.html')
    
    connection = conexion()
    
    id_empresa = session.get('id_empresa')
    barras = request.form['barras'].strip()
   
    id_art = request.form['id_art']

    print("barras: ", barras)
    print("id_art :", id_art)

    ########## Proveedores
    cur = connection.cursor()
    query = 'select * from proveedores where id_empresa = %s order by proveedor'
    params = [id_empresa]
    cur.execute(query, params)
    proveedores = cur.fetchall()
    cur.close()

    ########## articulo solo
    cur = connection.cursor()
    if barras != "0":
        query = '''
            select id_art, codigo, barras, articulo, costo, DATE_FORMAT(fe_ult, '%%Y/%%m/%%d') as fe_ult, id_prov from articulos where id_empresa = %s and barras = %s order by articulo
            '''
        params = [id_empresa, barras]
    if id_art != "":
        query = '''
                select id_art, codigo, barras, articulo, costo, DATE_FORMAT(fe_ult, '%%Y/%%m/%%d') as fe_ult, id_prov from articulos where id_empresa = %s and id_art = %s order by articulo
                '''
        params = [id_empresa, id_art] 
           
    cur.execute(query, params)
    articulo = cur.fetchall()
    cur.close()
    print("articulo ",articulo)
    
    ########## articulos
    cur = connection.cursor()
    query = '''
            select id_art, codigo, barras, articulo, costo, DATE_FORMAT(fe_ult, '%%Y/%%m/%%d') as fe_ult, id_prov from articulos where id_empresa = %s order by articulo
            '''
    params = [id_empresa]
    cur.execute(query,params)
    articulos = cur.fetchall()
    cur.close()

    jok = {"type": "ok", "articulos": articulos, "articulo": articulo, "proveedores": proveedores}
    return jsonify(jok)   

@app.route('/mod_stock', methods = ['GET', 'POST'])
def mod_stock():
   
        nro_comp = request.form['nro_comp']
        id_art = request.form['id_art']
        id_prov = request.form['id_prov']
        importe = request.form['importe']
        fecha = request.form['fecha']
        costo = request.form['costo']
        cantidad = request.form['cantidad']
        id_empresa = session['id_empresa']
        costo_ant = request.form['costo_ant']
        fecha_ant = request.form['fecha_ant']
       

        print("fecha_ant: ",fecha_ant)
        jok = {"type": "ok"}
        
        con = conexion()

        ##### VERIFICO PROVEEDOR
        cur = con.cursor()
        query = "select max(nro_comp) as nro_comp, max(id_prov) as id_prov from fact_prov where nro_comp = %s group  by nro_comp, id_prov, id_empresa   "
        params = [nro_comp]
        cur.execute(query,params)
        prov = cur.fetchall()
        cur.close()
        print("prov: ",prov)
        print("id_prov:",id_prov)
        for row in prov:
            if row[1] != int(id_prov) :
                print("distinto")
                jok = {"type": "404"}
                return jsonify(jok) 

        ##### GUARDO EN FACT_PROV
        cur = con.cursor()
        query = "insert into fact_prov (nro_comp, id_prov, importe, fecha, id_art, costo, costo_ant, fecha_ant, cantidad, id_empresa) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        params = [nro_comp, id_prov, importe, fecha, id_art, costo, costo_ant, fecha_ant, cantidad, id_empresa]
        cur.execute(query,params)
        con.commit()
        cur.close()

        ##### GUARDO COSTO Y CANTIDAD EN ARTICULOS
        cur = con.cursor()
        query = "update articulos set stock = stock + %s, costo = %s,  precio1 = %s * (1+(margen1/100)), precio2 = %s * (1+(margen2/100)), fe_ult = %s where id_art = %s"
        params = [cantidad, costo, costo, costo, fecha, id_art]
        cur.execute(query,params)
        con.commit()
        cur.close()

        print("paso bien")
        jok = {"type": "ok"}
 
        return jsonify(jok) 


@app.route('/ver_comp_prov/<fecha>', methods = ['GET', 'POST'] )
def ver_comp_prov(fecha):
    id_empresa = session.get('id_empresa')
   
    #if request.method == 'POST':
    #    fecha = request.form['fecha']
    #    print("post: ",fecha)
    #else: 
    #    fecha = date.today()
   
    if not fecha: 
        fecha = date.today()

    print(fecha)
   
    con = conexion()
    cur = con.cursor()
    query = '''  
            select  DATE_FORMAT(fact_prov.fecha, '%%d/%%m/%%Y') as fecha, fact_prov.nro_comp, fact_prov.Importe, proveedores.proveedor , 
            articulos.barras, articulos.articulo, fact_prov.costo_ant, fact_prov.fecha_ant, fact_prov.costo, 
            DATE_FORMAT(fact_prov.fecha_ant, '%%d/%%m/%%Y') as fecha_ant, fact_prov.cantidad 
            from fact_prov
            left join proveedores on proveedores.id_prov = fact_prov.id_prov 
            left join articulos on articulos.id_art = fact_prov.id_art
            where fecha = %s and fact_prov.id_empresa = %s group by proveedores.proveedor, fecha
            '''
    params = [fecha,id_empresa]
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    print("Articulos: ",data)
    
    cur = con.cursor()
    query = ''' 
                select proveedores.proveedor,DATE_FORMAT(fact_prov.fecha, '%%d/%%m/%%Y') as fecha, fact_prov.nro_comp, fact_prov.Importe, fact_prov.id_prov 
                from fact_prov 
                left join proveedores on proveedores.id_prov = fact_prov.id_prov 
                where fact_prov.fecha = %s and fact_prov.id_empresa = %s
                group by proveedores.proveedor, fact_prov.nro_comp  order by proveedor
    
            '''
    params=[fecha,id_empresa]
    cur.execute(query, params)        
    proveedores = cur.fetchall()
    cur.close()
    con.close()
    print("Proveedores : ", proveedores)
    return render_template('ver_comp_prov.html', data=data, proveedores=proveedores)


@app.route('/del_com_prov_ajax', methods = ['GET', 'POST'] )
def del_com_prov_ajax():
        nro_comp = request.form['nro_comp']
        fecha = request.form['fecha']
        prov = request.form['prov']
        id_prov = request.form['id_prov']
        dd = fecha[:2]
        mm = fecha[3:5]
        yyyy = fecha[6:]
        fecha = yyyy +'-'+mm+'-'+dd

        con = conexion()

        cur =con.cursor()
        query = "select * from fact_prov where nro_comp = %s and fecha = %s and id_prov = %s"
        params = [nro_comp, fecha, id_prov]
        cur.execute(query,params)
        data = cur.fetchall()
        cur.close()
        
        print("Data:",data)
        #### descuento la mercaderia cargada
        for row in data:
            cantidad = row[10]
            fecha_ant = row[9]
            id_art = row[6]
            print("cantidad: ",cantidad, "  fecha_ant: ", fecha_ant, "id_art : ", id_art)
            con = conexion()
            cur =con.cursor()
            query = "update articulos set stock = stock - %s, fe_ult = %s where id_art = %s"
            params = [cantidad, fecha_ant, id_art]
            cur.execute(query,params)
            data = cur.fetchall()
            cur.close()

        #### Borro de fact_prov
        cur =con.cursor()
        query = "delete from fact_prov where nro_comp = %s and fecha = %s and id_prov = %s"
        params = [nro_comp, fecha, id_prov]
        cur.execute(query,params)
        con.commit()
        cur.close()
        con.close()


        jok = {"type": "ok"}
        return jsonify(jok) 
      

@app.route('/gen_remito/<id>', methods = ['GET', 'POST'] )
def gen_remito(id):
    # ###################################
    # TRAIGO LOS DATOS
    # Connection
    conn = conexion()
    cur = conn.cursor()
    data=()
    query = '''
            select empresas.*, facturas.*, factura_items.*, clientes.* , articulos.codigo
            from facturas
            left join empresas on empresas.id_empresa = facturas.id_empresa 
            left join factura_items on factura_items.id_factura = facturas.id_factura 
            left join clientes on facturas.id_cliente = clientes.id
            left join articulos on articulos.id_art = factura_items.id_art 
            where facturas.id_factura = %s
            '''
    params = [id]
    cur.execute(query,params)
    data = cur.fetchall()
    cur.close
    conn.close()
    print(data)
    print(data[0][1])
    return render_template('remito.html', data=data)


@app.route('/buscar_art_ajax', methods = ['GET', 'POST'] )
def buscar_art_ajax():
    barras = '%'+request.form['barras']+'%'
    params = [barras]
    conn = conexion()
    cur = conn.cursor()
    query = 'select barras from articulos where barras like  %s'
    data = cur.execute(query,params)
    print('barras:', barras)
    print('Datos:', data)   
    if data:
        jok = {"type": "ok"}
    else:
        jok = {"type": "no"}

    return jsonify(jok) 

if __name__ == "__main__":
   
    # pongo en server en modo desarrollo
    app.run('0.0.0.0',debug=True,port=5002)
    
    # pongo en server en modo producción
    #from waitress import serve
    #serve(app, host="0.0.0.0", port=5000)