import pandas as pd
import unicodedata
from datetime import datetime
import re
from colorama import init, Fore, Back, Style
import glob
import os
import streamlit as st
from io import BytesIO

###################################### FUNCIÓN DE LIMPIEZA DE COLUMNAS ####################################
def limpieza_comun(df, fecha):

#Para la limpieza de las columnas se necesitan los siguientes pasos:

#primer paso: CARACTERES EXTRAÑOS Y RECUPERAMIENTO DE Ñ
#Primero, sabemos que al abrir el archivo algunas de las Ñ son cambiadas a su modo lectura de excel
#Que son unas A con virgulilla y un caracter aparte, significando ñ y Ñ, necesitamos cambiar todo esto a Ñ
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(r'(Ã‘|Ã±)', 'Ñ', regex=True)

    df.columns = [re.sub(r'(Ã‘|Ã±)', 'Ñ', str(col)) for col in df.columns]

#Una vez que cambiamos los valores por Ñ, debemos guardar la Ñ, ya que acá también se limpian acentos
#Es por esto que en la forma que se limpian se deshacen de las Ñ, así que las guardamos como un caracter 
#especial que después igual es reemplazado por la Ñ de nuevo después del tratamiento
#También hacemos todo el texto de la base en mayúscula, incluyendo los títulos de columna
    def limpiar_texto(texto):
        if isinstance(texto, str):
            texto = texto.replace('ñ', '__enie__').replace('Ñ', '__ENIE__')

            texto = unicodedata.normalize('NFKD', texto)
            texto = ''.join(c for c in texto if not unicodedata.combining(c))

            texto = texto.replace('__enie__', 'ñ').replace('__ENIE__', 'Ñ')

            return texto.upper()
        return texto
    
#Aplicamos la función de limpieza a los datos, en los títulos de columnas y en todos los datos
    df.columns = [limpiar_texto(col) for col in df.columns]

    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(limpiar_texto)

#Quitamos las columnas extras, esta generación de columnas se explica máááás abajito 
    df = df.drop(columns=[
        'EXTRA1','EXTRA2','EXTRA3','EXTRA4','EXTRA5',
        'EXTRA6','EXTRA7','EXTRA8','EXTRA9','EXTRA10'
    ], errors='ignore')

#La columna AV/P tiene datos mezclados, entre tipo texto y numeros, así que primero la pasamos a object
#después eliminamos las B que hay y en caso que haya valores NAN (vacios pero que se escriben NAN por la función
#de limpieza de texto) se cambian por el valor 99999999
    df['AV/P'] = df['AV/P'].astype(str)
    #para la columna AV/P se tiene que si la variable es vacia, debemos cambiarla por 99999999, y retirar las B
    df['AV/P'] = df['AV/P'].replace('NAN', '99999999')
    df['AV/P'] = df['AV/P'].str.replace('B', '', regex=True)

#Ahora sí, cambiamos todos los valores NAN sobrantes de los datos a 
    df = df.replace('NAN', '')
    
    columnas_a_numerico = ["IMPORTE CON IVA",'IVA','IMPORTE SIN IVA']
    for col in columnas_a_numerico:
        df[col] = pd.to_numeric(df[col], errors='coerce').round(2) #redondeado a dos decimales que son como vienen los datos originales

#Columnas que son de tipo int, únicamente por si se ncesitase
    columnas_int = [
        'CLAVE AREA','ASIENTO','SESION','AV/P',
        'TRANSACCION','OPERACION','CORRIDA',
        'NUMERO DE REFERENCIA','CLAVE DE AUTORIZACION','VOUCHER'
    ]

    for col in columnas_int:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

#Quitamos las columnas extras que estamos cargando que no son de necesidad, ¿Por qué hasta ahora si no son de necesidad?
#por si en algún momento con el movimiento columnar algún dato interesante cabia aquí dentro y ya acomodado donde se
#esperaría, pues ya se pueden quitar
    df = df.drop(columns=['RAZON SOCIAL', 'R.F.C.','DOCUMENTO ', ' EMPRESA', ' FACTURA', 'F. FACTURA', 
                        'FORMATO/SALTO'])
    
