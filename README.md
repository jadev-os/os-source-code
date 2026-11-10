<!-- BLOQUE DE INTRODUCCIÓN -->
<p><b>JadevOS Computers</b></p>

<p><b>JadevOS Computers 1.0 BETA 4</b> es una distribucion real basada en Debian GNU/Linux 13, con kernel Linux y GNOME como entorno de escritorio predeterminado, personalizado con el tema oscuro MacTahoe, iconos naranja, Dash to Dock inferior y panel translucido. Carbon DSK se conserva como sesion alternativa. Incluye Files, el gestor de archivos propio de dos paneles y Software Updater (disponible desde el menu; no se abre automaticamente), GNOME Terminal, Archive Manager, Firefox ESR, HyperBrowser con Google como página de inicio, Nautilus y Carbon DSK. GNOME Settings, Tweaks y Extensiones permiten personalizar la interfaz. Carbon DSK usa Openbox y Picom como gestor de ventanas y compositor, con panel, dock, lanzador, sesiones de trabajo y controles propios. El codename del sistema es kiwi. El inicio y la animación de Plymouth usan exclusivamente la marca JadevOS. La sesión Live inicia automáticamente con una cuenta temporal aleatoria jadevos-session-*; nunca crea una cuenta llamada live. Al instalar, se usa la cuenta creada en el instalador. Activa memoria comprimida zRAM para mejorar la respuesta cuando hay poca RAM, sin desactivar efectos visuales ni retirar aplicaciones. El menu de arranque es minimalista, en ingles y ofrece Start JadevOS y Boot into Safe Mode sobre fondo negro. La animacion de inicio y el instalador usan la marca JadevOS; la ISO se construye para equipos x86-64 con arranque BIOS.</p>

<br>
<!-- SECCIÓN: CONSTRUIR ISO -->
<p><b>Construir la ISO en Windows</b></p>

<p><b>Requisitos:</b> Windows con WSL 2 instalado. Una distribucion Ubuntu 24.04 en WSL. Si tu distribucion tiene otro nombre, puedes indicar JADEVOS_WSL_DISTRO antes de ejecutar el constructor. Conexion a internet y suficiente espacio libre para descargar los paquetes y generar la imagen.</p>

<p>Desde PowerShell, en la carpeta del proyecto:<br>
<code>python build.py</code></p>

<p>El constructor instala en Ubuntu WSL las herramientas de Debian Live que falten y guarda la ISO en dist\jadevos-tahoe.iso, reemplazando esa misma imagen en cada compilación. La primera compilación tarda más porque descarga Debian y las aplicaciones. No necesita NASM ni reemplaza el sistema operativo de Windows.</p>

<p>Para usar explícitamente una ruta fija en vez del nombre único:<br>
<code>python build.py --output dist\jadevos-prueba.iso</code></p>

<br>
<!-- SECCIÓN: PROBAR E INSTALAR -->
<p><b>Probar e instalar</b></p>

<p>En una maquina x86-64 compatible, prepara un disco vacio de 25 GB o mas y conexion a internet. Arranca la ISO recién generada en dist con el firmware BIOS; esta ISO de desarrollo todavia no admite UEFI.</p>

<p>La sesión predeterminada inicia GNOME automáticamente con tema oscuro MacTahoe, iconos MacTahoe naranja, apariencia GTK/libadwaita, dock inferior flotante y auto-ocultable, panel translúcido y botones de ventana a la izquierda. Carbon DSK sigue disponible como sesión alternativa en SDDM. La configuración del sistema se realiza con GNOME Settings y GNOME Tweaks. Incluye Files, Software Updater, GNOME Terminal, Firefox ESR, cámara (Cheese) y el reproductor Parole. El gestor permite copiar, mover, renombrar y enviar elementos a la papelera. La cámara necesita un dispositivo compatible y Parole reproduce archivos de música locales.</p>

<p>El fondo inicial es JadevOS Computers BETA 4. Los fondos de Wallpapers están disponibles en el selector GNOME Settings → Appearance; los fondos Debian se retiran de ese selector y de la imagen del sistema. La información de JadevOS muestra la serie del kernel Linux detectada al iniciar, por ejemplo 6.12.</p>

<p>En modo Live, SDDM abre automáticamente la sesión gráfica con una cuenta temporal de nombre aleatorio con el prefijo jadevos-session-; nunca se crea una cuenta llamada live. En el sistema instalado, inicia sesión con la cuenta creada durante la instalación.</p>

<p>Para conservar tus archivos y los cambios tras apagar el equipo, abre JadevOS Installer y usa el instalador gráfico. Elige solamente el disco vacio preparado para JadevOS; instalar o particionar un disco puede borrar sus datos.</p>

<p>El idioma inicial es inglés (Estados Unidos). Puedes cambiarlo a español desde GNOME Settings → Region & Language; selecciona Spanish y vuelve a iniciar sesión para aplicar el idioma. La distribución de teclado inicial es US y también puede cambiarse desde GNOME Settings → Keyboard.</p>

<p>La sesion Live sirve para probar el escritorio, pero sus cambios no persisten al apagar. Su cuenta temporal recibe un nombre aleatorio y usa la contraseña live para las tareas administrativas. Esto no afecta a la cuenta creada en la instalación. El instalador solicita autorizacion grafica antes de abrirse; escribe la contraseña temporal live cuando aparezca el dialogo de permisos.</p>

<br>
<!-- SECCIÓN: UPDATER -->
<p><b>JadevOS Updater</b></p>

<p>La ISO incluye Software Updater, una aplicación de escritorio en inglés que consulta las versiones publicadas en jamillansantiago/updates, descarga bundles OTA firmados y solicita autenticación de administrador con PolicyKit antes de instalar paquetes. El actualizador verifica la firma Ed25519 tanto antes de ofrecer el bundle como desde el instalador privilegiado. Las instalaciones no descargan dependencias adicionales ni eliminan paquetes. Software Updater se abre solo cuando el usuario lo inicia; no se ejecuta al iniciar la sesion. El repositorio de actualizaciones debe publicar el bundle .tar.gz y su firma .sig siguiendo la guía del actualizador. Hasta que se publiquen releases firmados, la aplicación indicará claramente que no hay actualizaciones disponibles; la ISO incluye el cliente, no una actualización OTA ficticia.</p>

<br>
<!-- SECCIÓN: TAHOE -->
<p><b>Tema Tahoe</b></p>

<p>La apariencia de GNOME toma como referencia el video Tahoe y usa MacTahoe GTK Theme e Icon Theme de vinceliuice, con una variante oscura naranja, el tema GTK para libadwaita, User Themes, Dash to Dock y Blur my Shell. El constructor fija las revisiones de ambos temas y verifica sus sumas SHA-256 antes de incorporarlos. Las fuentes y sus licencias se incluyen en /usr/share/doc/jadevos/mactahoe dentro del sistema.</p>

<br>
<!-- SECCIÓN: ALCANCE -->
<p><b>Alcance actual</b></p>

<p>Es una primera distribucion de desarrollo, basada en software del proyecto Debian; no es un kernel desarrollado desde cero. Esta preparada para equipos x86-64 con BIOS y todavia no se ha validado en equipos fisicos. La ISO aun no arranca con UEFI y no incluye Secure Boot ni soporte garantizado para todo el hardware. La conexion a internet depende de la red disponible en el equipo.</p>

<p>Los archivos jadevos.py, boot.asm y kernel.asm son prototipos educativos anteriores. build_bios.py conserva el generador de aquellas imagenes de demostracion; no crea el sistema completo. Usa python build.py para generar la ISO real de JadevOS.</p>
