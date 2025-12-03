#!/bin/bash

# Configurar región
export AWS_DEFAULT_REGION=us-east-1

# Variables globales para almacenar recursos
declare -A RECURSOS

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
    
    RECURSOS[vpc_id]=$VPC_ID
}

ejercicio2_crear_infraestructura() {
    local vpc_id=$1
    echo "=== EJERCICIO 2: Creando infraestructura de red ==="
    
    # Crear Subredes Públicas
    echo "Creando Subred-Publica-1..."
    SUBNET_PUBLICA_1_ID=$(aws ec2 create-subnet --vpc-id $vpc_id --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
    aws ec2 create-tags --resources $SUBNET_PUBLICA_1_ID --tags Key=Name,Value=Subred-Publica-1-AZ-A
    echo "Subred-Publica-1 creada: $SUBNET_PUBLICA_1_ID"
    
    echo "Creando Subred-Publica-2..."
    SUBNET_PUBLICA_2_ID=$(aws ec2 create-subnet --vpc-id $vpc_id --cidr-block 10.0.2.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
    aws ec2 create-tags --resources $SUBNET_PUBLICA_2_ID --tags Key=Name,Value=Subred-Publica-2-AZ-B
    echo "Subred-Publica-2 creada: $SUBNET_PUBLICA_2_ID"
    
    # Crear Subredes Privadas
    echo "Creando Subred-Privada-1..."
    SUBNET_PRIVADA_1_ID=$(aws ec2 create-subnet --vpc-id $vpc_id --cidr-block 10.0.3.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
    aws ec2 create-tags --resources $SUBNET_PRIVADA_1_ID --tags Key=Name,Value=Subred-Privada-1-AZ-A
    echo "Subred-Privada-1 creada: $SUBNET_PRIVADA_1_ID"
    
    echo "Creando Subred-Privada-2..."
    SUBNET_PRIVADA_2_ID=$(aws ec2 create-subnet --vpc-id $vpc_id --cidr-block 10.0.4.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
    aws ec2 create-tags --resources $SUBNET_PRIVADA_2_ID --tags Key=Name,Value=Subred-Privada-2-AZ-B
    echo "Subred-Privada-2 creada: $SUBNET_PRIVADA_2_ID"
    
    # Crear Internet Gateway
    echo "Creando Internet Gateway..."
    IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
    aws ec2 create-tags --resources $IGW_ID --tags Key=Name,Value=Examen-IGW
    aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $vpc_id
    echo "Internet Gateway creado y adjuntado: $IGW_ID"
    
    # Configurar Enrutamiento para Subredes Públicas
    echo "Configurando enrutamiento para subredes públicas..."
    ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $vpc_id --query 'RouteTable.RouteTableId' --output text)
    aws ec2 create-tags --resources $ROUTE_TABLE_ID --tags Key=Name,Value=RT-Subredes-Publicas
    aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
    aws ec2 associate-route-table --route-table-id $ROUTE_TABLE_ID --subnet-id $SUBNET_PUBLICA_1_ID
    aws ec2 associate-route-table --route-table-id $ROUTE_TABLE_ID --subnet-id $SUBNET_PUBLICA_2_ID
    echo "Tabla de enrutamiento creada y asociada: $ROUTE_TABLE_ID"
    
    # Crear NAT Gateway para Subred-Privada-2
    echo "Creando NAT Gateway para Subred-Privada-2..."
    ALLOCATION_2_ID=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
    
    NAT_GATEWAY_2_ID=$(aws ec2 create-nat-gateway --subnet-id $SUBNET_PUBLICA_2_ID --allocation-id $ALLOCATION_2_ID --query 'NatGateway.NatGatewayId' --output text)
    aws ec2 create-tags --resources $NAT_GATEWAY_2_ID --tags Key=Name,Value=Examen-NAT-GW-2
    
    # Esperar a que esté disponible
    echo "Esperando a que NAT Gateway 2 esté disponible..."
    aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GATEWAY_2_ID
    
    # Crear tabla de enrutamiento para Subred-Privada-2
    RT_PRIVADA_2_ID=$(aws ec2 create-route-table --vpc-id $vpc_id --query 'RouteTable.RouteTableId' --output text)
    aws ec2 create-tags --resources $RT_PRIVADA_2_ID --tags Key=Name,Value=RT-Privada-2
    aws ec2 create-route --route-table-id $RT_PRIVADA_2_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_GATEWAY_2_ID
    aws ec2 associate-route-table --route-table-id $RT_PRIVADA_2_ID --subnet-id $SUBNET_PRIVADA_2_ID
    echo "NAT Gateway 2 y tabla de enrutamiento configurados: $NAT_GATEWAY_2_ID"
    
    echo "✅ Infraestructura de red creada exitosamente!"
    
    # Almacenar recursos
    RECURSOS[subnet_publica_1_id]=$SUBNET_PUBLICA_1_ID
    RECURSOS[subnet_publica_2_id]=$SUBNET_PUBLICA_2_ID
    RECURSOS[subnet_privada_1_id]=$SUBNET_PRIVADA_1_ID
    RECURSOS[subnet_privada_2_id]=$SUBNET_PRIVADA_2_ID
    RECURSOS[igw_id]=$IGW_ID
    RECURSOS[route_table_id]=$ROUTE_TABLE_ID
    RECURSOS[nat_gateway_2_id]=$NAT_GATEWAY_2_ID
    RECURSOS[allocation_2_id]=$ALLOCATION_2_ID
}

ejercicio3_nat() {
    local subnet_id=$1
    echo "=== EJERCICIO 3: Creando NAT Gateway ==="
    
    # Crear IP Elástica
    echo "Creando IP Elástica..."
    ALLOCATION_ID=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
    echo "IP Elástica creada: $ALLOCATION_ID"
    
    # Crear NAT Gateway
    echo "Creando NAT Gateway..."
    NAT_GATEWAY_ID=$(aws ec2 create-nat-gateway --subnet-id $subnet_id --allocation-id $ALLOCATION_ID --query 'NatGateway.NatGatewayId' --output text)
    echo "NAT Gateway creado: $NAT_GATEWAY_ID"
    
    # Etiquetar NAT Gateway después de crearlo
    aws ec2 create-tags --resources $NAT_GATEWAY_ID --tags Key=Name,Value=Examen-NAT-GW
    
    # Esperar a que esté disponible
    echo "Esperando a que el NAT Gateway esté disponible..."
    aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GATEWAY_ID
    
    echo "✅ NAT Gateway creado exitosamente!"
    
    RECURSOS[nat_gateway_id]=$NAT_GATEWAY_ID
    RECURSOS[allocation_id]=$ALLOCATION_ID
}

ejercicio4_tablas_enrutamiento() {
    local vpc_id=$1
    local igw_id=$2
    local nat_gateway_id=$3
    local subnet_publica_1_id=$4
    local subnet_publica_2_id=$5
    local subnet_privada_1_id=$6
    local subnet_privada_2_id=$7
    
    echo "=== EJERCICIO 4: Creando tablas de enrutamiento ==="
    
    # Tabla para Subred Pública 1
    echo "Creando tabla de enrutamiento para Subred-Publica-1..."
    RT_PUB_1_ID=$(aws ec2 create-route-table --vpc-id $vpc_id --query 'RouteTable.RouteTableId' --output text)
    aws ec2 create-tags --resources $RT_PUB_1_ID --tags Key=Name,Value=RT-Publica-1
    aws ec2 create-route --route-table-id $RT_PUB_1_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $igw_id
    aws ec2 associate-route-table --route-table-id $RT_PUB_1_ID --subnet-id $subnet_publica_1_id
    echo "Tabla RT-Publica-1 creada: $RT_PUB_1_ID"
    
    # Tabla para Subred Pública 2
    echo "Creando tabla de enrutamiento para Subred-Publica-2..."
    RT_PUB_2_ID=$(aws ec2 create-route-table --vpc-id $vpc_id --query 'RouteTable.RouteTableId' --output text)
    aws ec2 create-tags --resources $RT_PUB_2_ID --tags Key=Name,Value=RT-Publica-2
    aws ec2 create-route --route-table-id $RT_PUB_2_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $igw_id
    aws ec2 associate-route-table --route-table-id $RT_PUB_2_ID --subnet-id $subnet_publica_2_id
    echo "Tabla RT-Publica-2 creada: $RT_PUB_2_ID"
    
    # Tabla para Subred Privada 1
    echo "Creando tabla de enrutamiento para Subred-Privada-1..."
    RT_PRIV_1_ID=$(aws ec2 create-route-table --vpc-id $vpc_id --query 'RouteTable.RouteTableId' --output text)
    aws ec2 create-tags --resources $RT_PRIV_1_ID --tags Key=Name,Value=RT-Privada-1
    aws ec2 create-route --route-table-id $RT_PRIV_1_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $nat_gateway_id
    aws ec2 associate-route-table --route-table-id $RT_PRIV_1_ID --subnet-id $subnet_privada_1_id
    echo "Tabla RT-Privada-1 creada: $RT_PRIV_1_ID"
    
    # Tabla para Subred Privada 2
    echo "Creando tabla de enrutamiento para Subred-Privada-2..."
    RT_PRIV_2_ID=$(aws ec2 create-route-table --vpc-id $vpc_id --query 'RouteTable.RouteTableId' --output text)
    aws ec2 create-tags --resources $RT_PRIV_2_ID --tags Key=Name,Value=RT-Privada-2
    aws ec2 create-route --route-table-id $RT_PRIV_2_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $nat_gateway_id
    aws ec2 associate-route-table --route-table-id $RT_PRIV_2_ID --subnet-id $subnet_privada_2_id
    echo "Tabla RT-Privada-2 creada: $RT_PRIV_2_ID"
    
    echo "✅ Tablas de enrutamiento creadas exitosamente!"
    
    RECURSOS[rt_publica_1_id]=$RT_PUB_1_ID
    RECURSOS[rt_publica_2_id]=$RT_PUB_2_ID
    RECURSOS[rt_privada_1_id]=$RT_PRIV_1_ID
    RECURSOS[rt_privada_2_id]=$RT_PRIV_2_ID
}

ejercicio5_instancias_ec2() {
    local vpc_id=$1
    local subnet_publica_1_id=$2
    local subnet_publica_2_id=$3
    local subnet_privada_1_id=$4
    local subnet_privada_2_id=$5
    
    echo "=== EJERCICIO 5: Creando grupos de seguridad e instancias ==="
    
    # Crear Security Groups para Subredes Públicas (Bastion)
    echo "Creando Security Group GS-Bastion..."
    SG_BASTION_ID=$(aws ec2 create-security-group --group-name GS-Bastion --description "Security Group para Bastion Hosts" --vpc-id $vpc_id --query 'GroupId' --output text)
    aws ec2 create-tags --resources $SG_BASTION_ID --tags Key=Name,Value=GS-Bastion
    
    # Regla SSH para GS-Bastion
    aws ec2 authorize-security-group-ingress --group-id $SG_BASTION_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
    echo "GS-Bastion creado: $SG_BASTION_ID"
    
    # Crear Security Group para Subredes Privadas (App)
    echo "Creando Security Group GS-App..."
    SG_APP_ID=$(aws ec2 create-security-group --group-name GS-App --description "Security Group para App Servers" --vpc-id $vpc_id --query 'GroupId' --output text)
    aws ec2 create-tags --resources $SG_APP_ID --tags Key=Name,Value=GS-App
    
    # Reglas para GS-App (SSH y ICMP solo desde GS-Bastion)
    aws ec2 authorize-security-group-ingress --group-id $SG_APP_ID --protocol tcp --port 22 --source-group $SG_BASTION_ID
    aws ec2 authorize-security-group-ingress --group-id $SG_APP_ID --protocol icmp --port -1 --source-group $SG_BASTION_ID
    echo "GS-App creado: $SG_APP_ID"
    
    # Obtener AMI de Ubuntu
    echo "Obteniendo AMI de Ubuntu..."
    AMI_ID=$(aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' --output text)
    
    # Lanzar instancias Bastion en subredes públicas
    echo "Lanzando Bastion-Host-1..."
    BASTION_1_ID=$(aws ec2 run-instances --image-id $AMI_ID --count 1 --instance-type t2.micro --key-name vockey --subnet-id $subnet_publica_1_id --security-group-ids $SG_BASTION_ID --associate-public-ip-address --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Bastion-Host-1}]' --query 'Instances[0].InstanceId' --output text)
    echo "Bastion-Host-1 lanzado: $BASTION_1_ID"
    
    echo "Lanzando Bastion-Host-2..."
    BASTION_2_ID=$(aws ec2 run-instances --image-id $AMI_ID --count 1 --instance-type t2.micro --key-name vockey --subnet-id $subnet_publica_2_id --security-group-ids $SG_BASTION_ID --associate-public-ip-address --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=Bastion-Host-2}]' --query 'Instances[0].InstanceId' --output text)
    echo "Bastion-Host-2 lanzado: $BASTION_2_ID"
    
    # Lanzar instancias App en subredes privadas
    echo "Lanzando App-Server-1..."
    APP_1_ID=$(aws ec2 run-instances --image-id $AMI_ID --count 1 --instance-type t2.micro --key-name vockey --security-group-ids $SG_APP_ID --subnet-id $subnet_privada_1_id --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=App-Server-1}]' --query 'Instances[0].InstanceId' --output text)
    echo "App-Server-1 lanzado: $APP_1_ID"
    
    echo "Lanzando App-Server-2..."
    APP_2_ID=$(aws ec2 run-instances --image-id $AMI_ID --count 1 --instance-type t2.micro --key-name vockey --security-group-ids $SG_APP_ID --subnet-id $subnet_privada_2_id --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=App-Server-2}]' --query 'Instances[0].InstanceId' --output text)
    echo "App-Server-2 lanzado: $APP_2_ID"
    
    echo "✅ Instancias y grupos de seguridad creados exitosamente!"
    
    RECURSOS[sg_bastion_id]=$SG_BASTION_ID
    RECURSOS[sg_app_id]=$SG_APP_ID
    RECURSOS[bastion_1_id]=$BASTION_1_ID
    RECURSOS[bastion_2_id]=$BASTION_2_ID
    RECURSOS[app_1_id]=$APP_1_ID
    RECURSOS[app_2_id]=$APP_2_ID
}

