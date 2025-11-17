#!/bin/bash

# Script para implementar Blue-Green Deployment en AWS Elastic Beanstalk
# Requiere: AWS CLI configurado con credenciales apropiadas

set -e

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

APP_NAME="mi-aplicacion-php"
REGION="us-east-1"
BLUE_ENV="app-blue-env"
GREEN_ENV="app-green-env"
S3_BUCKET="mi-bucket-deployments-${RANDOM}"
PLATFORM="php-8.2"  # Ajustar según versión necesaria

# Rutas locales de las aplicaciones
BLUE_APP_DIR="./blue-app"
GREEN_APP_DIR="./green-app"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCIONES
# ============================================================================

log() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

# Obtener el solution stack más reciente para PHP
get_php_solution_stack() {
    log "Obteniendo solution stack de PHP disponible..."
    
    # Obtener la lista y guardar en archivo temporal
    local temp_file=$(mktemp)
    aws elasticbeanstalk list-available-solution-stacks \
        --region "$REGION" \
        --output json > "$temp_file" 2>/dev/null
    
    # Extraer el primer stack de PHP usando grep, sed y head
    local php_stack=$(grep -o '"[^"]*PHP[^"]*"' "$temp_file" | \
        grep "Amazon Linux" | \
        grep "running PHP" | \
        head -n 1 | \
        sed 's/"//g' | \
        tr -d '\r\n\t' | \
        sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | \
        tr -cd '[:print:]')
    
    rm -f "$temp_file"
    
    if [ -z "$php_stack" ]; then
        error "No se encontró un solution stack de PHP disponible"
    fi
    
    # Debug: mostrar longitud y caracteres
    log "DEBUG - Longitud del stack: ${#php_stack}"
    log "DEBUG - Primeros 20 caracteres (hex): $(echo -n "$php_stack" | head -c 20 | od -A n -t x1)" >&2
    success "Solution stack encontrado: $php_stack" >&2
    echo "$php_stack"
}

# Verificar prerequisitos
check_prerequisites() {
    log "Verificando prerequisitos..."
    
    if ! command -v aws &> /dev/null; then
        error "AWS CLI no está instalado"
    fi
    
    if ! command -v zip &> /dev/null; then
        error "zip no está instalado"
    fi
    
    if [ ! -d "$BLUE_APP_DIR" ]; then
        error "Directorio $BLUE_APP_DIR no existe"
    fi
    
    if [ ! -d "$GREEN_APP_DIR" ]; then
        error "Directorio $GREEN_APP_DIR no existe"
    fi
    
    success "Prerequisitos verificados"
}

# Crear bucket S3
create_s3_bucket() {
    log "Creando bucket S3: $S3_BUCKET..."
    
    if aws s3 ls "s3://$S3_BUCKET" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://$S3_BUCKET" --region "$REGION" || error "No se pudo crear el bucket"
        success "Bucket S3 creado"
    else
        warning "Bucket S3 ya existe"
    fi
}

# Crear aplicación en Elastic Beanstalk
create_application() {
    log "Creando aplicación Elastic Beanstalk: $APP_NAME..."
    
    if ! aws elasticbeanstalk describe-applications \
        --application-names "$APP_NAME" \
        --region "$REGION" 2>&1 | grep -q "$APP_NAME"; then
        
        aws elasticbeanstalk create-application \
            --application-name "$APP_NAME" \
            --description "Aplicación PHP con Blue-Green Deployment" \
            --region "$REGION" || error "No se pudo crear la aplicación"
        
        success "Aplicación creada"
    else
        warning "Aplicación ya existe"
    fi
}

# Empaquetar aplicación
package_application() {
    local app_dir=$1
    local zip_name=$2
    
    log "Empaquetando aplicación desde $app_dir..."
    
    cd "$app_dir"
    zip -r "../$zip_name" . -x "*.git*" || error "No se pudo empaquetar la aplicación"
    cd - > /dev/null
    
    success "Aplicación empaquetada: $zip_name"
}

