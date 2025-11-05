#Creo la VPC y devuelvo su ID 
VPC_ID=$(aws ec2 create-vpc --cidr-block 192.168.0.0/24 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=VPCRicardo}]' \
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
    --cidr-block 192.168.0.0/28 \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=mi-subred1-ricardo}]' \
    --query Subnet.SubnetId --output text)

echo $SUB_ID

#Habilito la asignacion de ipv4 publica en la subred
#comprobar como NO se habilita y tenemos que hacerlo a posteriori
aws ec2 modify-subnet-attribute --subnet $SUB_ID --map-public-ip-on-launch

#Creo el grupo de seguridad con el puerto 22 abierto (SSH)
SG_ID=$(aws ec2 create-security-group --vpc-id $VPC_ID \
    --group-name gsmio \
    --description "Mi grupo de seguridad para abrir el puerto 22 (SSH)" \
    --vpc-id $VPC_ID \
    --query GroupId --output text)

echo $SG_ID 

# Dos versiones distintas para crear reglas de grupos de seguridad
    # --protocol tcp \
    # --port 22 \
    # --cidr 0.0.0.0/0 > /dev/null/
    --ip-permissions '[{"IpProtocol":"tcp","FromPort":22,"ToPort":22,"IpRanges": [{"CidrIp":"0.0.0.0/0","Description":"Allow SSH"}]}]'

# Añadimos reglas de entradas 
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --ip-permissions '[{"IpProtocol":"tcp","FromPort":22,"ToPort":22,"IpRanges": [{"CidrIp":"0.0.0.0/0","Description":"Allow SSH"}]}]'



#Creamos una instancia EC2
EC2_ID=$(aws ec2 run-instances \
    --image-id ami-0360c520857e3138f \
    --instance-type t2.micro \
    --key-name vockey \
    --subnet-id $SUB_ID \
    --associate-public-ip-address \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=miec2}]' \
    --query Instances.InstanceId --output text)

# Esperamos 5000ms para mostrar el ID de la instancia EC2
sleep 15
echo $EC2_ID






