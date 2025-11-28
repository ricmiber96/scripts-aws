#!/bin/bash

echo "========== INICIANDO LIMPIEZA DE INFRAESTRUCTURA =========="

# Obtener VPC ID por tag
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=tag:entorno,Values=prueba" \
    --query 'Vpcs[0].VpcId' --output text)

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    echo "No se encontró VPC con tag entorno=prueba"
    exit 1
fi

echo "VPC encontrada: $VPC_ID"

# ============== ELIMINAR INSTANCIAS EC2 ==============

echo "Eliminando instancias EC2..."

# Obtener IDs de instancias en la VPC
INSTANCES=$(aws ec2 describe-instances \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=instance-state-name,Values=running,stopped,stopping" \
    --query 'Reservations[].Instances[].InstanceId' --output text)

if [ ! -z "$INSTANCES" ]; then
    echo "Terminando instancias: $INSTANCES"
    aws ec2 terminate-instances --instance-ids $INSTANCES
    echo "Esperando a que las instancias se terminen..."
    aws ec2 wait instance-terminated --instance-ids $INSTANCES
    echo "Instancias terminadas"
else
    echo "No se encontraron instancias"
fi

# ============== ELIMINAR NAT GATEWAY ==============

echo "Eliminando NAT Gateway..."

NAT_GW_ID=$(aws ec2 describe-nat-gateways \
    --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" \
    --query 'NatGateways[0].NatGatewayId' --output text)

if [ "$NAT_GW_ID" != "None" ] && [ ! -z "$NAT_GW_ID" ]; then
    echo "NAT Gateway encontrado: $NAT_GW_ID"
    
    # Obtener Allocation ID de la IP elástica
    ALLOCATION_ID=$(aws ec2 describe-nat-gateways \
        --nat-gateway-ids $NAT_GW_ID \
        --query 'NatGateways[0].NatGatewayAddresses[0].AllocationId' --output text)
    
    aws ec2 delete-nat-gateway --nat-gateway-id $NAT_GW_ID
    echo "Esperando a que el NAT Gateway se elimine..."
    aws ec2 wait nat-gateway-deleted --nat-gateway-ids $NAT_GW_ID
    
    # Liberar IP elástica
    if [ "$ALLOCATION_ID" != "None" ] && [ ! -z "$ALLOCATION_ID" ]; then
        echo "Liberando IP elástica: $ALLOCATION_ID"
        aws ec2 release-address --allocation-id $ALLOCATION_ID
    fi
    
    echo "NAT Gateway eliminado"
else
    echo "No se encontró NAT Gateway"
fi

# ============== ELIMINAR TABLAS DE ENRUTAMIENTO ==============

echo "Eliminando tablas de enrutamiento personalizadas..."

ROUTE_TABLES=$(aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'RouteTables[?Associations[0].Main!=`true`].RouteTableId' --output text)

for RT_ID in $ROUTE_TABLES; do
    if [ ! -z "$RT_ID" ]; then
        echo "Eliminando tabla de enrutamiento: $RT_ID"
        
        # Desasociar de subredes
        ASSOCIATIONS=$(aws ec2 describe-route-tables \
            --route-table-ids $RT_ID \
            --query 'RouteTables[0].Associations[?Main!=`true`].RouteTableAssociationId' --output text)
        
        for ASSOC_ID in $ASSOCIATIONS; do
            if [ ! -z "$ASSOC_ID" ]; then
                aws ec2 disassociate-route-table --association-id $ASSOC_ID
            fi
        done
        
        aws ec2 delete-route-table --route-table-id $RT_ID
    fi
done

# ============== ELIMINAR INTERNET GATEWAY ==============

echo "Eliminando Internet Gateway..."

IGW_ID=$(aws ec2 describe-internet-gateways \
    --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
    --query 'InternetGateways[0].InternetGatewayId' --output text)

if [ "$IGW_ID" != "None" ] && [ ! -z "$IGW_ID" ]; then
    echo "Internet Gateway encontrado: $IGW_ID"
    aws ec2 detach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
    aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID
    echo "Internet Gateway eliminado"
else
    echo "No se encontró Internet Gateway"
fi

# ============== ELIMINAR GRUPOS DE SEGURIDAD ==============

echo "Eliminando grupos de seguridad..."

SECURITY_GROUPS=$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text)

for SG_ID in $SECURITY_GROUPS; do
    if [ ! -z "$SG_ID" ]; then
        echo "Eliminando grupo de seguridad: $SG_ID"
        aws ec2 delete-security-group --group-id $SG_ID
    fi
done

# ============== ELIMINAR SUBREDES ==============

echo "Eliminando subredes..."

SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[].SubnetId' --output text)

for SUBNET_ID in $SUBNETS; do
    if [ ! -z "$SUBNET_ID" ]; then
        echo "Eliminando subred: $SUBNET_ID"
        aws ec2 delete-subnet --subnet-id $SUBNET_ID
    fi
done

# ============== ELIMINAR VPC ==============

echo "Eliminando VPC..."
aws ec2 delete-vpc --vpc-id $VPC_ID
echo "VPC eliminada: $VPC_ID"

# ============== LIMPIAR ARCHIVOS TEMPORALES ==============

if [ -f "/tmp/user_data.sh" ]; then
    rm /tmp/user_data.sh
    echo "Archivo temporal eliminado"
fi

echo ""
echo "========== LIMPIEZA COMPLETADA =========="
echo "Toda la infraestructura ha sido eliminada exitosamente"
echo "VPC eliminada: $VPC_ID"