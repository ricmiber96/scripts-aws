Esta es una guía de estudio y práctica detallada, paso a paso, diseñada para resolver cada punto de tu temario. He asumido que tienes acceso a la consola de AWS y sabes moverte por los menús básicos, pero explicaré cada configuración necesaria para que funcione.

---

# 📘 Guía de Estudio y Práctica: Examen AWS RDS

---

## T1. No Relacionales vs Relacionales y Primeros Pasos

### 1. Teoría Rápida: NoSQL vs SQL
Antes de tocar la consola, ten claro esto para el examen:
*   **Relacionales (SQL):** Datos estructurados en tablas (filas y columnas). Esquema fijo. Ideal para sistemas transaccionales (ERP, CRM, Bancos). *Ejemplos AWS:* RDS (MySQL, Postgres, MariaDB, Oracle, SQL Server) y Aurora.
*   **No Relacionales (NoSQL):** Esquema flexible (JSON, Clave-Valor). Ideal para Big Data, catálogos de productos, sesiones de usuario, alta velocidad. *Ejemplos AWS:* DynamoDB (Clave-Valor), DocumentDB (Documentos).

### 2. Ejercicio Práctico: Crear RDS (Acceso Público) y Conectar

**Objetivo:** Crear una BD MySQL y conectarse desde tu PC de casa.

#### Paso A: Crear la RDS
1.  Ve a **RDS** en la consola -> **Databases** -> **Create database**.
2.  **Creation method:** Standard create.
3.  **Engine options:** MySQL.
4.  **Templates:** Selecciona **Free Tier** (Capa gratuita) para evitar cobros.
5.  **Settings:**
    *   *DB instance identifier:* `mi-rds-publica`
    *   *Master username:* `admin`
    *   *Master password:* `admin12345` (o una que recuerdes).
6.  **Instance configuration:** Deja `db.t3.micro` (o la que salga por defecto en Free Tier).
7.  **Connectivity (EL PASO MÁS IMPORTANTE):**
    *   *Compute resource:* Don't connect to an EC2 compute resource.
    *   *Public access:* **Yes** (Si marcas No, no podrás conectar desde tu casa).
    *   *VPC Security Group:* Create new. Nombre: `sg-rds-public`.
8.  **Authentication:** Password authentication.
9.  Clic en **Create database**. Tardará unos 5-10 minutos.
10. Cuando el estado sea "Available", entra en la base de datos y copia el **Endpoint** (ej. `mi-rds.cxyz.us-east-1.rds.amazonaws.com`).

#### Paso B: Conectar desde Terminal
*Requisito:* Tener instalado un cliente MySQL localmente.
1.  Abre tu terminal (PowerShell o CMD en Windows, Terminal en Mac/Linux).
2.  Ejecuta:
    ```bash
    mysql -h TU_ENDPOINT_COPIADO -P 3306 -u admin -p
    ```
3.  Introduce la contraseña cuando la pida. Si ves el prompt `mysql>`, ¡estás dentro!

#### Paso C: Conectar desde Workbench
1.  Abre **MySQL Workbench**.
2.  Clic en el símbolo **(+)** para nueva conexión.
3.  *Connection Name:* `AWS RDS Public`.
4.  *Hostname:* Pega el **Endpoint**.
5.  *Port:* 3306.
6.  *Username:* `admin`.
7.  Clic en **Test Connection**, pon la contraseña y OK.

---

## T2. Despliegue de RDS

### 1. Crear RDS con acceso desde EC2 (Privado)
*Escenario Real:* Por seguridad, las bases de datos nunca deben ser públicas. Se accede a ellas a través de una aplicación (EC2).

1.  **Lanzar EC2:**
    *   Ve a EC2 -> Launch Instance.
    *   Nombre: `Web-Server`.
    *   OS: Amazon Linux 2023.
    *   Network: En la misma VPC que usarás para la RDS.
    *   **Security Group (SG):** Crea uno nuevo (`sg-ec2`) permitiendo SSH (puerto 22).
    *   Lanza la instancia.
2.  **Crear RDS Privada:**
    *   Sigue los pasos del T1, **PERO** en **Connectivity**:
    *   *Public access:* **No**.
    *   *Security Group:* Create new (`sg-rds-privada`).