ejercicio6_nacl() {
    local vpc_id=$1
    local subnet_publica_1_id=$2
    local subnet_publica_2_id=$3
    local subnet_privada_1_id=$4
    local subnet_privada_2_id=$5
    
    echo "=== EJERCICIO 6: Configurando Network ACLs específicas ==="
    
    # NACL para Subredes Públicas (SSH e ICMP permitidos)
    echo "Creando NACL para subredes públicas..."
    NACL_PUBLICA_ID=$(aws ec2 create-network-acl --vpc-id $vpc_id --query 'NetworkAcl.NetworkAclId' --output text)
    aws ec2 create-tags --resources $NACL_PUBLICA_ID --tags Key=Name,Value=NACL-Publica
    
    # Reglas de entrada para NACL pública
    aws ec2 create-network-acl-entry --network-acl-id $NACL_PUBLICA_ID --rule-number 100 --protocol tcp --port-range From=22,To=22 --cidr-block 0.0.0.0/0 --rule-action allow
    aws ec2 create-network-acl-entry --network-acl-id $NACL_PUBLICA_ID --rule-number 110 --protocol icmp --icmp-type-code Type=-1,Code=-1 --cidr-block 0.0.0.0/0 --rule-action allow
    
    # Reglas de salida para NACL pública
    aws ec2 create-network-acl-entry --network-acl-id $NACL_PUBLICA_ID --rule-number 100 --protocol tcp --port-range From=1024,To=65535 --cidr-block 0.0.0.0/0 --rule-action allow --egress
    aws ec2 create-network-acl-entry --network-acl-id $NACL_PUBLICA_ID --rule-number 110 --protocol icmp --icmp-type-code Type=-1,Code=-1 --cidr-block 0.0.0.0/0 --rule-action allow --egress
    
    # NACL para Subredes Privadas (denegar tráfico externo)
    echo "Creando NACL para subredes privadas..."
    NACL_PRIVADA_ID=$(aws ec2 create-network-acl --vpc-id $vpc_id --query 'NetworkAcl.NetworkAclId' --output text)
    aws ec2 create-tags --resources $NACL_PRIVADA_ID --tags Key=Name,Value=NACL-Privada
    
    # Solo permitir tráfico interno de la VPC (10.0.0.0/16)
    aws ec2 create-network-acl-entry --network-acl-id $NACL_PRIVADA_ID --rule-number 100 --protocol tcp --port-range From=22,To=22 --cidr-block 10.0.0.0/16 --rule-action allow
    aws ec2 create-network-acl-entry --network-acl-id $NACL_PRIVADA_ID --rule-number 110 --protocol icmp --icmp-type-code Type=-1,Code=-1 --cidr-block 10.0.0.0/16 --rule-action allow
    
    # Reglas de salida para subredes privadas
    aws ec2 create-network-acl-entry --network-acl-id $NACL_PRIVADA_ID --rule-number 100 --protocol tcp --port-range From=1024,To=65535 --cidr-block 0.0.0.0/0 --rule-action allow --egress
    
    # Asociar NACLs a subredes
    echo "Asociando NACLs a subredes..."
    for subnet_nacl in "$subnet_publica_1_id:$NACL_PUBLICA_ID" "$subnet_publica_2_id:$NACL_PUBLICA_ID" "$subnet_privada_1_id:$NACL_PRIVADA_ID" "$subnet_privada_2_id:$NACL_PRIVADA_ID"; do
        subnet_id=${subnet_nacl%:*}
        nacl_id=${subnet_nacl#*:}
        
        CURRENT_ASSOCIATION_ID=$(aws ec2 describe-network-acls --filters "Name=association.subnet-id,Values=$subnet_id" --query 'NetworkAcls[0].Associations[0].NetworkAclAssociationId' --output text 2>/dev/null)
        
        if [ "$CURRENT_ASSOCIATION_ID" != "None" ] && [ -n "$CURRENT_ASSOCIATION_ID" ]; then
            aws ec2 replace-network-acl-association --association-id $CURRENT_ASSOCIATION_ID --network-acl-id $nacl_id 2>/dev/null && echo "NACL asociada a subred $subnet_id" || echo "Error asociando NACL a subred $subnet_id"
        else
            echo "No se encontró asociación para subred $subnet_id"
        fi
    done
    
    echo "✅ Network ACLs configuradas exitosamente!"
    
    RECURSOS[nacl_publica_id]=$NACL_PUBLICA_ID
    RECURSOS[nacl_privada_id]=$NACL_PRIVADA_ID
}

main() {
    echo
    echo "=================================================="
    echo "INICIANDO EJERCICIOS AWS"
    echo "=================================================="
    
    # Ejercicio 1: Crear VPC
    ejercicio1_crear_vpc
    
    # Ejercicio 2: Crear infraestructura de red
    ejercicio2_crear_infraestructura ${RECURSOS[vpc_id]}
    
    # Ejercicio 3: Crear NAT Gateway
    ejercicio3_nat ${RECURSOS[subnet_publica_1_id]}
    
    # Ejercicio 4: Crear tablas de enrutamiento
    ejercicio4_tablas_enrutamiento ${RECURSOS[vpc_id]} ${RECURSOS[igw_id]} ${RECURSOS[nat_gateway_id]} ${RECURSOS[subnet_publica_1_id]} ${RECURSOS[subnet_publica_2_id]} ${RECURSOS[subnet_privada_1_id]} ${RECURSOS[subnet_privada_2_id]}
    
    # Ejercicio 5: Crear instancias EC2
    ejercicio5_instancias_ec2 ${RECURSOS[vpc_id]} ${RECURSOS[subnet_publica_1_id]} ${RECURSOS[subnet_publica_2_id]} ${RECURSOS[subnet_privada_1_id]} ${RECURSOS[subnet_privada_2_id]}
    
    # Ejercicio 6: Configurar NACLs
    ejercicio6_nacl ${RECURSOS[vpc_id]} ${RECURSOS[subnet_publica_1_id]} ${RECURSOS[subnet_publica_2_id]} ${RECURSOS[subnet_privada_1_id]} ${RECURSOS[subnet_privada_2_id]}
    
    # Resumen final
    echo
    echo "=================================================="
    echo "RESUMEN FINAL"
    echo "=================================================="
    echo "VPC ID: ${RECURSOS[vpc_id]}"
    echo "NAT Gateway 1 ID: ${RECURSOS[nat_gateway_id]}"
    echo "NAT Gateway 2 ID: ${RECURSOS[nat_gateway_2_id]}"
    echo "Instancias creadas: 4 instancias EC2"
    echo "NACLs configuradas: 2 NACLs"
    echo "✅ Todos los ejercicios completados exitosamente!"
    echo "=================================================="
}

# Manejo de errores y ejecución
trap 'echo -e "\n❌ Ejecución interrumpida por el usuario"; exit 1' INT

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI no está instalado"
    exit 1
fi

main "$@"