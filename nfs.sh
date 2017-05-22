#!/bin/bash

# Se crean las carpetas donde se montarán las carpetas remotas.
mkdir -p /nfs/${PAM_USER}/nube
mkdir -p /nfs/compartido

# Si no está montado la nube del usuario se monta.
mount | grep /nfs/${PAM_USER}/nube > /dev/null;
if [ $? -ne 0 ];
then
    echo "Se intenta montar la nube del usuario ${PAM_USER}" > /tmp/nfs_sh.log
    
    # ¡AVISO! Aquí se puede dar que la carpeta remota no exista en el servidor
    # por lo que la orden de montar daría un error y ya no hacemos nada más.
    # En el else borramos la carpeta donde íbamos a montar la nube del usuario.
    mount 10.2.1.254:/var/nfs/${PAM_USER}/nube /nfs/${PAM_USER}/nube > /dev/null
    if [ $? -eq 0 ];
    then
	echo "Se montó correctamente la nube del usuario ${PAM_USER}" >> /tmp/nfs_sh.log
	
	mount | grep /nfs/compartido > /dev/null;
	if [ $? -ne 0 ];
	then
	    echo "Se monta la carpeta compartida" >> /tmp/nfs_sh.log
	    
	    mount 10.2.1.254:/var/nfs/compartido /nfs/compartido
	fi

	# Montamos el enlace simbólico si no existe.
	if test -L /home/${PAM_USER}/nube;
	then
	    echo "Ya existe el enlace simbólico de la nube del usuario ${PAM_USER}" >> /tmp/nfs_sh.log
	else
	    echo "Se crea el enlace simbólico de la nube del usuario ${PAM_USER}" >> /tmp/nfs_sh.log
	    ln -s /nfs/${PAM_USER}/nube /home/${PAM_USER}/nube
	fi

	# Montamos el otro enlace simbólico si no existe.
	if test -L /home/${PAM_USER}/compartido;
	then
	    echo "Ya existe el enlace simbólico de la carpeta compartida" >> /tmp/nfs_sh.log
	else
	    echo "Se crea el enlace simbólico de la carpeta compartida" >> /tmp/nfs_sh.log
	    ln -s /nfs/compartido /home/${PAM_USER}/compartido
	fi
    else
	echo "Vaya, parece que no existe una nube remota para el usuario ${PAM_USER}" >> /tmp/nfs_sh.log
	rm -rf /nfs/${PAM_USER}
    fi
fi
