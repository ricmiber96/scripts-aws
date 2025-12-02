
# Solucionario: Simulacro de Examen AWS (100% Consola Manual)

> **Introducción:** Esta guía resuelve el simulacro de examen paso a paso utilizando exclusivamente la **Consola de Administración de AWS (interfaz web)**. No se utiliza código Python ni CLI. El objetivo es comprender "qué ocurre por debajo" de los scripts de automatización.

---

## Parte 1: Creación de la VPC
*Referencia teórica: Documento `aws2_10 boto.pdf` (aplicado manualmente).*

**Objetivo:** Crear el contenedor de red principal y habilitar la resolución de nombres DNS.

1.  **Ir al panel de VPC:**
    *   En la barra de búsqueda superior, escribe **"VPC"** y entra al servicio.
2.  **Crear VPC:**
    *   Haz clic en el botón naranja **Crear VPC**.
    *   En *Configuración de VPC*, selecciona **Solo la VPC** (para evitar el asistente automático).
    *   **Etiqueta de nombre:** `Examen-VPC-Manual`
    *   **Bloque de CIDR IPv4:** `10.0.0.0/16`
    *   **Tenencia:** Predeterminado.
    *   Clic en **Crear VPC**.
3.  **Habilitar DNS (Crucial):**
    *   Selecciona tu nueva VPC en la lista.
    *   Ve al menú **Acciones** (arriba a la derecha) → **Editar configuración de VPC**.
    *   Marca la casilla **Habilitar nombres de host DNS** (*Enable DNS hostnames*).
    *   Clic en **Guardar cambios**.

---

## Parte 2: Configuración de Red (Subredes, IGW y Rutas)
*Referencia teórica: Documento `aws2_11igw.pdf` y `aws2_10 (1).pdf`.*

**Objetivo:** Crear las subredes y conectar la VPC a internet.

### 2.1. Crear Subredes
1.  En el menú izquierdo, clic en **Subredes** → **Crear subred**.
2.  **ID de la VPC:** Selecciona `Examen-VPC-Manual`.
3.  **Configuración de Subred 1 (Pública):**
    *   **Nombre:** `Subred-Publica`
    *   **Zona de disponibilidad:** `us-east-1a` (o la primera disponible).
    *   **Bloque de CIDR IPv4:** `10.0.1.0/24`
    *   *Clic en el botón **Agregar nueva subred** para crear la segunda sin salir.*
4.  **Configuración de Subred 2 (App/Privada):**
    *   **Nombre:** `Subred-App`
    *   **Zona de disponibilidad:** `us-east-1a` (Recomendado: misma zona que la pública).
    *   **Bloque de CIDR IPv4:** `10.0.2.0/24`
5.  Clic en **Crear subred**.

### 2.2. Crear y Adjuntar Internet Gateway (IGW)
1.  Menú izquierdo, **Gateways de Internet** → **Crear gateway de internet**.
2.  **Nombre:** `Examen-IGW`.
3.  Clic en **Crear gateway de internet**.
4.  El estado será *Detached*. Clic en **Acciones** → **Asociar a la VPC**.
5.  Selecciona `Examen-VPC-Manual` y confirma.

### 2.3. Configurar Tablas de Enrutamiento
Ve al menú izquierdo, **Tablas de enrutamiento**.

#### A. Tabla Pública
1.  Clic en **Crear tabla de enrutamiento**.
    *   **Nombre:** `RT-Publica`
    *   **VPC:** `Examen-VPC-Manual`
    *   Clic en **Crear**.
2.  **Agregar la Ruta de Salida:**
    *   Ve a la pestaña **Rutas** → **Editar rutas** → **Agregar ruta**.
    *   **Destino:** `0.0.0.0/0`
    *   **Objetivo:** Selecciona *Gateway de Internet* y elige `Examen-IGW`.
    *   Clic en **Guardar cambios**.
3.  **Asociación de Subred:**
    *   Ve a la pestaña **Asociaciones de subredes** → **Editar asociaciones**.
    *   Selecciona la `Subred-Publica`.
    *   Clic en **Guardar asociaciones**.

#### B. Tabla Privada
1.  Busca la tabla creada por defecto con la VPC (columna "Principal" = Sí). Renómbrala a `RT-Privada`.
2.  **Verificar Rutas:** Asegúrate de que **NO** tenga salida al IGW (solo debe tener la ruta local `10.0.0.0/16`).
3.  **Asociación:** En *Asociaciones de subredes*, edita y asocia la `Subred-App`.

---

## Parte 3: Seguridad y Bastionado (Reglas Encadenadas)
*Referencia teórica: Documento `aws2_13reglas_enca.pdf`.*

**Objetivo:** La App solo debe aceptar tráfico proveniente del Bastión.

### 3.1. Grupos de Seguridad (Security Groups)
Ve a **EC2** → Menú izquierdo **Grupos de seguridad**.

