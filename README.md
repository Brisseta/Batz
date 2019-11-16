# Projet SmartHome


Sécurisation d'une maison en cas d’incidents et alerting proactif vers liste de diffusion.

Installation physique de capteur de température et interfaçage avec bus I2C
Intégration de réseau de capteur possible 
*Testé avec le LTE Wingle HUAWEI E8372* à travers l'api **Huawei modem** 
https://pypi.org/project/huawei-modem-api-client/


# Prérequis

 1. **python version 3.6** [https://www.python.org/downloads/release/python-360/](https://www.python.org/downloads/release/python-360/)
 2. **un wingle lte compatible avec la lib** https://pypi.org/project/huawei-modem-api-client/
 3. **Une carte raspberry 3 avec OS  Raspbian**
 4. **GIT** [https://git-scm.com/downloads](https://git-scm.com/downloads)
# Fichiers

  **ressources.json** : permet de personaliser les messages , les seuils d'alerte, le nom des commandes
 **db.sqlite3** tout simplement la base de donnée associée
 vous pouvez visualiser les données et les modifier avec [https://sqlitebrowser.org/](https://sqlitebrowser.org/)
# Install
suivre ces étapes pour installer le programme sur votre carte raspberry
## Windows

 1. Installer un client ssh exemple [Putty ](https://putty.org/)
 2. Vérifier que le ssh est activé sur votre raspberry et que votre Host (PC) peut communiquer avec votre target (carte raspberry) :
    //sur la carte  (pour un réseau de classe C)
    

> **ifconfig eth0 192.168.X.100 netmask 255.255.255.0 up**

    //sur le pc
    dans votre explorer.exe
    Panneau de configuration\Réseau et Internet\Centre Réseau et partage
 Sur votre interface ethernet -> propriété![propriétés de votre interface](https://picasaweb.google.com/109379677041927261060/6759872889985582785#6759872890009520434 "title")
    Vérifier ensuite que vous êtes sur le même sous réseau![Vérification des paramètres réseaux](https://picasaweb.google.com/109379677041927261060/6759873704115765505#6759873707980467970 "title2")
 3. Récupérer le code
	
	//ouvrir un cmd.exe
	mkdir MyProj
	cd MyProj
    git clone https://github.com/Brisseta/SmartHome.git
    cd Batz

 4. Installer les dépendances
  `pip install -r requirements.txt`

## UML diagram
//TODO
