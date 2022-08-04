from flask import Blueprint,Flask, render_template, request, redirect, url_for, flash, session
resumenes = Blueprint('resumenes', __name__)
from Conexion import conexion,sql 
from random import randint
from datetime import datetime, date
import time
import datetime
import os
import pymysql.cursors 

# Connection
#connection=conexion()
#This is the index route where we are going to
#query on all our employee data
def estoy():
    if not session.get('id_empresa'):
        return render_template('login.html')
		
################################################## NICO

@resumenes.route('/iva_ventas/', methods = ['GET','POST'])
def iva_ventas():
    estoy()
    d=datetime.date.today()
    vyear = d.year
    vmonth = d.month
    tipo=''		
    if request.method == 'POST':
        vmonth = request.form['mes']
        vyear = request.form['anio']
        tipo = request.form['informe']
    id_empresa = session['id_empresa']
    #cur = connection.cursor()    
    if tipo=='resumen':
        #Resumen Por Tipo de IVa
        query = '''SELECT sum(excento) ,sum(iva21), sum(neto21) ,sum(iva105), 
        sum(neto105),sum(iva27) , sum(neto27) ,sum(iva0),sum(neto0),sum(total) 
        FROM `facturas` WHERE  cod_afip > 0 and id_empresa=%s and month(facturas.fecha)=%s and year(facturas.fecha)=%s'''
        params = [id_empresa,vmonth,vyear]
        data1=sql(query, params)        
        return render_template('resumenes/iva_ventas_resumen.html',anio=vyear,mes=vmonth,resumen=data1)
    if tipo=='detalle':
        #Detalle de Facturas
        query = '''SELECT f.dni,f.cliente,f.excento,f.neto,f.iva,f.total
        FROM facturas f  WHERE f.id_empresa=%s 
		and f.cod_afip > 0
		and month(f.fecha)=%s and year(f.fecha)=%s'''
        params = [id_empresa,vmonth,vyear] 
        data2=sql(query, params)                
        return render_template('resumenes/iva_ventas_detalle.html',anio=vyear,mes=vmonth,detalle=data2)	
    if tipo=='':
        return render_template('resumenes/iva_ventas.html',anio=vyear,mes=vmonth)

@resumenes.route('/citi_ventas/', methods = ['GET','POST'])
def citi_ventas():
    '''id_empresa = session['id_empresa']
    usuario = session['id_usuario']
    cur = connection.cursor()
    query = "update factura_tmp set estado = 'E' where id_empresa = %s and usuario = %s"
    params = [id_empresa, usuario]
    cur.execute(query, params)
    connection.commit()
    cur.close()'''
    return render_template('resumenes/citi_ventas.html')
	
@resumenes.route('/ingresos_ventas/', methods = ['GET','POST'])
def ingresos_ventas():
    estoy()
    id_empresa = session['id_empresa']
    tipo=0
    dias='0'    
    informe=''
    desde=date.today().strftime('%Y-%m-%d')
    hasta=date.today().strftime('%Y-%m-%d')
    tipocompd=0 #desde
    tipocomph=0 #hasta por tipo 
    if request.method == 'POST':
        tipo=request.form['tipo']
        dias=request.form['dias']
        informe=request.form['informe']	
        if dias=='1':
                desde='2000-01-01'  
                hasta='2050-01-01'               
        if tipo=='1':
            tipocompd=1 #desde factutas , nd , nc
            tipocomph=3
        if tipo=='2':
            tipocompd=0
            tipocomph=0
        if tipo=='3':
            tipocompd=4
            tipocomph=4
        if tipo=='4':
            tipocompd=0
            tipocomph=4        
        query = '''
            select clientes.id,
            CASE WHEN clientes.id is null THEN concat(T1.dni,' ',T1.cliente) ELSE clientes.cliente END as cliente
            ,T1.*from (
            select facturas_mpagos.m_pago,facturas.fecha ,
            concat(CASE WHEN facturas.id_tipo_comp = 1 THEN 'FC '
            WHEN facturas.id_tipo_comp = 2 THEN 'NC '
            WHEN facturas.id_tipo_comp = 3 THEN 'ND '
            WHEN facturas.id_tipo_comp = 4 THEN 'IN '
            END  ,  facturas.letra,' ',lpad(facturas.puerto,5,'0'),'-',lpad(facturas.numero,8,'0')) as nro,
            CASE WHEN id_tipo_comp=3 THEN  facturas_mpagos.importe * -1 ELSE facturas_mpagos.importe END
            , facturas.id_factura,facturas.id_cliente,facturas.id_empresa,obs,facturas.tipo_comp,facturas.dni,facturas.cliente,id_tipo_comp
            from facturas_mpagos 
            left join facturas on facturas.id_factura = facturas_mpagos.id_factura 
            left join clientes on clientes.id = facturas.id_cliente
            UNION 
            select recibos.m_pago,recibos.fecha, concat('REC ','00001-',lpad(recibos.numero,8,'0')), recibos.total,
            recibos.id ,recibos.id_cliente,recibos.id_empresa,obser,0,'','',0
            from recibos ) as T1 LEFT JOIN clientes on T1.id_cliente = clientes.id
            where  T1.fecha between DATE_ADD( %s , INTERVAL %s DAY) and %s and  T1.id_empresa = %s
            and T1.id_tipo_comp between %s and %s
            order by T1.fecha 
            '''       
        params = [desde,dias,hasta,id_empresa,tipocompd,tipocomph]     
        print(params)
        data2=sql(query, params)              
        cheque=0
        trans=0
        efec=0
        ctacte=0
        tarjeta=0
        facturas=0
        recibos=0
        internos=0
        for rs in data2:
            if rs[2]=='CHEQUE':
                cheque=cheque+rs[5]
            if rs[2]=='TRANSFERENCIA':
                trans=trans+rs[5]
            if rs[2]=='EFECTIVO':
                efec=efec+rs[5]
            if rs[2]=='TARJETA':
                tarjeta=tarjeta+rs[5]
            if rs[2]=='CTA-CTE.':
                ctacte=ctacte+rs[5]
            if rs[13]==0:
                recibos=recibos+rs[5]
            if rs[13]==4:
                internos=internos+rs[5]    
            if rs[13]>0 and  rs[13]<4:
                facturas=facturas+rs[5]    
    if informe=='':
        return render_template('resumenes/ingresos_ventas.html')
    if informe=='resumen':
        return render_template('resumenes/ingresos_tipos.html',rs=data2,efec=efec,cheque=cheque,trans=trans,ctacte=ctacte,tarjeta=tarjeta)
    if informe=='detalle':
        return render_template('resumenes/ingresos_detalle.html',rs=data2,recibos=recibos,internos=internos,facturas=facturas)	
