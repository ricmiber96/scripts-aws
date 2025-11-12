#Creo la VPC y devuelvo su ID 
VPC_ID=$(aws ec2 create-vpc --cidr-block 172.16.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=entorno,Value=prueba}]' \
    --query Vpc.VpcId --output text)

#Muestro la ID de la VPC
echo $VPC_ID

#habilitar dns en la vpc
aws ec2 modify-vpc-attribute \
    --vpc-id $VPC_ID \
    --enable-dns-hostnames "{\"Value\":true}"

#Creamos la subred para la VPC 
SUB_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 172.16.0.0/20 \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=mi-subred1-ricardo}]' \
    --query Subnet.SubnetId --output text)

echo $SUB_ID

#Habilito la asignacion de ipv4 publica en la subred
#comprobar como NO se habilita y tenemos que hacerlo a posteriori
aws ec2 modify-subnet-attribute --subnet $SUB_ID --map-public-ip-on-launch

#creo el grupo de seguridad permitiendo ssh
SG_ID=$(aws ec2 create-security-group --vpc-id $VPC_ID \
 --group-name gsmio \
 --description "Mi grupo de seguridad para abrir el puerto 22" \
 --query GroupId \
 --output text)

 echo "Y ahora el grupo de seguridad"
 echo $SG_ID

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]'

aws ec2 create-tags \
    --resources $SG_ID \
    --tags "Key=Name,Value=migruposeguridad"

#creo un ec2
EC2_ID=$(aws ec2 run-instances \
    --image-id ami-0360c520857e3138f \
    --instance-type t3.micro \
    --key-name vockey \
    --subnet-id $SUB_ID \
    --security-group-ids $SG_ID \
    --associate-public-ip-address \
    --private-ip-address 172.16.0.100 \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=miec2}]' \
    --query Instances[0].InstanceId --output text)

echo "Esperando 15 segundos a que la instancia se cree..."
sleep 15

echo "Instancia EC2 Creada: $EC2_ID"

# Paso 1. Crear el IGW (Internet Gateway)
aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=MyIGW}]'

# Adjuntar el IGW a la VPC
aws ec2 attach-internet-gateway \
  --internet-gateway-id igw-0123456789abcdef0 \
  --vpc-id $VPC_ID

# Paso 3. Crear una tabla de enrutamiento
aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=Public-RT}]'
  

# Paso 4. Agregar una ruta para la salida a Internet
aws ec2 create-route \
  --route-table-id rtb-0123456789abcdef0 \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id igw-0123456789abcdef0


# Paso 5. Asociar la tabla de enrutamiento a una subred
aws ec2 associate-route-table \
  --route-table-id rtb-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0