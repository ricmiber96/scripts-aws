#!/bin/bash

# Configurar región
export AWS_DEFAULT_REGION=us-east-1

ejercicio1_crear_vpc() {
    echo "=== EJERCICIO 1: Creando VPC ==="
    
    # Crear VPC con CIDR 10.0.0.0/16
    echo "Creando VPC..."
    VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text)
    echo "VPC creada con ID: $VPC_ID"
    
    # Habilitar DNS Support y Hostnames
    echo "Habilitando DNS Support..."
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support
    
    echo "Habilitando DNS Hostnames..."
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
    
    # Etiquetar VPC
    echo "Etiquetando VPC..."
    aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=Examen-VPC-Ricardo
    
    echo "✅ VPC creada exitosamente: $VPC_ID"
    echo
}

ejercicio2_crear_infraestructura() {
    local vpc_id=$1
    echo "=== EJERCICIO 2: Creando infraestructura de red ==="
    
    # Crear Subred-Publica
    echo "Creando Subred-Publica..."
    SUBNET_PUBLICA_ID=$(aws ec2 create-subnet --vpc-id $vpc_id --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
    aws ec2 create-tags --resources $SUBNET_PUBLICA_ID --tags Key=Name,Value=Subred-Publica
    
    # Habilitar asignación automática de IP pública
    aws ec2 modify-subnet-attribute --subnet-id $SUBNET_PUBLICA_ID --map-public-ip-on-launch
    echo "Subred-Publica creada: $SUBNET_PUBLICA_ID"
    
    # Crear Subred-App
    echo "Creando Subred-App..."
    SUBNET_APP_ID=$(aws ec2 create-subnet --vpc-id $vpc_id --cidr-block 10.0.2.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
    aws ec2 create-tags --resources $SUBNET_APP_ID --tags Key=Name,Value=Subred-App
    echo "Subred-App creada: $SUBNET_APP_ID"
    
    # Crear Internet Gateway
    echo "Creando Internet Gateway..."
    IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
    aws ec2 create-tags --resources $IGW_ID --tags Key=Name,Value=Examen-IGW
    aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $vpc_id
    echo "Internet Gateway creado y adjuntado: $IGW_ID"
    
    # Configurar Enrutamiento
    echo "Configurando enrutamiento..."
    ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $vpc_id --query 'RouteTable.RouteTableId' --output text)
    aws ec2 create-tags --resources $ROUTE_TABLE_ID --tags Key=Name,Value=RT-Subred-Publica
    aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
    aws ec2 associate-route-table --route-table-id $ROUTE_TABLE_ID --subnet-id $SUBNET_PUBLICA_ID
    
    echo "✅ Infraestructura de red creada exitosamente!"
}

ejercicio3_crear_instancias() {
    local vpc_id=$1
    local subnet_publica_id=$2
    local subnet_app_id=$3
    echo "=== EJERCICIO 3: Creando grupos de seguridad e instancias ==="
    
    # Crear Security Group GS-Bastion
    echo "Creando Security Group GS-Bastion..."
    SG_BASTION_ID=$(aws ec2 create-security-group --group-name GS-Bastion --description "Security Group para Bastion Host" --vpc-id $vpc_id --query 'GroupId' --output text)
    aws ec2 create-tags --resources $SG_BASTION_ID --tags Key=Name,Value=GS-Bastion
    
    # Regla SSH para GS-Bastion
    aws ec2 authorize-security-group-ingress --group-id $SG_BASTION_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
    echo "GS-Bastion creado: $SG_BASTION_ID"
    
    # Crear Security Group GS-App
    echo "Creando Security Group GS-App..."
    SG_APP_ID=$(aws ec2 create-security-group --group-name GS-App --description "Security Group para App Server" --vpc-id $vpc_id --query 'GroupId' --output text)
    aws ec2 create-tags --resources $SG_APP_ID --tags Key=Name,Value=GS-App
    
    # Reglas para GS-App (SSH y ICMP desde GS-Bastion)
    aws ec2 authorize-security-group-ingress --group-id $SG_APP_ID --protocol tcp --port 22 --source-group $SG_BASTION_ID
    aws ec2 authorize-security-group-ingress --group-id $SG_APP_ID --protocol icmp --port -1 --source-group $SG_BASTION_ID
    echo "GS-App creado: $SG_APP_ID"
    
    # Obtener AMI de Ubuntu
    echo "Obteniendo AMI de Ubuntu..."
    AMI_ID=$(aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' --output text)
    
    # Lanzar instancia Bastion-Host
    echo "Lanzando instancia Bastion-Host..."
    BASTION_ID=$(aws ec2 run-instances --image-id $AMI_ID --count 1 --instance-type t2.micro --key-name vockey --subnet-id $subnet_publica_id --security-group-ids $SG_BASTION_ID --associate-public-ip-address --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Bastion-Host}]' --query 'Instances[0].InstanceId' --output text)
    echo "Bastion-Host lanzado: $BASTION_ID"
    
    # Lanzar instancia App-Server
    echo "Lanzando instancia App-Server..."
    APP_SERVER_ID=$(aws ec2 run-instances --image-id $AMI_ID --count 1 --instance-type t2.micro --key-name vockey --subnet-id $subnet_app_id --security-group-ids $SG_APP_ID --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=App-Server}]' --query 'Instances[0].InstanceId' --output text)
    echo "App-Server lanzado: $APP_SERVER_ID"
    
    echo "✅ Instancias y grupos de seguridad creados exitosamente!"
}