**A. Crear SG del Bastión:**
1.  **Crear grupo de seguridad**.
2.  **Nombre:** `GS-Bastion`.
3.  **VPC:** `Examen-VPC-Manual`.
4.  **Reglas de entrada:**
    *   Tipo: `SSH` | Origen: `Cualquier lugar (0.0.0.0/0)`.
5.  Clic en **Crear**.

**B. Crear SG de la App (Regla Encadenada):**
1.  **Crear grupo de seguridad**.
2.  **Nombre:** `GS-App`.
3.  **VPC:** `Examen-VPC-Manual`.
4.  **Reglas de entrada:**
    *   **Regla 1:** Tipo `SSH`. En Origen, selecciona el grupo `GS-Bastion`.
    *   **Regla 2:** Tipo `ICMP personalizado IPv4` (Ping). En Origen, selecciona `GS-Bastion`.
5.  Clic en **Crear**.

### 3.2. Lanzar Instancias EC2
Ve a **Instancias** → **Lanzar instancias**.

**A. Bastión:**
*   **Nombre:** `Bastion-Host`
*   **Imagen:** Ubuntu
*   **Tipo:** t2.micro
*   **Par de claves:** Tu clave `.pem` (ej. vockey).
*   **Configuraciones de red:**
    *   **VPC:** `Examen-VPC-Manual`
    *   **Subred:** `Subred-Publica`
    *   **Asignar IP pública:** Habilitar.
    *   **Grupo de seguridad:** Seleccionar existente → `GS-Bastion`.
*   Clic en **Lanzar**.

**B. App Server:**
*   **Nombre:** `App-Server`
*   **Imagen:** Ubuntu
*   **Configuraciones de red:**
    *   **VPC:** `Examen-VPC-Manual`
    *   **Subred:** `Subred-App`
    *   **Asignar IP pública:** Deshabilitar.
    *   **Grupo de seguridad:** Seleccionar existente → `GS-App`.
*   Clic en **Lanzar**.

### 3.3. Verificación de Conexión (Terminal local)
Anota la **IP Pública del Bastión** y la **IP Privada de la App**.

1.  Carga tu clave en el agente:
    ```bash
    ssh-add vockey.pem
    ```
2.  Conecta con reenvío de agente (Agent Forwarding):
    ```bash
    ssh -A -i vockey.pem ubuntu@IP_PUBLICA_BASTION
    ```
3.  Salta a la App desde el Bastión:
    ```bash
    ssh ubuntu@IP_PRIVADA_APP
    ```
    *(Si conecta, la Parte 3 es un éxito).*

---
## Parte 4: Implementación de NAT Gateway para Salida Privada
*Referencia teórica:* El **NAT Gateway** es un servicio administrado que permite que las instancias en subredes privadas se conecten a internet (para actualizaciones, parches, etc.) o a otros servicios de AWS, pero impide que internet inicie una conexión con esas instancias. Requiere una IP Elástica y **debe residir en una subred pública**.

**Objetivo:** Dar salida a internet al App-Server sin hacerlo público (sin asignarle IP pública ni exponer puertos).

### 4.1. Crear IP Elástica (EIP)
1.  Ve al menú izquierdo de **VPC** → **IP Elásticas**.
2.  Clic en **Asignar dirección IP elástica**.
3.  Clic en **Asignar**.
    *   *Esto reserva una dirección IP estática pública que será utilizada exclusivamente por el NAT Gateway.*

### 4.2. Crear NAT Gateway (NGW)
1.  Ve al menú izquierdo de **VPC** → **Gateways NAT**.
2.  Clic en **Crear gateway NAT**.
3.  **Configuración:**
    *   **Nombre:** `Examen-NAT-GW`.
    *   **Subred:** Selecciona la `Subred-Publica` (10.0.1.0/24).
        *   *Nota: Es obligatorio que el NGW esté en la subred pública para poder enrutar el tráfico hacia el Internet Gateway.*
    *   **Asignación de IP elástica:** Selecciona la EIP que acabas de crear en el paso 4.1.
4.  Clic en **Crear gateway NAT**.
    *   *Espera unos instantes hasta que el estado cambie de **Pending** a **Available**.*

### 4.3. Modificar Tabla de Rutas de la Subred Privada (RT-Privada)
1.  Ve al menú izquierdo de **VPC** → **Tablas de enrutamiento**.
2.  Selecciona la tabla de rutas asociada a la Subred-App (asegúrate de que sea la `RT-Privada` configurada anteriormente).
3.  Ve a la pestaña **Rutas** → **Editar rutas**.
4.  **Agregar ruta:**
    *   **Destino:** `0.0.0.0/0` (Todo el tráfico saliente hacia internet).
    *   **Objetivo:** Selecciona **Gateway NAT** y elige tu `Examen-NAT-GW`.
5.  Clic en **Guardar cambios**.

