# -*- coding: utf-8 -*-

# Este script crea ficheros ldif a partir de un fichero cvs con la información
# del alumnado para:
# - Añadir usuarios al directorio dentro del organizationalUnit "usuarios".
# - Añadir a estos usuarios al commonName (cn) "alugrp" del organizationalUnit
#   (ou) "grupos".
#
# Necesita que se le pase a través de la línea de comandos los siguinetes
# parámetros:
# - La ruta del fichero CSV.
# - El siguiente uidNumber libre en el directorio (el gidNumber será el mismo).
#
# En el fichero CSV se necesitan los siguientes campos (no importan mayúsculas
# y minúsculas):
# - login o username.
# - password.
# - nombre o firstname.
# - apellidos o lastname.
#
# El delimitador por defecto del fichero CSV es el espacio aunque se puede
# indicar otro carácter por la línea de comandos.
#
# Por último, el script crea las carpetas remotas par los usuarios ldif en el
# directorio indicado en la línea de comandos con los permisos apropiados.


import argparse
import csv
import os
import ldap3


def get_username(row):
    if 'Login' in row:
        return row['Login']
    elif 'login' in row:
        return row['login']
    elif 'Nombre' in row:
        return row['Nombre']
    elif 'nombre' in row:
        return row['nombre']
    else:
        return None


def get_password(row):
    if 'Password' in row:
        return row['Password']
    elif 'password' in row:
        return row['password']
    else:
        return None


def get_first_name(row):
    if 'Firstname' in row:
        return row['Firstname'].title()
    elif 'firstname' in row:
        return row['firstname'].title()
    elif 'Nombre' in row:
        return row['Nombre'].title()
    elif 'nombre' in row:
        return row['nombre'].title()
    else:
        return None


def get_last_name(row):
    if 'Lastname' in row:
        return row['Lastname'].title()
    elif 'lastname' in row:
        return row['lastname'].title()
    elif 'Apellidos' in row:
        return row['Apellidos'].title()
    elif 'apellidos' in row:
        return row['apellidos'].title()
    else:
        return None


parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", required=True, help="fichero CVS con los datos del alumnado")
parser.add_argument("-u", "--uidNumber", required=True, type=int, help="el siguiente uidNumber libre en el directorio LDAP para el organizationalUnit usuarios")
parser.add_argument("-d", "--directory", required=True, help="el directorio donde se van a crear las carpetas remotas de los usuarios (su nube)")
parser.add_argument("-c", "--char-delimiter", help="el delimitador utilizado en el fichero CSV (por defecto se usa el espacio")
args = parser.parse_args()

fname = args.file
next_uid = args.uidNumber
directory = args.directory
char_delimiter = ' '
if args.char_delimiter:
    char_delimiter = args.char_delimiter

faluldif = "alu.ldif"
faddaluldif = "add_alu_grpalu.ldif"

