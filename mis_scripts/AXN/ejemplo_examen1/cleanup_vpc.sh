#!/bin/bash

# Script para limpiar la VPC 'Examen-VPC-Ricardo' y toda su infraestructura
# Versión bash del script cleanup_vpc.py

set -e

REGION="us-east-1"
VPC_NAME="Examen-VPC-Ricardo"

echo "Buscando VPC '$VPC_NAME'..."
VPC_ID=$(aws ec2 describe-vpcs --region $REGION \
    --filters "Name=tag:Name,Values=$VPC_NAME" \
    --query 'Vpcs[0].VpcId' --output text)

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    echo "❌ No se encontró la VPC '$VPC_NAME'"
    exit 1
fi

echo "VPC encontrada: $VPC_ID"

# 1. Terminar instancias EC2
echo -e "\nTerminando instancias EC2..."
INSTANCE_IDS=$(aws ec2 describe-instances --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=instance-state-name,Values=running,stopped" \
    --query 'Reservations[].Instances[].InstanceId' --output text)

if [ -n "$INSTANCE_IDS" ]; then
    aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_IDS
    echo "Instancias terminadas: $INSTANCE_IDS"
    
    echo "Esperando terminación de instancias..."
    aws ec2 wait instance-terminated --region $REGION --instance-ids $INSTANCE_IDS
    echo "Instancias terminadas exitosamente"
fi

# 2. Restaurar asociaciones de Network ACL y eliminar NACLs personalizadas
echo -e "\nEliminando Network ACLs personalizadas..."
DEFAULT_NACL_ID=$(aws ec2 describe-network-acls --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=default,Values=true" \
    --query 'NetworkAcls[0].NetworkAclId' --output text)

CUSTOM_NACLS=$(aws ec2 describe-network-acls --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=default,Values=false" \
    --query 'NetworkAcls[].NetworkAclId' --output text)

for NACL_ID in $CUSTOM_NACLS; do
    # Restaurar asociaciones a la NACL por defecto
    ASSOCIATIONS=$(aws ec2 describe-network-acls --region $REGION \
        --network-acl-ids $NACL_ID \
        --query 'NetworkAcls[0].Associations[].NetworkAclAssociationId' --output text)
    
    for ASSOC_ID in $ASSOCIATIONS; do
        aws ec2 replace-network-acl-association --region $REGION \
            --association-id $ASSOC_ID --network-acl-id $DEFAULT_NACL_ID || true
    done
    
    # Eliminar NACL personalizada
    aws ec2 delete-network-acl --region $REGION --network-acl-id $NACL_ID || true
    echo "Network ACL $NACL_ID eliminada"
done

# 3. Eliminar grupos de seguridad
echo -e "\nEliminando grupos de seguridad..."
SECURITY_GROUPS=$(aws ec2 describe-security-groups --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text)

# Primero eliminar reglas que referencian otros Security Groups
for SG_ID in $SECURITY_GROUPS; do
    # Eliminar reglas de entrada con referencias a otros SGs
    aws ec2 describe-security-groups --region $REGION --group-ids $SG_ID \
        --query 'SecurityGroups[0].IpPermissions[?UserIdGroupPairs]' --output json | \
    jq -c '.[]?' | while read -r rule; do
        if [ "$rule" != "null" ] && [ -n "$rule" ]; then
            aws ec2 revoke-security-group-ingress --region $REGION \
                --group-id $SG_ID --ip-permissions "$rule" || true
        fi
    done
    
    # Eliminar reglas de salida con referencias a otros SGs
    aws ec2 describe-security-groups --region $REGION --group-ids $SG_ID \
        --query 'SecurityGroups[0].IpPermissionsEgress[?UserIdGroupPairs]' --output json | \
    jq -c '.[]?' | while read -r rule; do
        if [ "$rule" != "null" ] && [ -n "$rule" ]; then
            aws ec2 revoke-security-group-egress --region $REGION \
                --group-id $SG_ID --ip-permissions "$rule" || true
        fi
    done
done

# Luego eliminar los Security Groups
for SG_ID in $SECURITY_GROUPS; do
    aws ec2 delete-security-group --region $REGION --group-id $SG_ID || true
    echo "Security Group $SG_ID eliminado"
done

# 4. Eliminar NAT Gateways e IPs Elásticas
echo -e "\nEliminando NAT Gateways..."
NAT_GW_IDS=$(aws ec2 describe-nat-gateways --region $REGION \
    --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" \
    --query 'NatGateways[].NatGatewayId' --output text)

for NAT_GW_ID in $NAT_GW_IDS; do
    # Obtener Allocation ID de la IP elástica
    ALLOCATION_ID=$(aws ec2 describe-nat-gateways --region $REGION \
        --nat-gateway-ids $NAT_GW_ID \
        --query 'NatGateways[0].NatGatewayAddresses[0].AllocationId' --output text)
    
    # Eliminar NAT Gateway
    aws ec2 delete-nat-gateway --region $REGION --nat-gateway-id $NAT_GW_ID || true
    echo "NAT Gateway $NAT_GW_ID eliminado"
    
    # Esperar a que se elimine
    echo "Esperando eliminación del NAT Gateway..."
    aws ec2 wait nat-gateway-deleted --region $REGION --nat-gateway-ids $NAT_GW_ID || true
    
    # Liberar IP elástica
    if [ "$ALLOCATION_ID" != "None" ] && [ -n "$ALLOCATION_ID" ]; then
        aws ec2 release-address --region $REGION --allocation-id $ALLOCATION_ID || true
        echo "IP Elástica $ALLOCATION_ID liberada"
    fi
done

# 5. Eliminar tablas de enrutamiento personalizadas
echo -e "\nEliminando tablas de enrutamiento..."
ROUTE_TABLES=$(aws ec2 describe-route-tables --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'RouteTables[?!Associations[?Main==`true`]].RouteTableId' --output text)

for RT_ID in $ROUTE_TABLES; do
    # Desasociar de subredes
    ASSOCIATIONS=$(aws ec2 describe-route-tables --region $REGION \
        --route-table-ids $RT_ID \
        --query 'RouteTables[0].Associations[?!Main].RouteTableAssociationId' --output text)
    
    for ASSOC_ID in $ASSOCIATIONS; do
        aws ec2 disassociate-route-table --region $REGION --association-id $ASSOC_ID || true
    done
    
    # Eliminar tabla de enrutamiento
    aws ec2 delete-route-table --region $REGION --route-table-id $RT_ID || true
    echo "Tabla de enrutamiento $RT_ID eliminada"
done

# 6. Desconectar y eliminar Internet Gateway
echo -e "\nEliminando Internet Gateway..."
IGW_IDS=$(aws ec2 describe-internet-gateways --region $REGION \
    --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
    --query 'InternetGateways[].InternetGatewayId' --output text)

for IGW_ID in $IGW_IDS; do
    aws ec2 detach-internet-gateway --region $REGION \
        --internet-gateway-id $IGW_ID --vpc-id $VPC_ID || true
    aws ec2 delete-internet-gateway --region $REGION --internet-gateway-id $IGW_ID || true
    echo "Internet Gateway $IGW_ID eliminado"
done

# 7. Eliminar subredes
echo -e "\nEliminando subredes..."
SUBNET_IDS=$(aws ec2 describe-subnets --region $REGION \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[].SubnetId' --output text)

for SUBNET_ID in $SUBNET_IDS; do
    aws ec2 delete-subnet --region $REGION --subnet-id $SUBNET_ID || true
    echo "Subred $SUBNET_ID eliminada"
done

# 8. Eliminar VPC
echo -e "\nEliminando VPC..."
aws ec2 delete-vpc --region $REGION --vpc-id $VPC_ID
echo "✅ VPC $VPC_ID y toda su infraestructura eliminada exitosamente!"