ejercicio4_crear_nat_gateway() {
    local vpc_id=$1
    local subnet_publica_id=$2
    local subnet_app_id=$3
    echo "=== EJERCICIO 4: Implementación de NAT Gateway para Salida Privada ==="
    
    # Crear IP Elástica
    echo "Creando IP Elástica..."
    ELASTIC_IP_ALLOC=$(aws ec2 allocate-address --domain vpc --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=Examen-NAT-EIP}]' --query 'AllocationId' --output text)
    echo "IP Elástica creada: $ELASTIC_IP_ALLOC"
    
    # Crear NAT Gateway
    echo "Creando NAT Gateway..."
    NAT_GW_ID=$(aws ec2 create-nat-gateway --subnet-id $subnet_publica_id --allocation-id $ELASTIC_IP_ALLOC --query 'NatGateway.NatGatewayId' --output text)
    
    # Etiquetar NAT Gateway
    aws ec2 create-tags --resources $NAT_GW_ID --tags Key=Name,Value=Examen-NAT-GW
    echo "NAT Gateway creado: $NAT_GW_ID"
    
    # Esperar a que el NAT Gateway esté disponible
    echo "Esperando a que el NAT Gateway esté disponible..."
    aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW_ID
    
    # Obtener la tabla de rutas privada
    RT_PRIVADA_ID=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$vpc_id" "Name=association.subnet-id,Values=$subnet_app_id" --query 'RouteTables[0].RouteTableId' --output text)
    
    # Agregar ruta hacia el NAT Gateway
    echo "Configurando ruta hacia NAT Gateway..."
    aws ec2 create-route --route-table-id $RT_PRIVADA_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_GW_ID
    
    echo "✅ NAT Gateway configurado exitosamente!"
    echo "El App-Server ahora tiene salida a internet a través del NAT Gateway"
}

ejercicio5_configurar_nacl_fallo_ping() {
    local vpc_id=$1
    local subnet_app_id=$2
    echo "=== EJERCICIO 5: Configurando Network ACL (FALLO PING) ==="
    
    # Crear Network ACL
    echo "Creando Network ACL..."
    NACL_ID=$(aws ec2 create-network-acl --vpc-id $vpc_id --query 'NetworkAcl.NetworkAclId' --output text)
    aws ec2 create-tags --resources $NACL_ID --tags Key=Name,Value=NACL-Fallo-Ping
    echo "Network ACL creada: $NACL_ID"
    
    # Asociar NACL a Subred-App
    echo "Asociando NACL a Subred-App..."
    CURRENT_ASSOCIATION_ID=$(aws ec2 describe-network-acls --filters "Name=association.subnet-id,Values=$subnet_app_id" --query 'NetworkAcls[0].Associations[0].NetworkAclAssociationId' --output text)
    aws ec2 replace-network-acl-association --association-id $CURRENT_ASSOCIATION_ID --network-acl-id $NACL_ID
    echo "NACL asociada a Subred-App"
    
    # Reglas de entrada (Inbound) - PERMITIR TODO
    echo "Configurando reglas de entrada..."
    # SSH (puerto 22)
    aws ec2 create-network-acl-entry --network-acl-id $NACL_ID --rule-number 100 --protocol tcp --port-range From=22,To=22 --cidr-block 0.0.0.0/0 --rule-action allow
    
    # ICMP de entrada - PERMITIR (para recibir ping)
    aws ec2 create-network-acl-entry --network-acl-id $NACL_ID --rule-number 110 --protocol icmp --icmp-type-code Type=-1,Code=-1 --cidr-block 0.0.0.0/0 --rule-action allow
    
    # Reglas de salida (Outbound) - BLOQUEAR ICMP
    echo "Configurando reglas de salida (SIN ICMP)..."
    # Puertos efímeros para respuestas SSH (1024-65535) - PERMITIR
    aws ec2 create-network-acl-entry --network-acl-id $NACL_ID --rule-number 100 --protocol tcp --port-range From=1024,To=65535 --cidr-block 0.0.0.0/0 --rule-action allow --egress
    
    # *** NO AÑADIR REGLA ICMP DE SALIDA - ESTO CAUSA EL FALLO ***
    # Las respuestas ICMP serán bloqueadas, demostrando el comportamiento stateless
    
    echo "⚠️  Network ACL configurada SIN reglas ICMP de salida"
    echo "⚠️  El ping FALLARÁ porque las respuestas ICMP están bloqueadas"
    echo "⚠️  Esto demuestra el comportamiento STATELESS de las NACLs"
}

