# -*- coding: utf-8 -*-


import os
import shutil
import ldap3


# Abre la conexión con ldap.
server = ldap3.Server('localhost')
conn = ldap3.Connection(server, 'cn=admin,dc=nodomain', 'ragonalex', auto_bind=True)
if not conn.bind():
    print("No se ha podido conectar a LDAP")
    exit(-1)

# Búsqueda en el directorio todos los usuarios.
conn.search(search_base='ou=usuarios,dc=nodomain',
            search_filter='(objectClass=person)',
            attributes=['uid'])

# Si la búsqueda ha dado resultados se eliminan todos los usuarios encontrados.
if len(conn.response) > 0:
    for entry in conn.response:
        dn = entry['dn']
        uid = entry['attributes']['uid'][0]
        conn.delete(dn)
        shutil.rmtree(os.path.join('/var/nfs', uid), ignore_errors=True)

        

# Desconecta de LDAP.
conn.unbind()