# Subir aplicación a S3
upload_to_s3() {
    local zip_file=$1
    local s3_key=$2
    
    log "Subiendo $zip_file a S3..."
    
    aws s3 cp "$zip_file" "s3://$S3_BUCKET/$s3_key" --region "$REGION" \
        || error "No se pudo subir a S3"
    
    success "Archivo subido a S3"
}

# Crear versión de aplicación
create_app_version() {
    local version_label=$1
    local s3_key=$2
    
    log "Creando versión de aplicación: $version_label..."
    
    aws elasticbeanstalk create-application-version \
        --application-name "$APP_NAME" \
        --version-label "$version_label" \
        --source-bundle S3Bucket="$S3_BUCKET",S3Key="$s3_key" \
        --region "$REGION" || error "No se pudo crear la versión"
    
    success "Versión creada: $version_label"
}

# Crear entorno
create_environment() {
    local env_name=$1
    local version_label=$2
    local cname_prefix=$3
    local solution_stack=$4
    
    log "Creando entorno: $env_name..."
    
    # Verificar si el entorno ya existe
    if aws elasticbeanstalk describe-environments \
        --application-name "$APP_NAME" \
        --environment-names "$env_name" \
        --region "$REGION" 2>&1 | grep -q "$env_name"; then
        warning "Entorno $env_name ya existe"
        return 0
    fi
    
    # Debug: verificar el solution stack antes de usarlo
    log "DEBUG - Solution stack a usar: '$solution_stack'"
    log "DEBUG - Longitud: ${#solution_stack} caracteres"
    
    # Limpiar el solution stack una vez más antes de usarlo
    solution_stack=$(echo "$solution_stack" | tr -cd '[:print:]' | xargs)
    
    log "DEBUG - Solution stack limpio: '$solution_stack'"
    
    aws elasticbeanstalk create-environment \
        --application-name "$APP_NAME" \
        --environment-name "$env_name" \
        --cname-prefix "$cname_prefix" \
        --version-label "$version_label" \
        --solution-stack-name "$solution_stack" \
        --option-settings \
            Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t2.micro \
            Namespace=aws:elasticbeanstalk:environment,OptionName=EnvironmentType,Value=SingleInstance \
            Namespace=aws:autoscaling:launchconfiguration,OptionName=IamInstanceProfile,Value=LabInstanceProfile \
            Namespace=aws:autoscaling:launchconfiguration,OptionName=EC2KeyName,Value=vockey \
        --region "$REGION" || error "No se pudo crear el entorno"
    
    success "Entorno $env_name creado"
}

# Esperar a que el entorno esté listo
wait_for_environment() {
    local env_name=$1
    
    log "Esperando a que el entorno $env_name esté listo (usando 'aws wait environment-ready')..."
    
    # 'aws wait' sondeará automáticamente.
    # Saldrá con éxito (código 0) si el estado es 'Ready'.
    # Saldrá con error (código 255) si el estado es 'Failed', 'Terminated', etc.
    # 'set -e' se encargará de detener el script si el waiter falla.
    
    aws elasticbeanstalk wait environment-exists \
        --application-name "$APP_NAME" \
        --environment-names "$env_name" \
        --region "$REGION" \
        || error "El entorno $env_name falló al lanzarse. Revisa los logs en la consola de Elastic Beanstalk."
    
    # Si llegamos aquí, el waiter tuvo éxito.
    success "Entorno $env_name está listo"
}

# Intercambiar URLs (Blue-Green swap)
swap_environment_urls() {
    local source_env=$1
    local dest_env=$2
    
    log "Intercambiando URLs entre $source_env y $dest_env..."
    
    aws elasticbeanstalk swap-environment-cnames \
        --source-environment-name "$source_env" \
        --destination-environment-name "$dest_env" \
        --region "$REGION" || error "No se pudo intercambiar las URLs"
    
    success "URLs intercambiadas exitosamente"
}

