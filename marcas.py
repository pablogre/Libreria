from flask import Blueprint,Flask, render_template, request, redirect, url_for, flash, session
marcas = Blueprint('marcas', __name__)
from Conexion import conexion,sql 
from random import randint
from datetime import datetime, date
import time
import datetime
import os
import pymysql.cursors 

@marcas.route('/marcas', methods = ['GET','POST'])
def marcas():
    if not session.get('id_empresa'):
        return render_template('login.html')

    id_empresa = session['id_empresa']

    filtro = '%'
    if request.method == 'POST':
        filtro = filtro + request.form['buscar'] + filtro
    
    connection=conexion()
    query = 'SELECT * FROM marcas where marca like %s and id_empresa = %s order by marca'
    params = [filtro, id_empresa]
    cur = connection.cursor()
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    connection.close()
    if request.method == 'POST':
        return render_template("search_marca.html", rubros = data)
    else:
        return render_template("marcas.html", marcas = data)
 


@marcas.route('/insert_marca', methods = ['GET','POST'])
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
 


@marcas.route('/update_marcas', methods = ['GET','POST'])
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
@marcas.route('/delete_marca/<id>', methods = ['GET', 'POST'])
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
