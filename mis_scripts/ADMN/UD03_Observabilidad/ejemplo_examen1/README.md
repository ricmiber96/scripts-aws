# Infraestructura de Monitoreo con Prometheus

Este script crea una infraestructura de monitoreo en AWS usando Prometheus y Node Exporter.

## Componentes creados:
- VPC con CIDR 10.0.0.0/16
- Subred pública 10.0.1.0/24
- Internet Gateway y tabla de rutas
- Security Group "monitoring-sg" con puertos 22, 9090, 9100
- Security Group "grafana-sg" con puertos 22, 3000 (opcional)
- Instancia EC2 "ec2_a" con Node Exporter
- Instancia EC2 "prometheus" con servidor Prometheus
- Instancia EC2 "ec2-grafana" con Grafana (opcional)

## Requisitos previos:
1. AWS CLI configurado con credenciales
2. Key pair 'vockey' existente en AWS
3. Python 3.x instalado

## Instalación:
```bash
pip install -r requirements.txt
```

## Uso:
1. Crear infraestructura base:
```bash
python create_monitoring_infrastructure.py
```

2. Añadir Grafana (opcional):
```bash
python add_grafana.py <vpc_id> <subnet_id>
```

## Acceso:
- Prometheus UI: http://[IP_PUBLICA_PROMETHEUS]:9090
- Grafana UI: http://[IP_PUBLICA_GRAFANA]:3000 (admin/admin)
- SSH a las instancias: ssh -i vockey.pem ubuntu@[IP_PUBLICA]

## Limpieza:
```bash
python cleanup_infrastructure.py
```

## Prueba Completa Paso a Paso

### 1. Despliegue de la Infraestructura

```bash
# Crear infraestructura base
python create_monitoring_infrastructure.py

# Anotar los valores de salida:
# VPC ID: vpc-xxxxxxxxx
# Subnet ID: subnet-xxxxxxxxx
# IPs públicas de las instancias

# Añadir Grafana
python add_grafana.py vpc-xxxxxxxxx subnet-xxxxxxxxx
```

### 2. Verificación de Prometheus

#### 2.1 Acceso a Prometheus UI
1. Abrir navegador en: `http://[IP_PROMETHEUS]:9090`
2. Verificar que Prometheus esté funcionando

#### 2.2 Verificar Targets
1. Ir a **Status > Targets**
2. Verificar que aparezcan:
   - `prometheus` (localhost:9090) - Estado: UP
   - `node` ([IP_EC2_A]:9100) - Estado: UP

#### 2.3 Consultas de Ejemplo en Prometheus
```promql
# CPU usage
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk usage
100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)

# Network traffic
rate(node_network_receive_bytes_total[5m])
rate(node_network_transmit_bytes_total[5m])
```

#### 2.4 Configurar Alertas en Prometheus

##### 2.4.1 Crear archivo de reglas de alertas
```bash
# Conectar por SSH a la instancia Prometheus
ssh -i vockey.pem ubuntu@[IP_PROMETHEUS]

# Crear archivo de reglas
sudo tee /etc/prometheus/alert_rules.yml > /dev/null <<EOF
groups:
  - name: node_alerts
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 2 minutes on {{ \$labels.instance }}"

      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 85% for more than 5 minutes on {{ \$labels.instance }}"

      - alert: HighDiskUsage
        expr: 100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100) > 90
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High disk usage detected"
          description: "Disk usage is above 90% on {{ \$labels.instance }}"

      - alert: NodeDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Node is down"
          description: "Node {{ \$labels.instance }} has been down for more than 1 minute"

      - alert: HighNetworkTraffic
        expr: rate(node_network_receive_bytes_total{device!="lo"}[5m]) > 10485760  # 10MB/s
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "High network traffic detected"
          description: "Network receive traffic is above 10MB/s for more than 3 minutes on {{ \$labels.instance }}"
EOF
```

##### 2.4.2 Actualizar configuración de Prometheus
```bash
# Editar configuración de Prometheus
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  - job_name: 'node'
    static_configs:
      - targets: ['[IP_PRIVADA_EC2_A]:9100']
EOF

# Cambiar permisos
sudo chown prometheus:prometheus /etc/prometheus/alert_rules.yml

# Reiniciar Prometheus
sudo systemctl restart prometheus
```

##### 2.4.3 Verificar Alertas en Prometheus UI
1. Ir a **Alerts** en Prometheus UI
2. Verificar que las reglas aparezcan listadas
3. Estado inicial debe ser "Inactive"

##### 2.4.4 Probar Alertas
```bash
# Conectar a ec2_a para generar alertas
ssh -i vockey.pem ubuntu@[IP_EC2_A]

# Generar alta carga de CPU (activará HighCPUUsage)
stress --cpu 4 --timeout 300s &

# Generar alta carga de memoria (activará HighMemoryUsage)
stress --vm 2 --vm-bytes 1G --timeout 300s &

# Llenar disco (activará HighDiskUsage)
dd if=/dev/zero of=/tmp/largefile bs=1M count=1000
```

##### 2.4.5 Monitorear Estados de Alertas
1. En Prometheus UI > **Alerts**
2. Observar cambios de estado:
   - **Inactive** → **Pending** → **Firing**
3. Verificar que las alertas se activen según los umbrales configurados