#cambiamos cada variable de fecha que tenemos a la fecha del día actual, esta se extrae automático dentro del ciclo de apertura

    df['CORRIDA'] = df['CORRIDA'].replace("******", '')
    print(f"Datos en Empresa Corrida para el {tipo, fecha}")
    print(df['EMPRESA CORRIDA'].unique())

    df['EMPRESA CORRIDA'] = df['EMPRESA CORRIDA'].replace('OMNIBUS DE MEXICO SA CV','OMNIBUS DE MEXICO S. A. DE C. V.')
    df['EMPRESA CORRIDA'] = df['EMPRESA CORRIDA'].replace('OVNIBUS S.A. DE C.V.','OMNIBUS DE MEXICO S. A. DE C. V.')
#columnas que deben ser pasadas a numérico para poder realizar las sumas de cantidades de manera efectiva
    
    print(f"\nDatos en Empresa Corrida para el {tipo, fecha} ya modificada")
    print(df['EMPRESA CORRIDA'].unique())

    #quitamos la primera fila del archivo ya que no sirve
    df = df.iloc[1:]

    ###########################
    df = df[(df['ORIGEN'] == 'FSOL') | (df['DESTINO'] == 'FSOL')]
    ###########################
    
#returneamos el df ya limpio
    return df

##########################################################################################################

#Para la limpieza de archivos históricos (Cuando son más de un archivo a la vez, que también podría usarse
#perfectamente para sólo de uno, es decir, el de limpiezaDiarios se puede usar también en esto, son similares)

#agarramos la carpeta de los datos sucios, en este caso se encuentra en la carpeta donde se descargan los datos
#la cual pues es la carpeta SICOM (tener en cuenta que en caso de hacer uso de streamlit pues la carpeta cambiaría)
#dónde vamos a abrir todos los archivos que empiecen con la forma 306_ pues son los archivos a limpiar en este código

#agarramos todos los archivos que engloben este patron, porque algunas veces puede haber otros archivos en esta
#misma carpeta, como el caso de juntar AFR con ZINA, nota: Podríamos bajar el patrón a sólo inicio con
#306 y que el sistema detecte automáticamente si es ZINA o AFR, al final de cuentas se limpian igual y sólo cambia
#el nombre de salida del archivo
archivos = st.file_uploader(
    "Sube los archivos 306",
    type="txt",
    accept_multiple_files=True
)

#Para cada archivo dentro de los archivos encontrados
for archivo in archivos:

    #primero obtenemos el nombre del archivo, que está pues en el path
    nombre_archivo = archivo.name

        #Extraer la parte de la fecha (ddmmaa), se encuentra después del primer _ en caso de ser
        #los históricos antiguos, en caso de ser los históricos más recientes, se encuentran a partir del 
        #segundo _ así que cuidao acá
    fecha_str = nombre_archivo.split("_")[2].split(".")[0]
    
    #convertimos la fecha obtenida a tipo datetime
    fecha_dt = datetime.strptime(fecha_str, "%d%m%Y")
    
    #Y ahora lo pasamos a formato con /, ya que se deben sustituir las columnas con este valor
    fecha = fecha_dt.strftime("%d/%m/%Y")  
    dia = fecha_dt.strftime("%d")
    #obtenemos la fecha sin slash para poder tener los datos con la fecha del archivo en formato ddmmaaaa
    fecha_sin_slash = fecha.replace("/", "")

    #obtenemos el tipo de archivo, que en este caso se refiere a la empresa de donde provienen los datos
    tipo = nombre_archivo.split("_")[1].split(".")[0]

    #mencionamos el archivo que se anda procesando y además pues lo abrimos, con las columnas extras y todo
    #como el caso de las individuales
    print("Procesando archivo:", nombre_archivo)
    df = pd.read_csv(archivo, sep=None, encoding='cp1252', engine='python', header = None, 
                     names = 
        ['Clave Area', 
        'Area de Venta', 'F. Contable', 'Sesión', 
       'Fecha de Apertura', 'Hora de Apertura', 'AV/P', 'Transacción',
       'Operación', 'Tipo', 'Origen', 'Destino', 'Fecha Salida', 'Hora Salida',
       'Folio Boleto', 'Asiento', 'Nombre Pasajero', 'Formas de Pago',
       'Importe con IVA', 'IVA', 'Importe sin IVA', 'Formato/Salto',
       'Fecha Venta', 'Hora Venta', 'Corrida', 'Empresa Corrida',
       'Tipo de Boleto', 'Numero de Referencia', 'Clave de Autorizacion',
       'Voucher', 'Tipo de Servicio', 'F. Cierre', 'Razon Social', 'R.F.C.',
       'DOCUMENTO ', ' EMPRESA', ' FACTURA', 'F. FACTURA', 'Extra1', 'Extra2', 'Extra3', 
       'Extra4', 'Extra5', 'Extra6', 'Extra7', 'Extra8', 'Extra9', 'Extra10'])

    #Lo de la limpieza diarios, checamos que en las columnas extra haya algún dato, esto indica que se recorrió
    columnas = ['Extra2', 'Extra3', 'Extra4', 'Extra5', 'Extra6', 'Extra7', 'Extra8', 'Extra9', 'Extra10']

