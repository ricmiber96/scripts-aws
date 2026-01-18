# Ejemplos de Infraestructura AWS

## Índice de Proyectos

- [🛡️ Juice Shop con AWS WAF](#juice-shop-con-aws-waf)
- [🌐 Transit Gateway Multi-Región](#transit-gateway-multi-región)

---

# Juice Shop con AWS WAF

## Descripción

Este proyecto despliega una aplicación web vulnerable (OWASP Juice Shop) en AWS con protección WAF, incluyendo balanceador de carga y alta disponibilidad.

## Arquitectura

### Componentes de Red
- **VPC**: 10.0.0.0/16
- **Subredes públicas**: 
  - Subnet-1: 10.0.1.0/24 (us-east-1a)
  - Subnet-2: 10.0.2.0/24 (us-east-1b)
- **Internet Gateway**: Acceso a internet
- **Security Group**: Puertos 22 (SSH) y 80 (HTTP) abiertos

### Capa de Computación
- **2 instancias EC2**:
  - Tipo: t2.micro
  - AMI: Amazon Linux 2023
  - Key Pair: vockey
  - Distribución: Una por zona de disponibilidad
  - Software: Docker + OWASP Juice Shop (puerto 80)

### Balanceador de Carga
- **Application Load Balancer (ALB)**:
  - Esquema: Internet-facing
  - Protocolo: HTTP (puerto 80)
  - Target Group: Instancias EC2 registradas

### Seguridad WAF
- **Web ACL Regional** con reglas:
  - **AWSManagedRulesCommonRuleSet**: Protección XSS y general
  - **AWSManagedRulesSQLiRuleSet**: Protección SQL injection
  - **Rate Limiting**: 100 requests/5min por IP

## Requisitos Previos

1. **AWS CLI configurado** con credenciales válidas
2. **Python 3.x** instalado
3. **Boto3** instalado: `pip install boto3`
4. **Key Pair 'vockey'** existente en us-east-1

## Ejecución

### Desplegar Infraestructura

```bash
cd ejemplos_examen2
python3 juice_shop_waf.py
```

**Tiempo estimado**: 5-10 minutos

### Acceder a la Aplicación

Una vez completado el despliegue, el script mostrará la URL del ALB:
```
🌐 Accede a la aplicación en: http://JuiceShop-ALB-xxxxxxxxx.us-east-1.elb.amazonaws.com
```

### Limpiar Recursos

```bash
python3 cleanup_juice_shop.py
```

## Verificación

1. **Instancias**: Verificar que ambas instancias estén ejecutándose
2. **Target Group**: Confirmar que las instancias estén "healthy"
3. **WAF**: Revisar métricas en CloudWatch
4. **Aplicación**: Acceder via URL del ALB

## Costos Estimados

- **EC2 (2 x t2.micro)**: ~$17/mes
- **ALB**: ~$22/mes
- **WAF**: ~$5/mes + requests
- **Total aproximado**: ~$44/mes

## Troubleshooting

- **Error Key Pair**: Crear 'vockey' en us-east-1 o modificar el script
- **Timeout ALB**: Esperar 2-3 minutos para que las instancias estén healthy
- **WAF no funciona**: Verificar asociación con ALB en consola AWS

---

# Transit Gateway Multi-Región

## Descripción

Este proyecto implementa una arquitectura de red escalable que conecta múltiples VPCs en dos regiones AWS (us-east-1 y us-west-2) utilizando Transit Gateway con peering inter-regional, proporcionando conectividad full-mesh entre todas las redes.

## Arquitectura

### Topología Hub-and-Spoke Regional

```
┌─────────────────┐    ┌─────────────────┐
│   US-EAST-1     │    │   US-WEST-2     │
│                 │    │                 │
│  ┌─VPC-East-1   │    │  ┌─VPC-West-1   │
│  │ 10.1.0.0/16  │    │  │192.168.0.0/16│
│  └──────┬───────│    │  └──────┬───────│
│         │       │    │         │       │
│    ┌────▼────┐  │    │    ┌────▼────┐  │
│    │TGW-East │◄─┼────┼───►│TGW-West │  │
│    │ASN:64512│  │    │    │ASN:64513│  │
│    └────▲────┘  │    │    └────▲────┘  │
│         │       │    │         │       │
│  ┌──────▼───────│    │  ┌──────▼───────│
│  │ VPC-East-2   │    │  │ VPC-West-2   │
│  │ 10.2.0.0/16  │    │  │192.224.0.0/16│
│  └──────────────│    │  └──────────────│
└─────────────────┘    └─────────────────┘
```

### Componentes de Red

#### US-EAST-1 (Virginia)
- **VPC-East-1**: 10.1.0.0/16
  - Subnet: 10.1.0.0/24
  - Instancia EC2 Ubuntu t2.micro
- **VPC-East-2**: 10.2.0.0/16
  - Subnet: 10.2.0.0/24
  - Instancia EC2 Ubuntu t2.micro
- **TGW-East**: ASN 64512

#### US-WEST-2 (Oregón)
- **VPC-West-1**: 192.168.0.0/16
  - Subnet: 192.168.1.0/24
  - Instancia EC2 Ubuntu t2.micro
- **VPC-West-2**: 192.224.0.0/16
  - Subnet: 192.224.0.0/24
  - Instancia EC2 Ubuntu t2.micro
- **TGW-West**: ASN 64513

### Enrutamiento

#### Tablas de Rutas VPC
- **Tráfico local**: Enrutado internamente
- **Internet (0.0.0.0/0)**: → Internet Gateway
- **Cross-region**:
  - East VPCs: 192.0.0.0/8 → TGW-East
  - West VPCs: 10.0.0.0/8 → TGW-West

#### Tablas de Rutas TGW
- **TGW-East**: 192.0.0.0/8 → TGW Peering
- **TGW-West**: 10.0.0.0/8 → TGW Peering

### Seguridad
- **Security Groups**: SSH (22) e ICMP habilitados
- **Conectividad**: Full-mesh entre todas las VPCs

## Requisitos Previos

1. **AWS CLI configurado** con credenciales válidas
2. **Python 3.x** y **boto3**: `pip install boto3`
3. **Permisos IAM** para EC2, Transit Gateway

## Ejecución

### Desplegar Infraestructura

```bash
cd ejemplos_examen2
python3 transit_gateway_multiregion.py
```

**Tiempo estimado**: 15-20 minutos

### Verificar Conectividad

1. **Conectar por SSH** a cualquier instancia
2. **Hacer ping** a instancias en otras VPCs:
   ```bash
   # Desde VPC-East-1 (10.1.x.x) hacia VPC-West-2
   ping 192.224.0.x
   
   # Desde VPC-West-1 hacia VPC-East-2
   ping 10.2.0.x
   ```

### Limpiar Recursos

```bash
python3 cleanup_transit_gateway.py
```

## Flujo de Tráfico (Ejemplo)

**Ping desde VPC-East-1 (10.1.0.50) → VPC-West-2 (192.224.0.50):**

1. **Instancia EC2** → Paquete sale de 10.1.0.50
2. **VPC Route Table** → 192.224.0.50 coincide con 192.0.0.0/8 → TGW-East
3. **TGW-East** → Destino 192.x → TGW Peering
4. **AWS Backbone** → Paquete cruza a us-west-2
5. **TGW-West** → 192.224.x pertenece a VPC-West-2
6. **VPC-West-2** → Entrega a instancia destino
7. **Respuesta** → Camino inverso

## Costos Estimados

- **EC2 (4 x t2.micro)**: ~$34/mes
- **Transit Gateway (2)**: ~$72/mes
- **TGW Attachments (4)**: ~$144/mes
- **TGW Peering**: ~$36/mes
- **Data Transfer**: Variable
- **Total aproximado**: ~$286/mes

## Casos de Uso

- **Arquitecturas multi-región** con alta disponibilidad
- **Conectividad híbrida** entre múltiples VPCs
- **Migración gradual** de aplicaciones entre regiones
- **Disaster Recovery** con failover automático
- **Compliance** con requisitos de residencia de datos

## Troubleshooting

- **Timeout conectividad**: Verificar Security Groups y NACLs
- **Rutas no funcionan**: Comprobar tablas de rutas TGW
- **Peering failed**: Verificar ASN diferentes en cada TGW
- **Instancias no accesibles**: Confirmar subredes públicas con IGW