#!/bin/bash

#Creo la VPC y devuelvo su ID 
VPC_ID=$(aws ec2 create-vpc --cidr-block 172.16.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=entorno,Value=prueba}]' \
    --query Vpc.VpcId --output text)

#Muestro la ID de la VPC
echo "VPC ID: $VPC_ID"

#habilitar dns en la vpc
aws ec2 modify-vpc-attribute \
    --vpc-id $VPC_ID \
    --enable-dns-hostnames "{\"Value\":true}"

echo "DNS habilitado en la VPC"

# ============== CREAR SUBREDES ==============

# Paso 1. Crear subred PÚBLICA
SUB_PUBLICA_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 172.16.16.0/20 \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=mi-subred-publica}]' \
    --query Subnet.SubnetId --output text)

echo "Subred Pública Creada: $SUB_PUBLICA_ID"

# Paso 2. Crear subred PRIVADA
SUB_PRIVADA_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 172.16.0.0/20 \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=mi-subred-privada}]' \
    --query Subnet.SubnetId --output text)

echo "Subred Privada Creada: $SUB_PRIVADA_ID"

#Habilito la asignacion de ipv4 publica en la subred pública
aws ec2 modify-subnet-attribute --subnet $SUB_PUBLICA_ID --map-public-ip-on-launch

# ============== CREAR INTERNET GATEWAY ==============

# Paso 3. Crear el IGW (Internet Gateway)
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=MyIGW}]' \
  --query InternetGateway.InternetGatewayId --output text)

echo "IGW Creado: $IGW_ID"

# Paso 4. Adjuntar el IGW a la VPC
aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID

# ============== CREAR TABLA DE ENRUTAMIENTO PÚBLICA ==============

# Paso 5. Crear tabla de enrutamiento pública
RT_PUBLICA=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=Public-RT}]' \
  --query RouteTable.RouteTableId --output text)

echo "Tabla de enrutamiento pública: $RT_PUBLICA"

# Paso 6. Agregar ruta a Internet desde la subred pública
aws ec2 create-route \
  --route-table-id $RT_PUBLICA \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

# Paso 7. Asociar tabla de enrutamiento pública a subred pública
aws ec2 associate-route-table \
  --route-table-id $RT_PUBLICA \
  --subnet-id $SUB_PUBLICA_ID

# ============== CREAR NAT GATEWAY ==============

# Paso 8. Asignar dirección IP Elástica para el NAT Gateway
ELASTIC_IP=$(aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=NAT-EIP}]' \
  --query PublicIp --output text)

echo "Dirección IP Elástica asignada: $ELASTIC_IP"

# Paso 9. Crear el NAT Gateway en la subred pública
NAT_GW_ID=$(aws ec2 create-nat-gateway \
  --subnet-id $SUB_PUBLICA_ID \
  --allocation-id $(aws ec2 describe-addresses --public-ips $ELASTIC_IP --query 'Addresses[0].AllocationId' --output text) \
  --tag-specifications 'ResourceType=nat-gateway,Tags=[{Key=Name,Value=MyNAT-GW}]' \
  --query NatGateway.NatGatewayId --output text)

echo "NAT Gateway Creado: $NAT_GW_ID"

echo "Esperando a que el NAT Gateway esté disponible..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW_ID

# ============== CREAR TABLA DE ENRUTAMIENTO PRIVADA ==============

# Paso 10. Crear tabla de enrutamiento privada
RT_PRIVADA=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=Private-RT}]' \
  --query RouteTable.RouteTableId --output text)

echo "Tabla de enrutamiento privada: $RT_PRIVADA"

# Paso 11. Agregar ruta en la tabla privada hacia el NAT Gateway
aws ec2 create-route \
  --route-table-id $RT_PRIVADA \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW_ID

# Paso 12. Asociar tabla de enrutamiento privada a subred privada
aws ec2 associate-route-table \
  --route-table-id $RT_PRIVADA \
  --subnet-id $SUB_PRIVADA_ID