##### 2.4.6 Limpiar Pruebas
```bash
# Detener procesos de stress
killall stress

# Eliminar archivo grande
rm -f /tmp/largefile

# Verificar que las alertas vuelvan a "Inactive"
```

### 3. Configuración de Alertmanager (Opcional)

#### 3.1 Instalar Alertmanager
```bash
# En la instancia Prometheus
wget https://github.com/prometheus/alertmanager/releases/download/v0.25.0/alertmanager-0.25.0.linux-amd64.tar.gz
tar xvfz alertmanager-0.25.0.linux-amd64.tar.gz
sudo cp alertmanager-0.25.0.linux-amd64/alertmanager /usr/local/bin/
sudo mkdir /etc/alertmanager
sudo useradd --no-create-home --shell /bin/false alertmanager
sudo chown alertmanager:alertmanager /usr/local/bin/alertmanager /etc/alertmanager
```

#### 3.2 Configurar Alertmanager
```bash
# Crear configuración básica
sudo tee /etc/alertmanager/alertmanager.yml > /dev/null <<EOF
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alertmanager@example.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://127.0.0.1:5001/'
EOF

# Crear servicio systemd
sudo tee /etc/systemd/system/alertmanager.service > /dev/null <<EOF
[Unit]
Description=Alertmanager
Wants=network-online.target
After=network-online.target

[Service]
User=alertmanager
Group=alertmanager
Type=simple
ExecStart=/usr/local/bin/alertmanager --config.file /etc/alertmanager/alertmanager.yml --storage.path /var/lib/alertmanager/

[Install]
WantedBy=multi-user.target
EOF

# Iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable alertmanager
sudo systemctl start alertmanager
```

#### 3.3 Conectar Prometheus con Alertmanager
```bash
# Actualizar configuración de Prometheus
sudo tee -a /etc/prometheus/prometheus.yml > /dev/null <<EOF

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093
EOF

# Reiniciar Prometheus
sudo systemctl restart prometheus
```

### 4. Verificación de Grafana

#### 4.1 Acceso inicial
1. Abrir navegador en: `http://[IP_GRAFANA]:3000`
2. Login: `admin` / `admin`
3. Cambiar contraseña cuando se solicite

#### 4.2 Verificar Datasource
1. Ir a **Configuration > Data Sources**
2. Verificar que "Prometheus" esté configurado y funcionando
3. URL debe ser: `http://[IP_PROMETHEUS_PRIVADA]:9090`

#### 4.3 Crear Dashboard de Ejemplo
1. Ir a **+ > Dashboard**
2. Hacer clic en **Add new panel**

**Panel 1: CPU Usage**
- Query: `100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- Visualization: Time series
- Title: "CPU Usage %"

**Panel 2: Memory Usage**
- Query: `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100`
- Visualization: Stat
- Title: "Memory Usage %"

**Panel 3: Disk Usage**
- Query: `100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)`
- Visualization: Gauge
- Title: "Disk Usage %"

**Panel 4: Network Traffic**
- Query A: `rate(node_network_receive_bytes_total{device!="lo"}[5m])`
- Query B: `rate(node_network_transmit_bytes_total{device!="lo"}[5m])`
- Visualization: Time series
- Title: "Network I/O"

#### 4.4 Guardar Dashboard
1. Hacer clic en **Save dashboard**
2. Nombre: "Node Monitoring"
3. Hacer clic en **Save**

### 5. Pruebas de Funcionalidad

#### 5.1 Generar Carga en ec2_a
```bash
# Conectar por SSH a ec2_a
ssh -i vockey.pem ubuntu@[IP_EC2_A]

# Generar carga de CPU
yes > /dev/null &
yes > /dev/null &

# Generar carga de memoria
stress --vm 1 --vm-bytes 512M --timeout 300s

# Generar tráfico de red
ping -f google.com
```

#### 5.2 Verificar Métricas
1. En Prometheus: Ejecutar queries y ver incremento en valores
2. En Grafana: Observar cambios en tiempo real en el dashboard
3. Verificar alertas si están configuradas

#### 5.3 Detener Carga
```bash
# Matar procesos de carga
killall yes
killall stress
killall ping
```

### 6. Verificación de Logs

#### 6.1 Logs de Node Exporter (ec2_a)
```bash
sudo journalctl -u node_exporter -f
```

#### 6.2 Logs de Prometheus
```bash
sudo journalctl -u prometheus -f
```

#### 6.3 Logs de Grafana
```bash
sudo journalctl -u grafana-server -f
```

### 7. Troubleshooting Común

#### 7.1 Si Node Exporter no aparece en Targets
- Verificar que el puerto 9100 esté abierto: `netstat -tlnp | grep 9100`
- Verificar conectividad desde Prometheus: `telnet [IP_EC2_A] 9100`

#### 7.2 Si Grafana no se conecta a Prometheus
- Verificar URL del datasource
- Probar conectividad: `curl http://[IP_PROMETHEUS]:9090/api/v1/query?query=up`

#### 7.3 Si las métricas no aparecen
- Verificar que los servicios estén corriendo
- Revisar logs de errores
- Verificar configuración de firewall

## Notas:
- Las instancias usan t2.micro (elegible para free tier)
- Node Exporter se instala automáticamente en ec2_a
- Prometheus se configura para monitorear ec2_a automáticamente
- Grafana se configura automáticamente con Prometheus como datasource