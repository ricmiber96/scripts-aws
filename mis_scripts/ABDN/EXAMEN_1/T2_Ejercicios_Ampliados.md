¡Claro que sí! Vamos a diseccionar el ejercicio de **Amazon Aurora** con un nivel de detalle extremo. Este es un punto crítico porque Aurora es el servicio de base de datos "estrella" de AWS y en el examen te preguntarán mucho sobre sus diferencias con la RDS normal (Standard).

---

# 🚀 T2 (Ampliación). Despliegue de RDS con Amazon Aurora

Antes de empezar, ten en cuenta esto para tu bolsillo: **Amazon Aurora NO tiene Capa Gratuita (Free Tier)** indefinida como la RDS `t2.micro`.
*   Aurora te cobrará por hora de instancia y por almacenamiento usado.
*   **Consejo:** Crea estos recursos, haz la práctica y **bórralos inmediatamente** al terminar (máximo 1-2 horas de uso te costarán céntimos, pero si los dejas días, será caro).

---

## Escenario A: Aurora Provisioned (Aprovisionado)

**¿Qué es?**
Imagina que alquilas un coche (servidor). Tú eliges el modelo (ej. `db.t3.medium`). Pagas por el coche las 24 horas, lo uses o no. Si el coche se queda pequeño, tienes que bajar, ir a la agencia y alquilar uno más grande (escalado manual).

### Paso a Paso Detallado:

1.  **Iniciar creación:**
    *   Ve a **RDS** -> **Create database**.
    *   **Creation method:** Standard create.

2.  **Engine options (El Motor):**
    *   Selecciona: **Aurora (MySQL Compatible)**.
    *   *Nota:* Verás que pone "Amazon Aurora" y "MySQL". No elijas "MySQL" a secas (eso es RDS Standard).
    *   **Available versions:** Elige la recomendada (normalmente la última estable, ej. 8.0.xx).

3.  **Templates (Plantilla):**
    *   Selecciona: **Dev/Test**.
    *   *¿Por qué?* "Production" activa por defecto el Multi-AZ (replicación en otra zona) y máquinas muy caras. "Dev/Test" nos permite elegir máquinas más baratas.

4.  **Settings (Configuración Básica):**
    *   **DB cluster identifier:** `aurora-cluster-provisionado`. (Aurora siempre crea un "Cluster" o grupo, aunque solo tenga una máquina).
    *   **Master username:** `admin`.
    *   **Master password:** `Admin12345` (o la que uses siempre).

5.  **Cluster storage configuration:**
    *   Selecciona: **Aurora Standard**. (Aurora I/O Optimized es más caro y es para uso intensivo).

6.  **Instance configuration (¡Punto Clave!):**
    *   Aquí es donde decides que sea "Provisioned" (Fijo).
    *   Selecciona **Burstable classes (includes t classes)**.
    *   En el desplegable, busca: **db.t3.medium**.
    *   *Explicación:* Esta es la instancia más pequeña y barata que soporta Aurora MySQL. Tiene 2 vCPU y 4GB de RAM.

7.  **Availability & durability:**
    *   **Multi-AZ deployment:** Selecciona **Don't create an Aurora Replica**.
    *   *Importante:* En producción pondrías "Create", pero para este ejercicio queremos ahorrar y no necesitamos alta disponibilidad real.

8.  **Connectivity:**
    *   **Compute resource:** Don’t connect to an EC2 compute resource.
    *   **VPC:** Default VPC.
    *   **Public access:**
        *   Si quieres conectar desde tu casa (Workbench): **Yes**.
        *   Si quieres conectar desde Cloud9/EC2 (como en el ejercicio anterior): **No**.
        *   *Recomendación:* Ponle **Yes** para verificar rápido la conexión y ciérralo luego.
    *   **VPC Security Group:** Create new -> `sg-aurora-test`. (Asegúrate que permita puerto 3306).

9.  **Create database.**

### ¿Qué acabas de crear? (Lo que verás en la consola)
Cuando termine, verás una estructura jerárquica:
*   📦 **aurora-cluster-provisionado** (Este es el Clúster, el "contenedor").
    *   📄 **aurora-cluster-provisionado-instance-1** (Esta es la instancia `db.t3.medium` **Writer**).

**Para conectar:**
Debes usar el **Endpoint** del Clúster (Writer). En la pestaña *Connectivity*, verás que dice "Writer instance" y te da una URL larga. Esa es la que pones en Workbench.

---

## Escenario B: Aurora Serverless v2

**¿Qué es?**
Imagina un coche mágico que se agranda y encoge. Si vas solo, es un Smart. Si suben 4 amigos, se convierte en un SUV en milisegundos.
**Tú no eliges la CPU/RAM**. Tú eliges un rango (Mínimo y Máximo). AWS ajusta la potencia segundo a segundo.