# ============== CREAR GRUPOS DE SEGURIDAD ==============

# Paso 13. Crear grupo de seguridad para la EC2 PÚBLICA
SG_PUBLICA=$(aws ec2 create-security-group \
  --vpc-id $VPC_ID \
  --group-name sg-ec2-publica \
  --description "Grupo de seguridad para EC2 pública - Acceso SSH desde exterior" \
  --query GroupId \
  --output text)

echo "Grupo de seguridad público creado: $SG_PUBLICA"

# Permitir SSH desde cualquier lugar (0.0.0.0/0)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_PUBLICA \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

aws ec2 create-tags \
  --resources $SG_PUBLICA \
  --tags "Key=Name,Value=sg-ec2-publica"

# Paso 14. Crear grupo de seguridad para la EC2 PRIVADA
SG_PRIVADA=$(aws ec2 create-security-group \
  --vpc-id $VPC_ID \
  --group-name sg-ec2-privada \
  --description "Grupo de seguridad para EC2 privada - Acceso SSH solo desde la VPC" \
  --query GroupId \
  --output text)

echo "Grupo de seguridad privado creado: $SG_PRIVADA"

# Permitir SSH solo desde la VPC (subred pública)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_PRIVADA \
  --protocol tcp \
  --port 22 \
  --cidr 172.16.0.0/16

# Permitir tráfico saliente irrestricto
aws ec2 authorize-security-group-egress \
  --group-id $SG_PRIVADA \
  --protocol -1 \
  --cidr 0.0.0.0/0

aws ec2 create-tags \
  --resources $SG_PRIVADA \
  --tags "Key=Name,Value=sg-ec2-privada"

# ============== CREAR INSTANCIA EC2 PÚBLICA ==============

echo "Esperando 10 segundos antes de crear las instancias..."
sleep 10

echo "Creando instancia EC2 PÚBLICA..."

EC2_PUBLICA=$(aws ec2 run-instances \
  --image-id ami-0360c520857e3138f \
  --instance-type t3.micro \
  --key-name vockey \
  --subnet-id $SUB_PUBLICA_ID \
  --security-group-ids $SG_PUBLICA \
  --associate-public-ip-address \
  --private-ip-address 172.16.16.100 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ec2-publica-bastion}]' \
  --query Instances[0].InstanceId \
  --output text)

echo "Instancia EC2 Pública Creada: $EC2_PUBLICA"

echo "Esperando 20 segundos a que la instancia pública se cree..."
sleep 20

