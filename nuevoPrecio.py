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
        param = "(porcentaje "
        if id_rubro:
            condi1 = condi1 + " id_rubro = %s"
            param = param + ", id_rubro"
        if id_marca:
            if condi1:
                condi2 = condi2 + " and id_marca = %s"
                param = param + ", id_marca"
        if id_proveedor:
            if condi2:
                condi3 = condi3 + " and id_proveedor = %s"
                param = param + ", id_proveedor"    
        param = param + ")"  
        print(condi1 + condi2 + condi3)  
        print(param)
        
        query = "update articulos set costo = costo * (1 + %s/100) where " + condi1 + condi2 + condi3
        print(query)
        connection=conexion()
        cur = connection.cursor() 
        cur.execute(query,param)
        flash('Registro modificado con Exito !')
        connection.commit()
        connection.close()
        
        
        jok = {"type": "ok", "status":200  }
        return jsonify(jok) 