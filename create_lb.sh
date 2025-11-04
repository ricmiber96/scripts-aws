#!/bin/bash
# -----------------------------------------------------------------
# VARIABLES: ¡AJUSTA ESTOS VALORES!
# -----------------------------------------------------------------

# Nombres (puedes cambiarlos)
NLB_NAME="mi-nlb-produccion"
TARGET_GROUP_NAME_80="tg-tcp-80"
TARGET_GROUP_NAME_443="tg-tcp-443"

# IDs de tu infraestructura (¡REEMPLAZA ESTOS VALORES!)
VPC_ID="vpc-0123456789abcdef0"
SUBNET_ID_1="subnet-0123456789abcdef1" # Subred pública A
SUBNET_ID_2="subnet-0123456789abcdef2" # Subred pública B (en otra AZ)

# IDs de tus instancias
INSTANCE_ID_1="i-0123456789abcdef4"
INSTANCE_ID_2="i-0123456789abcdef5"

# NOTA: El ID del Grupo de Seguridad se aplica a las INSTANCIAS, no
# al NLB durante su creación. Asegúrate de que el grupo de seguridad
# de tus instancias (no esta variable) permita 80/443 desde 0.0.0.0/0.

echo "### 1. Creando Network Load Balancer..."
NLB_ARN=$(aws elbv2 create-load-balancer \
    --name $NLB_NAME \
    --type network \
    --subnets $SUBNET_ID_1 $SUBNET_ID_2 \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text)

if [ -z "$NLB_ARN" ]; then
    echo "Error al crear el NLB. Abortando."
    exit 1
fi
echo "NLB Creado: $NLB_ARN"

# -----------------------------------------------------------------

echo "### 2. Creando Target Group para TCP 80..."
# El health check se hará por HTTP en el puerto 80
TG_ARN_80=$(aws elbv2 create-target-group \
    --name $TARGET_GROUP_NAME_80 \
    --protocol TCP \
    --port 80 \
    --vpc-id $VPC_ID \
    --health-check-protocol HTTP \
    --health-check-port 80 \
    --health-check-path / \
    --target-type instance \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "Target Group (TCP 80) Creado: $TG_ARN_80"

# -----------------------------------------------------------------

echo "### 3. Creando Target Group para TCP 443..."
# El health check se hará por TCP en el puerto 443 (solo comprueba conexión)
TG_ARN_443=$(aws elbv2 create-target-group \
    --name $TARGET_GROUP_NAME_443 \
    --protocol TCP \
    --port 443 \
    --vpc-id $VPC_ID \
    --health-check-protocol TCP \
    --health-check-port 443 \
    --target-type instance \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "Target Group (TCP 443) Creado: $TG_ARN_443"

# -----------------------------------------------------------------

echo "### 4. Registrando Instancias en ambos Target Groups..."
aws elbv2 register-targets \
    --target-group-arn $TG_ARN_80 \
    --targets Id=$INSTANCE_ID_1 Id=$INSTANCE_ID_2
echo "Instancias registradas en $TARGET_GROUP_NAME_80"

aws elbv2 register-targets \
    --target-group-arn $TG_ARN_443 \
    --targets Id=$INSTANCE_ID_1 Id=$INSTANCE_ID_2
echo "Instancias registradas en $TARGET_GROUP_NAME_443"

# -----------------------------------------------------------------

echo "### 5. Creando Listener para TCP 80..."
aws elbv2 create-listener \
    --load-balancer-arn $NLB_ARN \
    --protocol TCP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN_80

echo "Listener TCP (80) creado."

# -----------------------------------------------------------------

echo "### 6. Creando Listener para TCP 443..."
aws elbv2 create-listener \
    --load-balancer-arn $NLB_ARN \
    --protocol TCP \
    --port 443 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN_443

echo "Listener TCP (443) creado."

# -----------------------------------------------------------------

echo "### 7. Obteniendo el DNS del Load Balancer..."
DNS_NAME=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $NLB_ARN \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

echo "---"
echo "✅ ¡PROCESO COMPLETADO!"
echo "El DNS de tu Network Load Balancer es:"
echo $DNS_NAME
echo "Recuerda: El NLB puede tardar unos minutos en estar 'active' y las instancias en pasar los 'health checks'."