# Obtener URL del entorno
get_environment_url() {
    local env_name=$1
    
    local url=$(aws elasticbeanstalk describe-environments \
        --application-name "$APP_NAME" \
        --environment-names "$env_name" \
        --region "$REGION" \
        --query 'Environments[0].CNAME' \
        --output text)
    
    echo "$url"
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    log "Iniciando despliegue Blue-Green..."
    
    # 1. Verificar prerequisitos
    check_prerequisites
    
    # 2. Crear bucket S3
    create_s3_bucket
    
    # 3. Crear aplicación
    create_application
    
    # 4. Obtener solution stack de PHP
    PHP_SOLUTION_STACK=$(get_php_solution_stack)
    
    # 5. Preparar versión BLUE
    log "========== DESPLEGANDO ENTORNO BLUE =========="
    BLUE_ZIP="blue-app.zip"
    BLUE_VERSION="blue-v$(date +%Y%m%d-%H%M%S)"
    
    package_application "$BLUE_APP_DIR" "$BLUE_ZIP"
    upload_to_s3 "$BLUE_ZIP" "$BLUE_ZIP"
    create_app_version "$BLUE_VERSION" "$BLUE_ZIP"
    create_environment "$BLUE_ENV" "$BLUE_VERSION" "${APP_NAME}-blue" "$PHP_SOLUTION_STACK"
    wait_for_environment "$BLUE_ENV"
    
    BLUE_URL=$(get_environment_url "$BLUE_ENV")
    success "Entorno BLUE disponible en: http://$BLUE_URL"
    
    # 6. Preparar versión GREEN
    log "========== DESPLEGANDO ENTORNO GREEN =========="
    GREEN_ZIP="green-app.zip"
    GREEN_VERSION="green-v$(date +%Y%m%d-%H%M%S)"
    
    package_application "$GREEN_APP_DIR" "$GREEN_ZIP"
    upload_to_s3 "$GREEN_ZIP" "$GREEN_ZIP"
    create_app_version "$GREEN_VERSION" "$GREEN_ZIP"
    create_environment "$GREEN_ENV" "$GREEN_VERSION" "${APP_NAME}-green" "$PHP_SOLUTION_STACK"
    wait_for_environment "$GREEN_ENV"
    
    GREEN_URL=$(get_environment_url "$GREEN_ENV")
    success "Entorno GREEN disponible en: http://$GREEN_URL"
    
    # 7. Mostrar información
    echo ""
    log "=========================================="
    log "DESPLIEGUE COMPLETADO"
    log "=========================================="
    log "Entorno BLUE:  http://$BLUE_URL"
    log "Entorno GREEN: http://$GREEN_URL"
    log "Solution Stack: $PHP_SOLUTION_STACK"
    echo ""
    log "Para intercambiar los entornos (hacer que GREEN sea producción):"
    log "  ./$(basename $0) swap"
    echo ""
    
    # Limpiar archivos zip locales
    rm -f "$BLUE_ZIP" "$GREEN_ZIP"
}

# Función para intercambiar entornos
swap_environments() {
    log "========== INTERCAMBIANDO ENTORNOS =========="
    
    swap_environment_urls "$BLUE_ENV" "$GREEN_ENV"
    
    log "Esperando a que el intercambio se complete..."
    sleep 10
    
    BLUE_URL=$(get_environment_url "$BLUE_ENV")
    GREEN_URL=$(get_environment_url "$GREEN_ENV")
    
    success "Intercambio completado"
    log "Nuevo estado:"
    log "  Entorno BLUE:  http://$BLUE_URL"
    log "  Entorno GREEN: http://$GREEN_URL"
}

# Manejar argumentos
case "${1:-}" in
    swap)
        swap_environments
        ;;
    *)
        main
        ;;
esac