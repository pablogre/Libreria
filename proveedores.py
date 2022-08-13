
from flask import Blueprint,Flask, render_template, request, redirect, url_for, flash, session
proveedores = Blueprint('proveedores', __name__)
from Conexion import conexion,sql 
from random import randint
from datetime import datetime, date
import time
import datetime
import os
import pymysql.cursors 
import json



##/////////////////////////////////////////////////////////////////////////////////////////////////////////
@proveedores.route('/cargar_stock/', methods = ['GET', 'POST'])
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
   
    return render_template('proveedores/cargar_stock.html', proveedores=proveedores, articulos=articulos)   

@proveedores.route('/cargar_stock2', methods = ['GET', 'POST'])
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

@proveedores.route('/mod_stock', methods = ['GET', 'POST'])
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
        query = "insert into fact_prov (nro_comp, id_prov, importe, fecha, id_art, costo, costo_ant, fecha_ant, id_empresa) values(%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        params = [nro_comp, id_prov, importe, fecha, id_art, costo, costo_ant, fecha_ant, id_empresa]
        cur.execute(query,params)
        con.commit()
        cur.close()

        ##### GUARDO COSTO Y CANTIDAD EN ARTICULOS
        cur = con.cursor()
        query = "update articulos set stock = stock + %s, costo = %s, fe_ult = %s where id_art = %s"
        params = [cantidad, costo, fecha, id_art]
        cur.execute(query,params)
        con.commit()
        cur.close()

        print("paso bien")
        jok = {"type": "ok"}
 
        return jsonify(jok) 

@proveedores.route('proveedores/ver_comp_prov', methods = ['GET', 'POST'] )
def ver_comp_prov():
    con = conexion()
    cur = con.cursor()
    query = '''  
            select  DATE_FORMAT(fact_prov.fecha, ''%Y/%m/%d'') as fecha, fact_prov.nro_comp, fact_prov.Importe, proveedores.proveedor , 
            articulos.barras, articulos.articulo, fact_prov.costo_ant, fact_prov.fecha_ant, fact_prov.costo 
            from fact_prov
            left join proveedores on proveedores.id_prov = fact_prov.id_prov 
            left join articulos on articulos.id_art = fact_prov.id_art
            where fecha = %s
            '''
    params = ['2022/08/12']
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    print(data)