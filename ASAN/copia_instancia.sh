#!/bin/bash
# ===============================================================
# Script: copy-launch-ec2.sh
# Descripción:
#   1. Lanza una instancia EC2 en REGION_ORIGEN
#   2. Crea una AMI a partir de esa instancia
#   3. Copia la AMI a REGION_DESTINO
#   4. Crea un par de claves en la región destino
#   5. Lanza una instancia desde la AMI copiada
# ===============================================================

set -e  # detener si hay errores

# ========= CONFIGURACIÓN =========
REGION_ORIGEN="us-east-1"
REGION_DESTINO="eu-west-2"
INSTANCE_TYPE="t3.micro"
KEY_NAME_ORIGEN="clave-origen"
KEY_NAME_DESTINO="clave-destino"
AMI_NAME="mi-ami-transferida"
TAG_NAME="Instancia-Copiada"

# COMPROBAMOS SI RECOGEMOS LOS PARAMETROS DE ENTRADA
if [ "$#" -ne 3 ]; then
  echo "❌ Uso incorrecto."
  echo "➡️  Sintaxis: $0 <REGION_ORIGEN> <INSTANCE_ID_ORIGEN> <REGION_DESTINO>"
  exit 1
fi

REGION_ORIGEN="$1"
INSTANCE_ID="$2"
REGION_DESTINO="$3"


# ========= 1. LANZAR INSTANCIA EN LA REGIÓN ORIGEN =========
echo "🚀 Lanzando instancia en $REGION_ORIGEN..."

SG_ID_ORIG=$(aws ec2 describe-security-groups \
  --region $REGION_ORIGEN \
  --filters "Name=group-name,Values=default" \
  --query "SecurityGroups[0].GroupId" --output text)

SUBNET_ID_ORIG=$(aws ec2 describe-subnets \
  --region $REGION_ORIGEN \
  --query "Subnets[0].SubnetId" --output text)

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --count 1 \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME_ORIGEN \
  --security-group-ids $SG_ID_ORIG \
  --subnet-id $SUBNET_ID_ORIG \
  --region $REGION_ORIGEN \
  --query "Instances[0].InstanceId" --output text)

echo "✅ Instancia creada: $INSTANCE_ID"
echo "⏳ Esperando a que la instancia esté en estado 'running'..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION_ORIGEN

# ========= 2. CREAR AMI A PARTIR DE ESA INSTANCIA =========
echo "📸 Creando AMI desde la instancia..."
AMI_ID=$(aws ec2 create-image \
  --instance-id $INSTANCE_ID \
  --name "$AMI_NAME" \
  --description "AMI creada automáticamente" \
  --region $REGION_ORIGEN \
  --query "ImageId" --output text)

echo "✅ AMI creada: $AMI_ID"
echo "⏳ Esperando a que la AMI esté disponible..."
aws ec2 wait image-available --image-ids $AMI_ID --region $REGION_ORIGEN

# ========= 3. COPIAR AMI A LA REGIÓN DESTINO =========
echo "📦 Copiando AMI a $REGION_DESTINO..."
NEW_AMI_ID=$(aws ec2 copy-image \
  --source-region $REGION_ORIGEN \
  --source-image-id $AMI_ID \
  --region $REGION_DESTINO \
  --name "$AMI_NAME-copiada" \
  --query "ImageId" --output text)

echo "✅ AMI copiada a $REGION_DESTINO: $NEW_AMI_ID"
echo "⏳ Esperando a que la AMI copiada esté disponible..."
aws ec2 wait image-available --image-ids $NEW_AMI_ID --region $REGION_DESTINO

# ========= 4. CREAR KEY PAIR EN LA REGIÓN DESTINO =========
echo "🔑 Creando nuevo par de claves en $REGION_DESTINO..."
aws ec2 create-key-pair \
  --key-name $KEY_NAME_DESTINO \
  --region $REGION_DESTINO \
  --query 'KeyMaterial' \
  --output text > ${KEY_NAME_DESTINO}.pem

chmod 400 ${KEY_NAME_DESTINO}.pem
echo "✅ Clave creada: ${KEY_NAME_DESTINO}.pem"

# ========= 5. LANZAR INSTANCIA EN LA REGIÓN DESTINO =========
echo "🚀 Lanzando nueva instancia en $REGION_DESTINO desde la AMI copiada..."

SG_ID_DEST=$(aws ec2 describe-security-groups \
  --region $REGION_DESTINO \
  --filters "Name=group-name,Values=default" \
  --query "SecurityGroups[0].GroupId" --output text)

SUBNET_ID_DEST=$(aws ec2 describe-subnets \
  --region $REGION_DESTINO \
  --query "Subnets[0].SubnetId" --output text)

INSTANCE_ID_DEST=$(aws ec2 run-instances \
  --image-id $NEW_AMI_ID \
  --count 1 \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME_DESTINO \
  --security-group-ids $SG_ID_DEST \
  --subnet-id $SUBNET_ID_DEST \
  --region $REGION_DESTINO \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$TAG_NAME}]" \
  --query "Instances[0].InstanceId" --output text)

echo "✅ Instancia lanzada en $REGION_DESTINO: $INSTANCE_ID_DEST"
echo "⏳ Esperando a que la instancia esté en estado 'running'..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID_DEST --region $REGION_DESTINO

# ========= 6. MOSTRAR RESULTADOS =========
IP_PUBLICA=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID_DEST \
  --region $REGION_DESTINO \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)

echo "🌍 Instancia final disponible en $REGION_DESTINO"
echo "   ID: $INSTANCE_ID_DEST"
echo "   IP Pública: $IP_PUBLICA"
echo "   Conéctate con: ssh -i ${KEY_NAME_DESTINO}.pem ec2-user@$IP_PUBLICA"