### Paso a Paso Detallado:

1.  **Iniciar creación:**
    *   **RDS** -> **Create database**.
    *   **Engine:** **Aurora (MySQL Compatible)**.

2.  **Templates:**
    *   Selecciona: **Dev/Test**.

3.  **Settings:**
    *   **DB cluster identifier:** `aurora-cluster-serverless`.
    *   **Credentials:** `admin` / `Admin12345`.

4.  **Instance configuration (El corazón del Serverless):**
    *   Aquí cambia todo respecto al ejercicio anterior.
    *   Debes marcar la casilla: **Serverless v2**.
    *   Verás que las opciones de "db.t3.medium", etc., desaparecen o se bloquean (dependiendo de la versión de consola, a veces te deja elegir una instancia base, pero lo importante es la casilla Serverless).

5.  **Capacity settings (Configuración de Capacidad):**
    *   Esto es lo que preguntan en el examen. La capacidad se mide en **ACUs** (Aurora Capacity Units).
    *   1 ACU ≈ 2 GB de RAM y su CPU correspondiente.
    *   **Minimum capacity:** Pon **0.5 ACU** (1 GB RAM).
        *   *¿Por qué?* Si nadie usa la base de datos, bajará a este tamaño para cobrarte lo mínimo.
    *   **Maximum capacity:** Pon **1 ACU** (2 GB RAM).
        *   *¿Por qué?* En un entorno real pondrías 64 o 128. Pero para este ejercicio, ponemos el tope en 1 para que, si tu script de estrés se vuelve loco, **AWS no te escale la máquina a un monstruo de 100€/hora**. Es tu límite de seguridad de costes.

6.  **Connectivity:**
    *   Igual que antes. Public Access: **Yes** (para probar rápido) o No (para EC2).
    *   **VPC Security Group:** Puedes reutilizar el `sg-aurora-test` que creaste en el escenario A.

7.  **Create database.**

### Comparación Visual en la Consola
Una vez creada, ve a la lista de "Databases".
1.  Mira la columna **Size** (Tamaño).
    *   En el **Escenario A**, dirá claramente `db.t3.medium`.
    *   En el **Escenario B**, dirá `Serverless`.
2.  **Prueba de concepto (Mental):**
    *   Si lanzas el script de estrés (del T3) contra la **Provisioned**, la CPU subirá al 100% y la base de datos se saturará.
    *   Si lanzas el script contra la **Serverless**, verás en las gráficas que la línea de "Capacity (ACUs)" sube automáticamente para absorber el tráfico.

---

## 🧹 Cómo borrar Aurora correctamente (¡PELIGRO!)

Borrar Aurora tiene truco. Si lo haces mal, el clúster se queda "vacío" pero existiendo, y te cobran por el almacenamiento.

**Pasos de limpieza obligatorios:**

1.  **Selecciona la Instancia:**
    *   En la jerarquía, despliega el clúster.
    *   Selecciona la **Instancia** (el nodo, ej. `instance-1`), **NO** el Clúster (la caja superior).
    *   **Actions** -> **Delete**.
    *   Te pedirá confirmación. Escribe `delete me`.
    *   *Nota:* Si tienes varias instancias (Reader/Writer), bórralas todas una a una.

2.  **Esperar:**
    *   Espera a que la instancia desaparezca.

3.  **Borrar el Clúster:**
    *   Ahora selecciona la caja superior (**Cluster** identifier).
    *   Verás que ahora está vacío (0 instancias).
    *   **Actions** -> **Delete**.
    *   **Skip final snapshot:** Marca esta casilla (SÍ, sáltatelo). Si no, te intentará cobrar por guardar la foto final.
    *   Confirmar borrado.

Solo cuando desaparezca todo de la lista estarás a salvo de costes.

---

### Resumen para el Examen:

| Característica | Aurora Provisioned | Aurora Serverless v2 |
| :--- | :--- | :--- |
| **Definición** | Servidor de tamaño fijo (`t3`, `r5`, etc.). | Capacidad elástica automática. |
| **Configuración** | Eliges `DB Instance Class`. | Eliges rango de `ACUs` (Min/Max). |
| **Escalado** | Manual (o lento). Requiere downtime para cambiar de `medium` a `large`. | Instantáneo (milisegundos). Sin interrupción. |
| **Uso ideal** | Cargas predecibles (ej. ERP de oficina 9am-5pm). | Cargas impredecibles (ej. venta de entradas, flash sales). |
| **Pago** | Por hora de instancia (fijo). | Por ACU-hora (variable segundo a segundo). |