ejercicio5_configurar_nacl() {
    local vpc_id=$1
    local subnet_app_id=$2
    echo "=== EJERCICIO 5: Configurando Network ACL ==="
    
    # Crear Network ACL
    echo "Creando Network ACL..."
    NACL_ID=$(aws ec2 create-network-acl --vpc-id $vpc_id --query 'NetworkAcl.NetworkAclId' --output text)
    aws ec2 create-tags --resources $NACL_ID --tags Key=Name,Value=NACL-Prueba
    echo "Network ACL creada: $NACL_ID"
    
    # Asociar NACL a Subred-App
    echo "Asociando NACL a Subred-App..."
    CURRENT_ASSOCIATION_ID=$(aws ec2 describe-network-acls --filters "Name=association.subnet-id,Values=$subnet_app_id" --query 'NetworkAcls[0].Associations[0].NetworkAclAssociationId' --output text)
    aws ec2 replace-network-acl-association --association-id $CURRENT_ASSOCIATION_ID --network-acl-id $NACL_ID
    echo "NACL asociada a Subred-App"
    
    # Reglas de entrada (Inbound)
    echo "Configurando reglas de entrada..."
    # SSH (puerto 22)
    aws ec2 create-network-acl-entry --network-acl-id $NACL_ID --rule-number 100 --protocol tcp --port-range From=22,To=22 --cidr-block 0.0.0.0/0 --rule-action allow
    
    # ICMP
    aws ec2 create-network-acl-entry --network-acl-id $NACL_ID --rule-number 110 --protocol icmp --icmp-type-code Type=-1,Code=-1 --cidr-block 0.0.0.0/0 --rule-action allow
    
    # Reglas de salida (Outbound)
    echo "Configurando reglas de salida..."
    # Puertos efímeros para respuestas SSH (1024-65535)
    aws ec2 create-network-acl-entry --network-acl-id $NACL_ID --rule-number 100 --protocol tcp --port-range From=1024,To=65535 --cidr-block 0.0.0.0/0 --rule-action allow --egress
    
    # ICMP de salida
    aws ec2 create-network-acl-entry --network-acl-id $NACL_ID --rule-number 110 --protocol icmp --icmp-type-code Type=-1,Code=-1 --cidr-block 0.0.0.0/0 --rule-action allow --egress
    
    echo "✅ Network ACL configurada exitosamente!"
}

main() {
    # Ejecutar ejercicios
    ejercicio1_crear_vpc
    ejercicio2_crear_infraestructura $VPC_ID
    ejercicio3_crear_instancias $VPC_ID $SUBNET_PUBLICA_ID $SUBNET_APP_ID
    ejercicio4_crear_nat_gateway $VPC_ID $SUBNET_PUBLICA_ID $SUBNET_APP_ID
    
    # Usar la función normal o la de fallo según se necesite
    ejercicio5_configurar_nacl $VPC_ID $SUBNET_APP_ID
    # ejercicio5_configurar_nacl_fallo_ping $VPC_ID $SUBNET_APP_ID  # Para demostrar fallo
    
    # Resumen final
    echo
    echo "=== RESUMEN FINAL ==="
    echo "VPC ID: $VPC_ID"
    echo "Subred-Publica ID: $SUBNET_PUBLICA_ID"
    echo "Subred-App ID: $SUBNET_APP_ID"
    echo "Internet Gateway ID: $IGW_ID"
    echo "Tabla de Enrutamiento ID: $ROUTE_TABLE_ID"
    echo "Security Group Bastion ID: $SG_BASTION_ID"
    echo "Security Group App ID: $SG_APP_ID"
    echo "Bastion-Host ID: $BASTION_ID"
    echo "App-Server ID: $APP_SERVER_ID"
    echo "NAT Gateway ID: $NAT_GW_ID"
    echo "IP Elástica NAT: $ELASTIC_IP_ALLOC"
    echo "Network ACL ID: $NACL_ID"
    echo
    echo "Nota: App-Server tiene salida a internet a través del NAT Gateway"
    echo "Nota: NACL-Prueba está asociada a Subred-App con reglas stateless para SSH e ICMP"
    echo
    echo "Para demostrar el comportamiento STATELESS de las NACLs:"
    echo "- Cambia 'ejercicio5_configurar_nacl' por 'ejercicio5_configurar_nacl_fallo_ping' en main()"
    echo "- El ping fallará porque las respuestas ICMP estarán bloqueadas"
}

# Ejecutar script principal
main