#Vamos a separar nuestros datos en dos, si en alguna de las columnas extras existen datos por ahí perdidos
#quiere decir que se recorrió, y dividiremos las bases en 2: df_limpio, que es donde no hay nada recorrido
#hasta dónde este método encuentra, tenemos que tener en cuenta que este código busca resolver un problema 
#general, pero hay casos especiales que se tendrán que revisar manualmente, recomendado hacerlo el mismo día
#de la limpieza de cierto archivo, para que no se junte la problemática al verlo ya quincenal, o mensual
    mask = df[columnas].notna().any(axis=1)

    df_sucio = df[mask].copy()

    df_limpio = df[~mask].copy()


#Si en alguna de las columnas se encuentra algún dato vacio, quiere decir que se recorrió la base de datos
#así que la división debe ser tratada
    if df[columnas].notna().any().any():

        print(Fore.RED + f"\n\tSE ENCONTRARON VALORES RECORRIDOS para el archivo {tipo, fecha}")

        print(Style.RESET_ALL + '')

        print("Separación correcta en dos archivos, df_limpio y df_sucio")

        #Cambiamos el nombre de df_sucio a df2 y df_limpio a df1 para no escribir tanto nombre
        #Esto realmente se podría saltar si desde el inicio llamamos como df1 y df2, pero mantenemos arriba los 
        #Nombres de df_sucio y df_limpio para encontrar el lugar si sale algún error en la creación de estos
        df2 = df_sucio.reset_index(drop=True)
        df1 = df_limpio.reset_index(drop=True)

    #Mostramos el tamaño de cada df para obsrevar cuantos datos totales son y cuántos tiene cada uno para
    #hacernos a la idea de la cantidad de errores
        print(df2.shape)
        print(df1.shape)

    #Convertimos cada df a tipo object porque algunas veces por el movimiento de columnas se mezclan tipos de datos
        df2 = df2.astype(object)
        df1 = df1.astype(object)

        #VERIFICAIÓN DE LA COLUMNA NOMBRES COMPARANDO CON MÉTODO DE PAGO
        #El método de pago se encuentra a un lado de la columna Nombre Pasajero, esta columna a veces es mal ingresada
        #y se dividide en dos, lo que ocasiona los problemas de movimiento columnar, esta parte del código lo que 
        #busca es asegurarse que en la columna Formas de Pago sólo se encuentren datos que incluyan las letras
        #de los métodos de pago, en otro caso, debemos de eliminar ese dato y recorrer las demás filas a la izquierda
        #Esto soluciona algunos de los problemas
        columna = "Formas de Pago"
        col_index = df2.columns.get_loc(columna)
        mask = ~df2[columna].astype(str).str.contains("EF|TC|TD|DO|ME", na=False)

        for i in df2[mask].index:
            df2.iloc[i, col_index:-1] = df2.iloc[i, col_index+1:].values
            df2.iloc[i, -1] = None

    #Ahora que ya se recorrieron estas filas en estos casos, se concatenan ambas bases de datos, de manera vertical
    #es decir, se pegan los datos de df2 abajo de los de df1, las filas, vaya.
        df = pd.concat([df1, df2], axis=0, ignore_index=True)
        
    #Observamos ahora el tamaño de los dataframe completo ya con todo y todo modificado, esto nos permite ver
    #junto con lo de arriba, el tamaño de cada uno por separado y el tamaño final de ambos juntos
        print(df.shape)
        #de nuevo convertimos a object por cualquier cosa
        df = df.astype(object)

    #Vamos a ver que tipo de valores podemos esperar en la variable de empresa corrida de nuestro df
    #¿Por qué?, algunas veces los nombres de las empresas están cortados, el caso más común es que dice únicamente
    #ÓMNIBUS DE MÉXICO y no el nombre de razón social completo, así que esto se modifica

        nombre_correcto = "ÓMNIBUS DE MÉXICO S. A. DE C. V."
        nombre_base = "ÓMNIBUS DE MÉXICO"

    #Vemos cada valor en nuestra columna de Empresa corrida
        for i in df.index:
            for j in range(len(df.columns)):
            
                valor = str(df.iat[i, j])
            
            #Si tiene el nombre sin la razón social, eso está mal, y debemos cambiarlo
                if nombre_base in valor and nombre_correcto not in valor:
                
                #reemplazamos el nombre malo por el nombre correcto
                    df.iat[i, j] = nombre_correcto
                
                #Eliminamos el dato siguiente y volvemos a jalar las filas hacia la izquierda
                    if j < len(df.columns) - 1:
                    
                        for k in range(j + 1, len(df.columns) - 1):
                            df.iat[i, k] = df.iat[i, k + 1]
                    
                    #por último, vaciamos la última columna, que trae los caracteres rarosos
                        df.iat[i, len(df.columns) - 1] = None
                
                    break

        df = limpieza_comun(df, fecha)
        
        if tipo == 'ZINA':
    #La ruta de salida del archivo es la carpeta de BASE LIMPIA FINAL, se guarda tal cual como entró
    #pero en extensión .xlsx
    #Salida de limpieza para archivos de tipo ZINA
            ruta = fr"G:\Unidades compartidas\Reportes Limpios\306\ZIN\306_ZINA_{fecha_sin_slash}.xlsx" 
            
            df.to_excel(ruta, index=False)

            print(Fore.GREEN + f"\n\tLA BASE LIMPIA SE HA CARGADO EN LA CARPETA BASE LIMPIA FINAL para el archivo {tipo, fecha}")
            print(Style.RESET_ALL + '\n')

        elif tipo == 'AFR':
                #La ruta de salida del archivo es la carpeta de BASE LIMPIA FINAL, se guarda tal cual como entró
    #pero en extensión .xlsx
            nombre_salida = archivo.name.replace(".txt", ".xlsx")

            # crear archivo en memoria
            output = BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)

            st.download_button(
                label="Descargar archivo limpio",
                data=output,
                file_name=nombre_salida,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            print(Fore.GREEN + f"\n\tLA BASE LIMPIA SE HA CARGADO EN LA CARPETA BASE LIMPIA FINAL para el archivo {tipo, fecha}")
            print(Style.RESET_ALL + '\n')
        
        else:
            print("Nombre de archivo no coincide con AFR o ZINA")

#SI NO HUBO ALGÚN VALOR RECORRIDO PARA LOS ARCHIVOS QUE SE VAN ABRIENDO, SE MODIFICAN LOS DATOS Y SE SUBEN
    else:

        #Si no hubo datos recorridos, dentro de lo que cabe uno de los problemas, se avisa al usuario
        print(Fore.GREEN + f"\n\tNO HUBO VALORES RECORRIDOS para el archivo {tipo, fecha}")

        print(Style.RESET_ALL + '')

        #nuestro df limpio sería el df original
        df = df_limpio

        df = limpieza_comun(df, fecha)
        #Si nuestro dato tiene tipo ZINA, o sea, empresa de ZINA:
        if tipo == 'ZINA':
    #La ruta de salida del archivo es la carpeta de reportes limpios para la carpeta 306, se guarda tal cual como entró
    #pero en extensión .xlsx
    #Salida de limpieza para archivos de tipo ZINA
            ruta = fr"G:\Unidades compartidas\Reportes Limpios\306\ZIN\306_ZINA_{fecha_sin_slash}.xlsx" 

            df.to_excel(ruta, index=False)

            print(Fore.GREEN + f"\n\tLA BASE LIMPIA SE HA CARGADO EN LA CARPETA BASE LIMPIA FINAL para el archivo {tipo, fecha}")
            print(Style.RESET_ALL + '\n')
            #Si el dato es de FR, no cambia nada, realmente sólo la forma en que se guarda en el path
        elif tipo == 'AFR':
                #La ruta de salida del archivo es la carpeta de 306, se guarda tal cual como entró
    #pero en extensión .xlsx
            nombre_salida = archivo.name.replace(".txt", ".xlsx")

            # crear archivo en memoria
            output = BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)

            st.download_button(
                label="Descargar archivo limpio",
                data=output,
                file_name=nombre_salida,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            print(Fore.GREEN + f"\n\tLA BASE LIMPIA SE HA CARGADO EN LA CARPETA BASE LIMPIA FINAL para el archivo {tipo, fecha}")
            print(Style.RESET_ALL + '\n')
    
    #Si ningún dato es de tipo AFR o Zina reconocido
        else:
            print(f"Nombre de archivo no coincide con AFR o ZINA {tipo, fecha}")
