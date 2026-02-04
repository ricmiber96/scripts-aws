Aquí tienes el `README.md` perfecto para tu repositorio de estudio o para imprimirlo como hoja de ruta. Resume todo lo que hemos trabajado, organizado por temas tal y como me has pedido.

---

# 📚 Guía de Prácticas: Examen AWS RDS (NoSQL vs Relacionales)

Este documento resume la hoja de ruta de ejercicios prácticos para preparar el examen de Bases de Datos en AWS. Cubre desde la creación básica hasta estrategias avanzadas de recuperación y escalado.

**Requisitos previos:**
*   Cuenta de AWS activa.
*   Cliente MySQL instalado (Terminal) y MySQL Workbench.
*   Conocimientos básicos de navegación en la consola AWS.

---

## 📋 Resumen de Temas y Ejercicios

### T1. Introducción y Conectividad
**Conceptos clave:** Diferencia SQL vs NoSQL, Endpoints, Acceso Público, Security Groups.

| Tema | Descripción Teórica | Ejercicios Propuestos |
| :--- | :--- | :--- |
| **NoSQL vs Relacionales** | Diferencias entre esquemas fijos (RDS) y flexibles (DynamoDB). | N/A (Teórico) |
| **Creación Básica** | Configuración de una instancia MySQL en capa gratuita (Free Tier). | **1. Crear RDS Pública:** Configurar `Public Access: Yes` y crear Security Group. |
| **Conectividad** | Métodos para acceder a la BD desde fuera de la VPC de AWS. | **2. Conexión Terminal:** Usar comando `mysql -h [endpoint] -u admin -p`.<br>**3. Conexión Workbench:** Configurar conexión TCP/IP visual con credenciales. |

---

### T2. Despliegue y Arquitectura
**Conceptos clave:** Seguridad en capas (VPC), Caché en memoria (Redis), Motores Modernos (Aurora).

| Tema | Descripción Teórica | Ejercicios Propuestos |
| :--- | :--- | :--- |
| **Arquitectura Segura** | Las BD no deben ser públicas. Se accede a través de un servidor de aplicaciones (EC2). | **1. RDS Privada + EC2:** Crear RDS sin acceso público. Configurar SG para permitir tráfico 3306 **solo** desde el SG de la EC2. |
| **Rendimiento (Caché)** | Diferencia entre disco (EBS) y memoria (RAM). | **2. Snapshot vs ElastiCache:** Crear un Snapshot manual y desplegar un cluster Redis (comparar latencias teóricas: ms vs µs). |
| **Amazon Aurora** | Motor nativo de nube, compatible con MySQL/Postgres. | **3. Aurora Serverless vs Provisioned:** Crear un clúster Aurora configurando el escalado automático por ACUs (Serverless v2). |

---

### T3. Escalado de Bases de Datos
**Conceptos clave:** CPU vs Lectura, Réplicas, CloudWatch, Estrés de infraestructura.

| Tema | Descripción Teórica | Ejercicios Propuestos |
| :--- | :--- | :--- |
| **Escalado Vertical** | Aumentar la potencia de la máquina (CPU/RAM). Implica reinicio. | **1. Change Instance Type:** Modificar una `db.t3.micro` a `db.t3.small` aplicando cambios inmediatamente. |
| **Escalado Horizontal** | Dividir la carga de lectura en varias máquinas. | **2. Read Replicas (Standard):** Crear una réplica y conectar a su Endpoint exclusivo de lectura.<br>**3. Aurora Readers:** Añadir un nodo lector y entender el "Reader Endpoint" único. |
| **Monitorización** | Observabilidad y pruebas de carga. | **4. Stress Test:** Usar **AWS Cloud9** y un script Python para saturar la BD y visualizar el pico de CPU en **CloudWatch**. |

---

### T4. Recuperación ante Desastres (DR)
**Conceptos clave:** Alta Disponibilidad (Multi-AZ), RPO/RTO, Durabilidad, Proxies.

| Tema | Descripción Teórica | Ejercicios Propuestos |
| :--- | :--- | :--- |
| **Alta Disponibilidad** | Supervivencia ante la caída de un centro de datos (AZ). | **1. Habilitar Multi-AZ:** Modificar instancia a "Standby Instance" (Síncrono). Entender que el Endpoint no cambia. |
| **Backups** | Recuperación ante errores humanos o corrupción de datos. | **2. AWS Backup & Restore:** Configurar plan de backup y realizar un "Point-in-time recovery" (PITR) creando una instancia nueva. |
| **Resiliencia de Conexión** | Gestión de pool de conexiones y failover transparente. | **3. RDS Proxy:** Crear un Proxy, almacenar credenciales en **Secrets Manager** y conectar a través del Proxy Endpoint. |

---

### T5. Mantenimiento y Operaciones
**Conceptos clave:** Actualizaciones sin parada, Tuning de parámetros, Ventanas de mantenimiento.

| Tema | Descripción Teórica | Ejercicios Propuestos |
| :--- | :--- | :--- |
| **Configuración del Motor** | No hay acceso a `my.cnf`, se usan grupos lógicos. | **1. Parameter Groups:** Crear grupo custom, editar `max_connections`, asignarlo a la BD y **reiniciar** para aplicar. |
| **Mantenimiento** | Controlar cuándo ocurren los parches y actualizaciones. | **2. Maintenance Window:** Configurar día y hora específicos para parches automáticos. |
| **Actualizaciones Mayores** | Actualizar versión de motor con mínimo tiempo de inactividad. | **3. Blue/Green Deployment:** Crear entorno paralelo (Green) con nueva versión, sincronizar y hacer "Switchover". |

---

## ⚠️ Checklist de Limpieza (Fin de Prácticas)

**IMPORTANTE:** Para evitar costes inesperados en la factura de AWS, asegúrate de eliminar los recursos en este orden al finalizar:

1.  [ ] **Aurora Clusters y Despliegues Blue/Green** (Son los más costosos).
2.  [ ] **RDS Proxy** y **Nat Gateways** (si se crearon).
3.  [ ] **Instancias RDS** y **Read Replicas**.
4.  [ ] **Clusters de ElastiCache**.
5.  [ ] **Instancias EC2** y entornos **Cloud9**.
6.  [ ] **Snapshots manuales** y **Secretos** en Secrets Manager.
7.  [ ] **Elastic IPs** (si no están asociadas a nada, cobran).