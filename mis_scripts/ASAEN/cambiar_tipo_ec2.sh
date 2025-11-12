#!/bin/bash

# --- Variables de Entrada ---
INSTANCE_ID=$1
NEW_INSTANCE_TYPE=$2

# Colores para la salida
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

## --- Función de Uso y Validación ---
usage() {
    echo -e "${YELLOW}Uso: $0 <ID_de_Instancia> <Nuevo_Tipo_de_Instancia>${NC}"
    echo "Ejemplo: $0 i-0abcdef1234567890 t2.large"
    exit 1
}

if [ -z "$INSTANCE_ID" ] || [ -z "$NEW_INSTANCE_TYPE" ]; then
    usage
fi

echo -e "${YELLOW}--- Inicio del Proceso de Cambio de Tipo ---${NC}"
echo -e "Instancia ID: ${INSTANCE_ID}"
echo -e "Nuevo Tipo: ${NEW_INSTANCE_TYPE}"

# --- 1. Comprobar que la instancia existe y obtener su estado ---
echo -e "\n${GREEN}[1/6] Comprobando existencia y estado de la instancia...${NC}"

CURRENT_STATE=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query "Reservations[0].Instances[0].State.Name" \
    --output text 2>/dev/null)

if [ "$?" -ne 0 ] || [ "$CURRENT_STATE" == "None" ] || [ -z "$CURRENT_STATE" ]; then
    echo -e "${RED}Error: La instancia con ID ${INSTANCE_ID} no existe o no se pudo acceder.${NC}"
    exit 1
fi

echo -e "Estado actual de la instancia: ${CURRENT_STATE}"

# --- 2. Si la instancia está en ejecución, parar la instancia ---
if [ "$CURRENT_STATE" == "running" ]; then
    echo -e "\n${GREEN}[2/6] La instancia está en ejecución. Deteniendo instancia...${NC}"
    aws ec2 stop-instances --instance-ids "$INSTANCE_ID"
elif [ "$CURRENT_STATE" == "stopped" ]; then
    echo -e "\n${GREEN}[2/6] La instancia ya está detenida. Saltando paso de detención.${NC}"
elif [ "$CURRENT_STATE" == "stopping" ] || [ "$CURRENT_STATE" == "pending" ] || [ "$CURRENT_STATE" == "shutting-down" ]; then
    echo -e "\n${YELLOW}La instancia está en un estado transitorio (${CURRENT_STATE}). Esperando a que termine...${NC}"
else
    echo -e "\n${RED}Error: La instancia está en un estado inesperado (${CURRENT_STATE}). Abortando.${NC}"
    exit 1
fi

# --- 3. Esperar a que la instancia esté detenida (stopped) ---
if [ "$CURRENT_STATE" != "stopped" ]; then
    echo -e "\n${GREEN}[3/6] Esperando a que la instancia se detenga (stopped)...${NC}"
    aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID"
    if [ "$?" -ne 0 ]; then
        echo -e "${RED}Error: El tiempo de espera para la detención ha expirado o falló.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Instancia detenida.${NC}"
fi

# Obtenemos el tamaño de la instancia actual 
CURRENT_TYPE=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query "Reservations[0].Instances[0].InstanceType" \
    --output text 2>/dev/null)

if [ -z "$CURRENT_TYPE" ]; then
    echo "Error: No se pudo obtener el tipo de instancia para $INSTANCE_ID. Verifique el ID."
fi

# --- 4. Cambiar el tipo de la instancia al nuevo tipo ---
echo -e "\n${GREEN}[4/6] Cambiando tipo de instancia de ${CURRENT_TYPE} a ${NEW_INSTANCE_TYPE}...${NC}"

aws ec2 modify-instance-attribute \
    --instance-id "$INSTANCE_ID" \
    --instance-type "{\"Value\": \"$NEW_INSTANCE_TYPE\"}"

if [ "$?" -ne 0 ]; then
    echo -e "${RED}Error: No se pudo cambiar el tipo de instancia. Verifica que el tipo sea válido y que la AMI lo soporte.${NC}"
    exit 1
fi

echo -e "${GREEN}Tipo de instancia cambiado exitosamente a ${NEW_INSTANCE_TYPE}.${NC}"

# --- 5. Arrancar la instancia ---
echo -e "\n${GREEN}[5/6] Arrancando instancia...${NC}"

aws ec2 start-instances --instance-ids "$INSTANCE_ID"

# --- 6. Esperar hasta que esté arrancada (running) ---
echo -e "\n${GREEN}[6/6] Esperando a que la instancia esté en ejecución (running)...${NC}"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

if [ "$?" -ne 0 ]; then
    echo -e "${RED}Error: El tiempo de espera para el arranque ha expirado o falló.${NC}"
    exit 1
fi

echo -e "${GREEN}--- Proceso Completado ---${NC}"
echo -e "${GREEN}La instancia ${INSTANCE_ID} está ahora en ejecución y es de tipo ${NEW_INSTANCE_TYPE}.${NC}"