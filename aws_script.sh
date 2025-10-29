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