# Obtener IP pública de la instancia pública
IP_PUBLICA=$(aws ec2 describe-instances \
  --instance-ids $EC2_PUBLICA \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "IP Pública de la instancia: $IP_PUBLICA"

# ============== CREAR INSTANCIA EC2 PRIVADA ==============

echo "Creando instancia EC2 PRIVADA..."

# Script de prueba para user data
cat > /tmp/user_data.sh << 'EOF'
#!/bin/bash
# Script de prueba de conectividad NAT

echo "Iniciando configuración de EC2 privada..." > /var/log/nat-setup.log

# Actualizar el sistema
yum update -y >> /var/log/nat-setup.log 2>&1

# Instalar herramientas útiles
yum install -y curl wget net-tools >> /var/log/nat-setup.log 2>&1

# Crear un archivo de log de pruebas
{
  echo "=== Prueba de Conectividad a Internet a través del NAT Gateway ==="
  echo "Timestamp: $(date)"
  echo ""
  echo "=== Información de Interfaz de Red ==="
  ip addr show
  echo ""
  echo "=== Tabla de Enrutamiento ==="
  ip route show
  echo ""
  echo "=== Prueba de DNS ==="
  nslookup google.com
  echo ""
  echo "=== Conectividad a Internet ==="
  curl -v https://www.google.com 2>&1 | head -20
  echo ""
  echo "=== IP Pública (a través del NAT Gateway) ==="
  curl -s https://checkip.amazonaws.com
  echo ""
  echo "=== Prueba completada ==="
} >> /var/log/nat-setup.log 2>&1

EOF

EC2_PRIVADA=$(aws ec2 run-instances \
  --image-id ami-0360c520857e3138f \
  --instance-type t3.micro \
  --key-name vockey \
  --subnet-id $SUB_PRIVADA_ID \
  --security-group-ids $SG_PRIVADA \
  --no-associate-public-ip-address \
  --private-ip-address 172.16.0.50 \
  --user-data file:///tmp/user_data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ec2-privada}]' \
  --query Instances[0].InstanceId \
  --output text)

echo "Instancia EC2 Privada Creada: $EC2_PRIVADA"

echo "Esperando 20 segundos a que la instancia privada se cree..."
sleep 20

# Obtener IP privada de la instancia privada
IP_PRIVADA=$(aws ec2 describe-instances \
  --instance-ids $EC2_PRIVADA \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text)

echo ""
echo "========== CONFIGURACIÓN COMPLETADA =========="
echo ""
echo "=== VPC Y REDES ==="
echo "VPC ID: $VPC_ID"
echo "Subred Pública: $SUB_PUBLICA_ID (172.16.16.0/20)"
echo "Subred Privada: $SUB_PRIVADA_ID (172.16.0.0/20)"
echo ""
echo "=== GATEWAYS E INTERNET ==="
echo "Internet Gateway: $IGW_ID"
echo "NAT Gateway: $NAT_GW_ID"
echo "IP Elástica del NAT: $ELASTIC_IP"
echo ""
echo "=== TABLAS DE ENRUTAMIENTO ==="
echo "Tabla Pública: $RT_PUBLICA"
echo "Tabla Privada: $RT_PRIVADA"
echo ""
echo "=== GRUPOS DE SEGURIDAD ==="
echo "Grupo Público: $SG_PUBLICA"
echo "Grupo Privado: $SG_PRIVADA"
echo ""
echo "=== INSTANCIAS EC2 ==="
echo "EC2 PÚBLICA (Bastion) ID: $EC2_PUBLICA"
echo "  - IP Privada: 172.16.16.100"
echo "  - IP Pública: $IP_PUBLICA"
echo ""
echo "EC2 PRIVADA ID: $EC2_PRIVADA"
echo "  - IP Privada: $IP_PRIVADA"
echo "  - Acceso a Internet: A través del NAT Gateway ($ELASTIC_IP)"
echo ""
echo "========== INSTRUCCIONES DE CONEXIÓN =========="
echo ""
echo "1. CONECTARSE A LA EC2 PÚBLICA DESDE EL EXTERIOR:"
echo "   ssh -i vockey.pem ec2-user@$IP_PUBLICA"
echo ""
echo "2. DESDE LA EC2 PÚBLICA, CONECTARSE A LA EC2 PRIVADA:"
echo "   ssh -i /tmp/vockey.pem ec2-user@$IP_PRIVADA"
echo ""
echo "   NOTA: Necesitas transferir la clave privada a la EC2 pública primero:"
echo "   scp -i vockey.pem vockey.pem ec2-user@$IP_PUBLICA:/tmp/"
echo ""
echo "3. VERIFICAR LOGS DE PRUEBA EN LA EC2 PRIVADA:"
echo "   tail -f /var/log/nat-setup.log"
echo ""
echo "========== FLUJO DE ACCESO =========="
echo "Exterior --> IP Pública ($IP_PUBLICA)"
echo "          --> EC2 Pública (172.16.16.100)"
echo "          --> EC2 Privada ($IP_PRIVADA)"
echo "          --> Internet (a través de NAT Gateway con IP $ELASTIC_IP)"
echo ""
echo "=========================================="