with open(fname) as f, open(faluldif, 'w') as fd1, open(faddaluldif, 'w') as fd2:
    # Abre la conexión con ldap.
    server = ldap3.Server('localhost')
    conn = ldap3.Connection(server, 'cn=admin,dc=nodomain', 'ragonalex', auto_bind=True)
    if not conn.bind():
        print("No se ha podido conectar a LDAP")
        exit(-1)

    # Abre el fichero CSV de entrada y lo recorre añadiendo cada alumno/a al directorio.
    # Además, se añade cada uno de estos usuarios al grupo alugrp.
    input_file = csv.DictReader(f, delimiter=char_delimiter)
    for row in input_file:
        username = get_username(row)
        password = get_password(row)
        first_name = get_first_name(row)
        last_name = get_last_name(row)        

        if username and password and first_name and last_name:
            # Realiza la búsqueda en el directorio para comprobar si existe ya un usuario con
            # el uid o el uidNumber. Si ya existe se avisa con un mensaje por pantalla y no se
            # añade el usuario al directorio. En caso contrario se añade el usuario al directorio.
            #
            # Por ejemplo, imagina que uid es igual a al036001 y uidNumber es 5002, la búsqueda
            # que se hace en el directorio es la siguiente:
            #
            # ldapsearch -x -h localhost -b "ou=usuarios,dc=nodomain" "(|(uid=al036001)(uidNumber=4))"
            conn.search(search_base='ou=usuarios,dc=nodomain',
                        search_filter='(|(uidNumber={0})(uid={1}))'.format(next_uid, username),
                        attributes=['uid', 'uidNumber'],
                        paged_size=5)

            # Si ya existe un usuario con ese uid y/o uidNumber mostramos mensajes y seguimos con el
            # siguiente.
            if len(conn.response) > 0:
                msg = ""
                is_and = False
                for entry in conn.response:
                    if str(next_uid) in entry['attributes']['uidNumber']:
                        if username in entry['attributes']['uid']:
                            msgAux = "Ya existe un usuario con el uid {0} y el nombre de usuario {1}".format(next_uid, username)
                            msg += " / {0}".format(msgAux) if msg else msgAux
                        else:
                            msgAux = "Ya existe un usuario con el uid {0}".format(next_uid)
                            msg += " / {0}".format(msgAux) if msg else msgAux
                    elif username in entry['attributes']['uid']:
                        if str(next_uid) in entry['attributes']['uidNumber']:
                            msgAux = "Ya existe un usuario el uid {0} y el nombre de usuario {1}".format(next_uid, username)
                            msg += " / {0}".format(msgAux) if msg else msgAux
                        else:
                            msgAux = "Ya existe un usuario con el nombre de usuario {0}".format(username)
                            msg += " / {0}".format(msgAux) if msg else msgAux
                print(msg)

            # Si no existe el usuario lo introducimos en el directorio.
            else:
                # La nube para el usuario ldap que se creará a través del ldif.
                os.makedirs(os.path.join(directory, username + '/nube'), exist_ok=True)
                os.chown(os.path.join(directory, username), next_uid, next_uid)
                os.chown(os.path.join(directory, username + '/nube'), next_uid, next_uid)
                
                # Se añade al usuario al directorio LDAP.
                conn.add('uid={0},ou=usuarios,dc=nodomain'.format(username),
                         ['person', 'posixAccount'],
                         {'uid': username,
                          'cn': first_name,
                          'sn': last_name,
                          'uidNumber': next_uid,
                          'gidNumber': next_uid,
                          'userPassword': password,
                          'loginShell': '/bin/bash',
                          'homeDirectory': '/home/{0}'.format(username)})

                # Se escribe la entrada en el fichero ldif.
                fd1.write("dn: uid={0},ou=usuarios,dc=nodomain\n".format(username))
                fd1.write("objectClass: person\n")
                fd1.write("objectClass: posixAccount\n")
                fd1.write("uid: {0}\n".format(username))
                fd1.write("cn: {0}\n".format(first_name))
                fd1.write("sn: {0}\n".format(last_name))
                fd1.write("uidNumber: {0}\n".format(next_uid))
                fd1.write("gidNumber: {0}\n".format(next_uid))
                fd1.write("userPassword: {0}\n".format(password))
                fd1.write("loginShell: /bin/bash\n")
                fd1.write("homeDirectory: /home/{0}\n\n".format(username))
                
                # Se modifica el usuario para añadirlo al grupo alugrp.
                conn.modify('cn=alugrp,ou=grupos,dc=nodomain',
                            {'memberuid': [(ldap3.MODIFY_ADD, [username])]})

                # Se escribe en el fichero ldif.
                fd2.write("dn: cn=alugrp,ou=grupos,dc=nodomain\n")
                fd2.write("changetype: modify\n")
                fd2.write("add: memberuid\n")
                fd2.write("memberuid: {0}\n\n".format(username))
                
                next_uid = next_uid + 1

        else:
            print("Faltan valores: ", row)


    # Desconecta de LDAP.
    conn.unbind()
