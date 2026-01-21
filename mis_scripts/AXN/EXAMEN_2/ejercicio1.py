import boto3
import time
import os

# --- CONFIGURACIÓN ---
REGION = 'us-east-1'
VPC_CIDR = '15.0.0.0/20'  # Rango solicitado
SUBNETS_INFO = {
    'Frontend': {'cidr': '15.0.1.0/24', 'public': True},
    'Backend':  {'cidr': '15.0.2.0/24', 'public': False},
    'Database': {'cidr': '15.0.3.0/24', 'public': False}
}
AMI_ID = 'ami-0e2c8caa4b6378d8c' # Ubuntu 24.04 LTS en us-east-1 (Verificar si cambia)
KEY_NAME = 'vockey'  # Nombre de la clave SSH (Usando la de AWS Academy por defecto)

ec2 = boto3.client('ec2', region_name=REGION)

def create_3tier_architecture():
    print(f"--- INICIANDO DESPLIEGUE EN {REGION} ---")

    # 1. Crear VPC
    print(f"Creando VPC {VPC_CIDR}...")
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR, TagSpecifications=[{'ResourceType': 'vpc', 'Tags': [{'Key': 'Name', 'Value': 'VPC-3Capas'}]}])
    vpc_id = vpc['Vpc']['VpcId']
    ec2.get_waiter('vpc_available').wait(VpcIds=[vpc_id])
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    print(f"-> VPC ID: {vpc_id}")

    # 2. Internet Gateway
    print("Creando Internet Gateway...")
    igw = ec2.create_internet_gateway(TagSpecifications=[{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'Name', 'Value': 'IGW-3Capas'}]}])
    igw_id = igw['InternetGateway']['InternetGatewayId']
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

    # 3. Subredes
    print("Creando Subredes...")
    subnets = {}
    for name, info in SUBNETS_INFO.items():
        sn = ec2.create_subnet(
            VpcId=vpc_id, 
            CidrBlock=info['cidr'],
            AvailabilityZone=f"{REGION}a",
            TagSpecifications=[{'ResourceType': 'subnet', 'Tags': [{'Key': 'Name', 'Value': f'Subnet-{name}'}]}]
        )
        sn_id = sn['Subnet']['SubnetId']
        subnets[name] = sn_id
        
        if info['public']:
            ec2.modify_subnet_attribute(SubnetId=sn_id, MapPublicIpOnLaunch={'Value': True})
            print(f"-> Subred {name} ({info['cidr']}) creada [PÚBLICA]: {sn_id}")
        else:
            print(f"-> Subred {name} ({info['cidr']}) creada [PRIVADA]: {sn_id}")

    # 4. NAT Gateway (Para que Backend/DB salgan a internet)
    print("Configurando NAT Gateway (Esto tarda unos minutos)...")
    eip = ec2.allocate_address(Domain='vpc')
    nat_gw = ec2.create_nat_gateway(
        SubnetId=subnets['Frontend'], # El NAT vive en la pública
        AllocationId=eip['AllocationId'],
        TagSpecifications=[{'ResourceType': 'natgateway', 'Tags': [{'Key': 'Name', 'Value': 'NAT-GW-3Capas'}]}]
    )
    nat_gw_id = nat_gw['NatGateway']['NatGatewayId']
    
    # Esperar a que el NAT esté disponible
    print(f"-> Esperando disponibilidad del NAT {nat_gw_id}...")
    ec2.get_waiter('nat_gateway_available').wait(NatGatewayIds=[nat_gw_id])
    print("-> NAT Gateway Listo.")

    # 5. Tablas de Rutas
    print("Configurando Tablas de Rutas...")
    
    # 5.1 Tabla Pública
    rt_pub = ec2.create_route_table(VpcId=vpc_id, TagSpecifications=[{'ResourceType': 'route-table', 'Tags': [{'Key': 'Name', 'Value': 'RT-Publica'}]}])
    rt_pub_id = rt_pub['RouteTable']['RouteTableId']
    ec2.create_route(RouteTableId=rt_pub_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
    ec2.associate_route_table(RouteTableId=rt_pub_id, SubnetId=subnets['Frontend'])
    
    # 5.2 Tabla Privada
    rt_priv = ec2.create_route_table(VpcId=vpc_id, TagSpecifications=[{'ResourceType': 'route-table', 'Tags': [{'Key': 'Name', 'Value': 'RT-Privada'}]}])
    rt_priv_id = rt_priv['RouteTable']['RouteTableId']
    ec2.create_route(RouteTableId=rt_priv_id, DestinationCidrBlock='0.0.0.0/0', NatGatewayId=nat_gw_id)
    # Asociar Backend y DB a la tabla privada
    ec2.associate_route_table(RouteTableId=rt_priv_id, SubnetId=subnets['Backend'])
    ec2.associate_route_table(RouteTableId=rt_priv_id, SubnetId=subnets['Database'])

    # 6. Grupos de Seguridad (Security Groups)
    print("Configurando Security Groups...")
    
    # SG Frontend: SSH y HTTP desde cualquier lugar
    sg_front = ec2.create_security_group(GroupName='SG-Frontend', Description='Frontend Access', VpcId=vpc_id)
    sg_front_id = sg_front['GroupId']
    ec2.authorize_security_group_ingress(GroupId=sg_front_id, IpProtocol='tcp', FromPort=22, ToPort=22, CidrIp='0.0.0.0/0')
    ec2.authorize_security_group_ingress(GroupId=sg_front_id, IpProtocol='tcp', FromPort=80, ToPort=80, CidrIp='0.0.0.0/0')
    
    # SG Backend: SSH y Tráfico App SOLO desde Frontend
    sg_back = ec2.create_security_group(GroupName='SG-Backend', Description='Backend Access', VpcId=vpc_id)
    sg_back_id = sg_back['GroupId']
    ec2.authorize_security_group_ingress(GroupId=sg_back_id, IpPermissions=[
        {'IpProtocol': '-1', 'UserIdGroupPairs': [{'GroupId': sg_front_id}]}
    ])
    
    # SG DB: Tráfico SOLO desde Backend
    sg_db = ec2.create_security_group(GroupName='SG-Database', Description='DB Access', VpcId=vpc_id)
    sg_db_id = sg_db['GroupId']
    ec2.authorize_security_group_ingress(GroupId=sg_db_id, IpPermissions=[
        {'IpProtocol': '-1', 'UserIdGroupPairs': [{'GroupId': sg_back_id}]}
    ])

    print("-> Reglas de Seguridad aplicadas.")

    # 7. Lanzar Instancias para probar
    print("Lanzando Instancias de prueba...")
    
    # Instancia Frontend (Bastión)
    instance_fe = ec2.run_instances(
        ImageId=AMI_ID, InstanceType='t2.micro', KeyName=KEY_NAME, MinCount=1, MaxCount=1,
        NetworkInterfaces=[{'SubnetId': subnets['Frontend'], 'DeviceIndex': 0, 'AssociatePublicIpAddress': True, 'Groups': [sg_front_id]}],
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'Srv-Frontend'}]}]
    )
    fe_id = instance_fe['Instances'][0]['InstanceId']
    
    # Instancia Backend (Privada)
    instance_be = ec2.run_instances(
        ImageId=AMI_ID, InstanceType='t2.micro', KeyName=KEY_NAME, MinCount=1, MaxCount=1,
        NetworkInterfaces=[{'SubnetId': subnets['Backend'], 'DeviceIndex': 0, 'AssociatePublicIpAddress': False, 'Groups': [sg_back_id]}],
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'Srv-Backend'}]}]
    )
    be_id = instance_be['Instances'][0]['InstanceId']

    print("Esperando a que las instancias estén corriendo...")
    ec2.get_waiter('instance_running').wait(InstanceIds=[fe_id, be_id])
    
    # Obtener IPs
    fe_info = ec2.describe_instances(InstanceIds=[fe_id])['Reservations'][0]['Instances'][0]
    be_info = ec2.describe_instances(InstanceIds=[be_id])['Reservations'][0]['Instances'][0]

    print("\n--- DESPLIEGUE FINALIZADO ---")
    print(f"Frontend IP Pública: {fe_info.get('PublicIpAddress')}")
    print(f"Backend IP Privada: {be_info.get('PrivateIpAddress')}")
    print("\nINSTRUCCIONES PARA LA PRUEBA:")
    print(f"1. Conéctate al Frontend: ssh -i {KEY_NAME}.pem -A ubuntu@{fe_info.get('PublicIpAddress')}")
    print(f"2. Desde el Frontend, salta al Backend: ssh ubuntu@{be_info.get('PrivateIpAddress')}")
    print("3. Ejecuta en el Backend: sudo apt-get update")

if __name__ == '__main__':
    create_3tier_architecture()