3.  **Configurar la conexión (El truco del examen):**
    *   La RDS tiene un firewall (SG) que bloquea todo. Tienes que decirle "Deja entrar tráfico solo si viene de mi EC2".
    *   Ve a la consola de RDS -> Clic en tu BD -> Clic en el enlace del **VPC Security Group** (activo).
    *   Ve a la pestaña **Inbound rules** -> **Edit inbound rules**.
    *   Add Rule -> Type: **MySQL/Aurora** (3306).
    *   Source: En la lupa, busca y selecciona el Security Group de tu EC2 (`sg-ec2`). **No pongas una IP, pon el ID del grupo de seguridad.**
    *   Save rules.
4.  **Prueba:** Conéctate por SSH a la EC2, instala el cliente (`sudo dnf install mariadb105 -y`) e intenta el comando `mysql -h ...` apuntando a la RDS. Debería conectar.

### 2. Crear RDS, Snapshot y Caché (Comparar)

**A. Hacer Snapshot (Copia de seguridad manual):**
1.  Selecciona tu RDS.
2.  Botón **Actions** -> **Take snapshot**.
3.  Nombre: `foto-antes-de-borrar`.
4.  Esperar a que termine. (Esto sirve para restaurar la BD exacta en ese momento en otra instancia nueva).

**B. Crear ElastiCache (Concepto y Creación):**
*Teoría:* RDS guarda datos en disco (lento). ElastiCache (Redis/Memcached) guarda datos en RAM (ultra rápido). Se usa para guardar resultados de consultas frecuentes y no machacar la RDS.
*   **Comparar:** RDS = Milisegundos (ms). ElastiCache = Microsegundos (µs).

*Práctica:*
1.  Busca **ElastiCache** en el buscador.
2.  **Create cluster** -> **Create Redis cluster**.
3.  *Design your own cluster* -> *Cluster Mode:* Disabled (más fácil para pruebas).
4.  Name: `mi-cache`.
5.  Node type: `cache.t2.micro` (el más barato).
6.  Subnet Group: Create new (selecciona tu VPC).
7.  Create.

### 3. Crear RDS con Aurora (Serverless vs Aprovisionado)

**Aurora** es el motor "Premium" de AWS compatible con MySQL/Postgres.

**A. Aurora Provisioned (Aprovisionado):**
*   *Concepto:* Tú eliges el tamaño del servidor (ej. r5.large). Pagas esté en uso o no.
*   *Pasos:* Create database -> Aurora (MySQL Compatible) -> En *Instance configuration* eliges una clase "Memory Optimized".

**B. Aurora Serverless v2:**
*   *Concepto:* No eliges servidor. AWS escala la CPU y RAM automáticamente según la demanda (ACUs - Aurora Capacity Units). Si nadie entra, baja al mínimo.
*   *Pasos:*
    1.  Create database -> Aurora (MySQL Compatible).
    2.  En **Instance configuration**, selecciona **Serverless v2**.
    3.  Define el rango de capacidad (Mínimo 0.5 ACU - Máximo 128 ACU).

---

## T3. Escalado de BD Relacional

### 1. Escalado Vertical (Hacer la máquina más potente)
*Situación:* La CPU de tu RDS está al 100%. Necesitas más potencia.
1.  Selecciona tu instancia RDS.
2.  Clic en **Modify**.
3.  Busca **Instance configuration**.
4.  Cambia de `db.t3.micro` a `db.t3.small` (o medium).
5.  Baja al final -> Continue.
6.  **Importante:** Selecciona **Apply immediately** (si no, esperará a la noche).
7.  Modify DB Instance. *Nota: Habrá una pequeña caída del servicio (downtime).*

### 2. Escalado Horizontal (Réplicas de Lectura)
*Situación:* Mucha gente está leyendo tu web y la BD no da abasto, pero la CPU de escritura está bien. Solución: Crear copias solo para leer.

**A. En RDS Standard:**
1.  Selecciona tu instancia (debe tener Backups automáticos activados).
2.  **Actions** -> **Create read replica**.
3.  Configura nombre (`mi-rds-replica`).
4.  Create read replica.
5.  *Resultado:* Tendrás una nueva IP (Endpoint) que solo sirve para `SELECT`.

**B. En RDS Aurora:**
1.  Selecciona el clúster.
2.  **Actions** -> **Add reader**.
3.  Aurora gestiona automáticamente el balanceo entre el Writer y los Readers.

---

## T4. Recuperación ante desastres