### 4.4. Verificación de Salida
1.  Vuelve a tu terminal local.
2.  Si no estás conectado, entra al Bastión y salta al App-Server:
    ```bash
    ssh -A -i vockey.pem ubuntu@IP_PUBLICA_BASTION
    ssh ubuntu@IP_PRIVADA_APP
    ```
3.  **Prueba de Salida de Internet:** Ejecuta un ping a Google:
    ```bash
    ping 8.8.8.8
    ```
    *   **Resultado esperado:** El ping ahora debe responder correctamente. Esto demuestra que el servidor privado puede *salir* a buscar información a internet a través del NAT Gateway, aunque nadie pueda entrar directamente a él.


## Parte 4: Implementación de NAT Gateway para Salida Privada
*Referencia teórica: El NAT Gateway es un servicio administrado que permite que las instancias en subredes privadas se conecten a internet o a otros servicios de AWS, pero impide que el internet inicie una conexión con esas instancias. Requiere una IP Elástica y debe residir en una subred pública.*

**Objetivo:** Dar salida a internet al App-Server sin hacerlo público.

### 4.1. Crear IP Elástica (EIP)
1.  **VPC** → **IP Elásticas**.
2.  Clic en **Asignar dirección IP elástica**.
3.  Clic en **Asignar**. *(Esto crea la dirección IP estática que necesita el NAT Gateway).*

### 4.2. Crear NAT Gateway (NGW)
1.  **VPC** → **Gateways NAT**.
2.  Clic en **Crear gateway NAT**.
3.  **Nombre:** `Examen-NAT-GW`.
4.  **Subred:** Selecciona la `Subred-Publica` (10.0.1.0/24). *El NGW siempre debe estar en una subred pública.*
5.  **Asignación de IP elástica:** Selecciona la EIP que acabas de crear en el paso 4.1.
6.  Clic en **Crear gateway NAT**. *(Espera a que el estado cambie a Available).*

### 4.3. Modificar Tabla de Rutas de la Subred Privada (RT-Privada)
1.  **VPC** → **Tablas de enrutamiento**.
2.  Busca la tabla de rutas asociada a la `Subred-App` (la privada) y ponle nombre `RT-Privada`.
3.  Ve a la pestaña **Rutas** → **Editar rutas**.
4.  **Agregar ruta:**
    *   **Destino:** `0.0.0.0/0`. *(Tráfico que va a internet).*
    *   **Objetivo:** Selecciona "Gateway NAT" y elige tu `Examen-NAT-GW`.
5.  Clic en **Guardar cambios**.

### 4.4. Verificación de Salida
1.  Conéctate al Bastión.
2.  Desde el Bastión, conéctate al App-Server (IP Privada).
3.  **Prueba de Salida de Internet:** Ejecuta el ping de nuevo:
    ```bash
    ping 8.8.8.8
    ```
4.  **Resultado esperado:** El ping ahora debe ser exitoso, demostrando que el App-Server tiene salida a internet a través del NAT Gateway.

---

## Parte 5: NACLs y Stateless (Prueba de Ping)
*Referencia teórica: Documento `aws2_14nacl.pdf`.*

**Objetivo:** Demostrar el comportamiento *stateless* (sin estado) de las NACLs provocando un fallo de red.

**Estado inicial:** Desde el Bastión, haz `ping IP_PRIVADA_APP`. Debería funcionar.

1.  **Crear la NACL:**
    *   Panel de VPC → **Listas de control de acceso a la red (NACL)**.
    *   **Crear lista**. Nombre: `NACL-Stateless-Test`. VPC: `Examen-VPC-Manual`.
2.  **Asociar a la Subred Privada:**
    *   Selecciona la NACL nueva → Pestaña **Asociaciones de subredes** → **Editar**.
    *   Selecciona `Subred-App` y guarda.
    *   *Nota: Ahora la App está aislada (Deny All implícito).*
3.  **Configurar Regla de ENTRADA (Inbound):**
    *   Pestaña **Reglas de entrada** → **Editar**.
    *   Agregar regla → **Nº**: `100` | **Tipo**: `Todo el tráfico ICMP` | **Origen**: `0.0.0.0/0` | **Permitir**.
    *   Guardar.
4.  **Demostración del Fallo:**
    *   Vuelve a la terminal del Bastión e intenta el `ping`. **Fallará.**
    *   *Causa:* La NACL permite entrar la solicitud (Inbound), pero como es *stateless*, no recuerda la conexión y bloquea la respuesta al no haber regla de salida explícita.
5.  **Solución (Regla de SALIDA):**
    *   Pestaña **Reglas de salida** → **Editar**.
    *   Agregar regla → **Nº**: `100` | **Tipo**: `Todo el tráfico ICMP` | **Destino**: `0.0.0.0/0` | **Permitir**.
    *   Guardar.
6.  **Resultado final:** El ping volverá a funcionar inmediatamente.