### 1. RDS Proxy
*Concepto:* Gestiona un "pool" de conexiones. Si hay un failover (la BD principal cae y sube la secundaria), el Proxy mantiene la conexión viva para que la aplicación no dé error.
1.  En el menú izq. de RDS -> **Proxies**.
2.  **Create proxy**.
3.  Engine: Compatible con tu BD.
4.  **Secrets Manager:** El Proxy necesita saber usuario/pass de la BD. Tienes que crear un "Secret" en AWS Secrets Manager antes y seleccionarlo aquí.
5.  Target group: Selecciona tu RDS.

### 2. Redologs (Concepto Teórico)
*   No se configuran en la consola directamente como un botón.
*   Son ficheros transaccionales. Si la BD se apaga de golpe, AWS lee los redo logs para recuperar las últimas transacciones que estaban en memoria pero no en disco. Garantizan la "Durability" (la D de ACID).

### 3. AWS Backup y otras copias

**A. Snapshot (Ya visto en T2):** Manual, estático, se guarda indefinidamente.

**B. Automated Backups:**
1.  Modify instancia.
2.  Sección **Additional configuration** -> **Backup**.
3.  *Backup retention period:* Define cuántos días guardar (ej. 7 días). AWS hace una foto diaria y guarda logs cada 5 minutos. Te permite hacer "Point-in-time recovery" (volver a las 14:35 de ayer).

**C. AWS Backup (Servicio Centralizado):**
1.  Busca el servicio **AWS Backup**.
2.  Create Backup Plan (ej. "Backup Diario").
3.  Assign resources -> Selecciona "RDS" y busca tu base de datos.
4.  *Ventaja:* Gestiona backups de RDS, EC2, DynamoDB y EFS desde un solo sitio.

### 4. Multi-AZ (Alta Disponibilidad)

**A. Multi-AZ Instance (Standard RDS):**
1.  Al crear o modificar la RDS -> **Availability & durability**.
2.  Selecciona **Create a standby instance** (Multi-AZ DB Instance).
3.  *Efecto:* Crea una BD espejo en otra zona (ej. us-east-1**b**). Si la principal (us-east-1**a**) muere, AWS redirige el DNS a la 'b' automáticamente. Es **Síncrono**.

**B. Multi-AZ Cluster:**
1.  Opción más nueva y rápida.
2.  Crea un Writer y dos Readers. Si cae el Writer, un Reader toma el control en menos de 35 segundos.

---

## T5. Mantenimiento de BDR

### 1. Ventana de Mantenimiento
AWS necesita actualizar el SO o la versión de la BD a veces.
1.  Modify instancia.
2.  Sección **Maintenance**.
3.  **Maintenance window:** Select preference.
4.  Elige día y hora (ej. Domingos a las 3:00 AM) donde menos tráfico tengas. AWS solo aplicará parches en ese hueco.

### 2. Blue/Green Deployment (Despliegue Azul/Verde)
*Objetivo:* Actualizar una BD (ej. de MySQL 5.7 a 8.0) sin miedo a romper la producción y con parada mínima.
1.  Selecciona tu BD.
2.  **Actions** -> **Create Blue/Green Deployment**.
3.  Identifier: `bg-upgrade`.
4.  Engine version: Elige la versión nueva (ej. 8.0).
5.  Create.
6.  *Qué pasa:* AWS crea un entorno "Green" (copia exacta pero con versión nueva) y lo mantiene sincronizado.
7.  Haces tus pruebas en Green. Si todo va bien -> **Switch over**. AWS cambia el tráfico de Blue a Green en segundos.

### 3. Grupos de Parámetros (Parameter Groups)
*Objetivo:* Cambiar configuraciones del motor (ej. `max_connections`, `timeout`, `character_set`). No puedes editar el archivo `my.cnf` en RDS, usas esto.
1.  Menú izq -> **Parameter groups**.
2.  **Create parameter group**.
3.  Family: ej. `mysql8.0`.
4.  Entra en el grupo creado -> **Edit parameters**.
5.  Busca `max_connections`, cambia el valor (ej. 1000) -> Save.
6.  **Asociar:** Ve a tu Base de Datos -> Modify -> **Additional configuration** -> DB parameter group -> Elige el que acabas de crear.
7.  **Reiniciar:** El cambio requiere reiniciar la RDS (Actions -> Reboot) para aplicarse.

---

### Consejos finales para el examen:
*   **Seguridad:** Si no conecta, siempre es el **Security Group**. Regla de entrada puerto 3306.
*   **Costes:** Acuérdate de borrar todas las RDS, Snapshots y ElastiCache al terminar la práctica.
*   **Multi-AZ vs Read Replica:** Multi-AZ es para **Desastres** (Standby), Read Replica es para **Rendimiento** (Escalado).