#!/usr/bin/env python3
import boto3

def ejercicio1_crear_vpc():
    """Ejercicio 1: Crear VPC con configuración básica"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 1: Creando VPC ===")
    
    # Crear VPC con CIDR 10.0.0.0/16
    print("Creando VPC...")
    vpc_response = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    print(f"VPC creada con ID: {vpc_id}")
    
    # Habilitar DNS Support y Hostnames
    print("Habilitando DNS Support...")
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    
    print("Habilitando DNS Hostnames...")
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    
    # Etiquetar VPC
    print("Etiquetando VPC...")
    ec2.create_tags(
        Resources=[vpc_id],
        Tags=[{'Key': 'Name', 'Value': 'Examen-VPC-Ricardo'}]
    )
    
    print(f"✅ VPC creada exitosamente: {vpc_id}\n")
    return vpc_id


def ejercicio2_crear_infraestructura(vpc_id):
    """Ejercicio 2: Crear 4 subredes distribuidas en 2 zonas de disponibilidad"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 2: Creando infraestructura de red ===")
    
    # Crear Subredes Públicas
    print("Creando Subred-Publica-1...")
    subnet_publica_1_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.0.1.0/24', AvailabilityZone='us-east-1a'
    )
    subnet_publica_1_id = subnet_publica_1_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_publica_1_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Publica-1-AZ-A'}])
    print(f"Subred-Publica-1 creada: {subnet_publica_1_id}")
    
    print("Creando Subred-Publica-2...")
    subnet_publica_2_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.0.2.0/24', AvailabilityZone='us-east-1b'
    )
    subnet_publica_2_id = subnet_publica_2_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_publica_2_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Publica-2-AZ-B'}])
    print(f"Subred-Publica-2 creada: {subnet_publica_2_id}")
    
    # Crear Subredes Privadas
    print("Creando Subred-Privada-1...")
    subnet_privada_1_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.0.3.0/24', AvailabilityZone='us-east-1a'
    )
    subnet_privada_1_id = subnet_privada_1_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_privada_1_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Privada-1-AZ-A'}])
    print(f"Subred-Privada-1 creada: {subnet_privada_1_id}")
    
    print("Creando Subred-Privada-2...")
    subnet_privada_2_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.0.4.0/24', AvailabilityZone='us-east-1b'
    )
    subnet_privada_2_id = subnet_privada_2_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_privada_2_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Privada-2-AZ-B'}])
    print(f"Subred-Privada-2 creada: {subnet_privada_2_id}")
    
    # Crear Internet Gateway
    print("Creando Internet Gateway...")
    igw_response = ec2.create_internet_gateway()
    igw_id = igw_response['InternetGateway']['InternetGatewayId']
    ec2.create_tags(Resources=[igw_id], Tags=[{'Key': 'Name', 'Value': 'Examen-IGW'}])
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    print(f"Internet Gateway creado y adjuntado: {igw_id}")
    
    # Configurar Enrutamiento para Subredes Públicas
    print("Configurando enrutamiento para subredes públicas...")
    route_table_response = ec2.create_route_table(VpcId=vpc_id)
    route_table_id = route_table_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[route_table_id], Tags=[{'Key': 'Name', 'Value': 'RT-Subredes-Publicas'}])
    ec2.create_route(RouteTableId=route_table_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
    ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_publica_1_id)
    ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_publica_2_id)
    print(f"Tabla de enrutamiento creada y asociada: {route_table_id}")
    
    # Crear NAT Gateway para Subred-Privada-2
    print("Creando NAT Gateway para Subred-Privada-2...")
    eip_2_response = ec2.allocate_address(Domain='vpc')
    allocation_2_id = eip_2_response['AllocationId']
    
    nat_2_response = ec2.create_nat_gateway(
        SubnetId=subnet_publica_2_id,
        AllocationId=allocation_2_id
    )
    nat_gateway_2_id = nat_2_response['NatGateway']['NatGatewayId']
    ec2.create_tags(Resources=[nat_gateway_2_id], Tags=[{'Key': 'Name', 'Value': 'Examen-NAT-GW-2'}])
    
    # Esperar a que esté disponible
    print("Esperando a que NAT Gateway 2 esté disponible...")
    waiter = ec2.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_gateway_2_id])
    
    # Crear tabla de enrutamiento para Subred-Privada-2
    rt_privada_2_response = ec2.create_route_table(VpcId=vpc_id)
    rt_privada_2_id = rt_privada_2_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[rt_privada_2_id], Tags=[{'Key': 'Name', 'Value': 'RT-Privada-2'}])
    ec2.create_route(RouteTableId=rt_privada_2_id, DestinationCidrBlock='0.0.0.0/0', NatGatewayId=nat_gateway_2_id)
    ec2.associate_route_table(RouteTableId=rt_privada_2_id, SubnetId=subnet_privada_2_id)
    print(f"NAT Gateway 2 y tabla de enrutamiento configurados: {nat_gateway_2_id}")
    
    print(f"✅ Infraestructura de red creada exitosamente!")
    return {
        'subnet_publica_1_id': subnet_publica_1_id,
        'subnet_publica_2_id': subnet_publica_2_id,
        'subnet_privada_1_id': subnet_privada_1_id,
        'subnet_privada_2_id': subnet_privada_2_id,
        'igw_id': igw_id,
        'route_table_id': route_table_id,
        'nat_gateway_2_id': nat_gateway_2_id,
        'allocation_2_id': allocation_2_id
    }

# def ejercicio2_crear_infraestructura_completa(vpc_id):
    """
    Ejercicio 2: Crear 4 subredes distribuidas en 2 zonas de disponibilidad 
    y configurar Internet Gateway (IGW) y NAT Gateway (NGW).
    """
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 2: Creando infraestructura de red COMPLETA ===")
    
    # 1. Crear Subredes (Ajustadas a 10.10.x.0/24)
    # ---
    
    # Subredes Públicas
    subnet_publica_1_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.10.1.0/24', AvailabilityZone='us-east-1a'
    )
    subnet_publica_1_id = subnet_publica_1_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_publica_1_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Publica-1 (AZ-A)'}])
    print(f"Subred-Publica-1 creada: {subnet_publica_1_id}")
    
    subnet_publica_2_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.10.2.0/24', AvailabilityZone='us-east-1b'
    )
    subnet_publica_2_id = subnet_publica_2_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_publica_2_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Publica-2 (AZ-B)'}])
    print(f"Subred-Publica-2 creada: {subnet_publica_2_id}")
    
    # Subredes Privadas
    subnet_privada_1_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.10.3.0/24', AvailabilityZone='us-east-1a'
    )
    subnet_privada_1_id = subnet_privada_1_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_privada_1_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Privada-1 (AZ-A)'}])
    print(f"Subred-Privada-1 creada: {subnet_privada_1_id}")
    
    subnet_privada_2_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.10.4.0/24', AvailabilityZone='us-east-1b'
    )
    subnet_privada_2_id = subnet_privada_2_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_privada_2_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Privada-2 (AZ-B)'}])
    print(f"Subred-Privada-2 creada: {subnet_privada_2_id}")

    # 2. Configuración de Internet Gateway (IGW)
    # ---
    print("Creando y adjuntando Internet Gateway...")
    igw_response = ec2.create_internet_gateway()
    igw_id = igw_response['InternetGateway']['InternetGatewayId']
    ec2.create_tags(Resources=[igw_id], Tags=[{'Key': 'Name', 'Value': 'Examen-IGW'}])
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    print(f"Internet Gateway creado y adjuntado: {igw_id}")
    
    # 3. Configuración de NAT Gateway (NGW)
    # ---
    
    # a. Asignar Elastic IP (EIP) para el NAT Gateway
    print("Asignando Elastic IP para NAT Gateway...")
    allocation_response = ec2.allocate_address(Domain='vpc')
    eip_allocation_id = allocation_response['AllocationId']
    print(f"Elastic IP asignada (Allocation ID): {eip_allocation_id}")
    
    # b. Crear NAT Gateway en la Subred Pública 1 (AZ-A)
    print("Creando NAT Gateway en Subred-Publica-1...")
    nat_response = ec2.create_nat_gateway(
        SubnetId=subnet_publica_1_id,
        AllocationId=eip_allocation_id
    )
    nat_gateway_id = nat_response['NatGateway']['NatGatewayId']
    ec2.create_tags(Resources=[nat_gateway_id], Tags=[{'Key': 'Name', 'Value': 'Examen-NAT-GW'}])
    print(f"NAT Gateway creado: {nat_gateway_id}. Esperando a que esté 'available'...")
    
    # ¡Importante! Esperar a que el NAT Gateway esté disponible antes de usarlo en la tabla de rutas
    waiter = ec2.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_gateway_id])
    print("NAT Gateway disponible.")

    # 4. Configuración de Tablas de Enrutamiento
    # ---

    # a. Tabla de Rutas Públicas
    print("Configurando enrutamiento para subredes públicas...")
    rt_publica_response = ec2.create_route_table(VpcId=vpc_id)
    rt_publica_id = rt_publica_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[rt_publica_id], Tags=[{'Key': 'Name', 'Value': 'RT-Subredes-Publicas'}])
    
    # Ruta por defecto a Internet Gateway
    ec2.create_route(RouteTableId=rt_publica_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
    
    # Asociación
    ec2.associate_route_table(RouteTableId=rt_publica_id, SubnetId=subnet_publica_1_id)
    ec2.associate_route_table(RouteTableId=rt_publica_id, SubnetId=subnet_publica_2_id)
    print(f"Tabla de Enrutamiento Pública creada y asociada: {rt_publica_id}")
    
    # b. Tabla de Rutas Privadas
    print("Configurando enrutamiento para subredes privadas...")
    rt_privada_response = ec2.create_route_table(VpcId=vpc_id)
    rt_privada_id = rt_privada_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[rt_privada_id], Tags=[{'Key': 'Name', 'Value': 'RT-Subredes-Privadas'}])
    
    # Ruta por defecto a NAT Gateway
    ec2.create_route(RouteTableId=rt_privada_id, DestinationCidrBlock='0.0.0.0/0', NatGatewayId=nat_gateway_id)
    
    # Asociación
    ec2.associate_route_table(RouteTableId=rt_privada_id, SubnetId=subnet_privada_1_id)
    ec2.associate_route_table(RouteTableId=rt_privada_id, SubnetId=subnet_privada_2_id)
    print(f"Tabla de Enrutamiento Privada creada y asociada: {rt_privada_id}")
    
    print(f"✅ Infraestructura de red creada EXITOSAMENTE! (VPC, IGW, NGW, 4 Subredes y Tablas de Ruta)")

    return {
        'subnet_publica_1_id': subnet_publica_1_id,
        'subnet_publica_2_id': subnet_publica_2_id,
        'subnet_privada_1_id': subnet_privada_1_id,
        'subnet_privada_2_id': subnet_privada_2_id,
        'igw_id': igw_id,
        'nat_gateway_id': nat_gateway_id,
        'rt_publica_id': rt_publica_id,
        'rt_privada_id': rt_privada_id
    }


def ejercicio3_nat(subnet_id):
    """Ejercicio 3: Crear NAT Gateway en la subred especificada"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 3: Creando NAT Gateway ===")
    
    # Crear IP Elástica
    print("Creando IP Elástica...")
    eip_response = ec2.allocate_address(Domain='vpc')
    allocation_id = eip_response['AllocationId']
    print(f"IP Elástica creada: {allocation_id}")
    
    # Crear NAT Gateway
    print("Creando NAT Gateway...")
    nat_response = ec2.create_nat_gateway(
        SubnetId=subnet_id,
        AllocationId=allocation_id
    )
    nat_gateway_id = nat_response['NatGateway']['NatGatewayId']
    print(f"NAT Gateway creado: {nat_gateway_id}")
    
    # Etiquetar NAT Gateway después de crearlo
    ec2.create_tags(Resources=[nat_gateway_id], Tags=[{'Key': 'Name', 'Value': 'Examen-NAT-GW'}])
    
    # Esperar a que esté disponible
    print("Esperando a que el NAT Gateway esté disponible...")
    waiter = ec2.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_gateway_id])
    
    print("✅ NAT Gateway creado exitosamente!")
    return {
        'nat_gateway_id': nat_gateway_id,
        'allocation_id': allocation_id
    }

def ejercicio4_tablas_enrutamiento(vpc_id, igw_id, nat_gateway_id, subnet_publica_1_id, subnet_publica_2_id, subnet_privada_1_id, subnet_privada_2_id):
    """Ejercicio 4: Crear 4 tablas de enrutamiento separadas"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 4: Creando tablas de enrutamiento ===")
    
    # Tabla para Subred Pública 1
    print("Creando tabla de enrutamiento para Subred-Publica-1...")
    rt_pub_1_response = ec2.create_route_table(VpcId=vpc_id)
    rt_pub_1_id = rt_pub_1_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[rt_pub_1_id], Tags=[{'Key': 'Name', 'Value': 'RT-Publica-1'}])
    ec2.create_route(RouteTableId=rt_pub_1_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
    ec2.associate_route_table(RouteTableId=rt_pub_1_id, SubnetId=subnet_publica_1_id)
    print(f"Tabla RT-Publica-1 creada: {rt_pub_1_id}")
    
    # Tabla para Subred Pública 2
    print("Creando tabla de enrutamiento para Subred-Publica-2...")
    rt_pub_2_response = ec2.create_route_table(VpcId=vpc_id)
    rt_pub_2_id = rt_pub_2_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[rt_pub_2_id], Tags=[{'Key': 'Name', 'Value': 'RT-Publica-2'}])
    ec2.create_route(RouteTableId=rt_pub_2_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
    ec2.associate_route_table(RouteTableId=rt_pub_2_id, SubnetId=subnet_publica_2_id)
    print(f"Tabla RT-Publica-2 creada: {rt_pub_2_id}")
    
    # Tabla para Subred Privada 1
    print("Creando tabla de enrutamiento para Subred-Privada-1...")
    rt_priv_1_response = ec2.create_route_table(VpcId=vpc_id)
    rt_priv_1_id = rt_priv_1_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[rt_priv_1_id], Tags=[{'Key': 'Name', 'Value': 'RT-Privada-1'}])
    ec2.create_route(RouteTableId=rt_priv_1_id, DestinationCidrBlock='0.0.0.0/0', NatGatewayId=nat_gateway_id)
    ec2.associate_route_table(RouteTableId=rt_priv_1_id, SubnetId=subnet_privada_1_id)
    print(f"Tabla RT-Privada-1 creada: {rt_priv_1_id}")
    
    # Tabla para Subred Privada 2
    print("Creando tabla de enrutamiento para Subred-Privada-2...")
    rt_priv_2_response = ec2.create_route_table(VpcId=vpc_id)
    rt_priv_2_id = rt_priv_2_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[rt_priv_2_id], Tags=[{'Key': 'Name', 'Value': 'RT-Privada-2'}])
    ec2.create_route(RouteTableId=rt_priv_2_id, DestinationCidrBlock='0.0.0.0/0', NatGatewayId=nat_gateway_id)
    ec2.associate_route_table(RouteTableId=rt_priv_2_id, SubnetId=subnet_privada_2_id)
    print(f"Tabla RT-Privada-2 creada: {rt_priv_2_id}")
    
    print("✅ Tablas de enrutamiento creadas exitosamente!")
    return {
        'rt_publica_1_id': rt_pub_1_id,
        'rt_publica_2_id': rt_pub_2_id,
        'rt_privada_1_id': rt_priv_1_id,
        'rt_privada_2_id': rt_priv_2_id
    }

def ejercicio5_instancias_ec2(vpc_id, subnet_publica_1_id, subnet_publica_2_id, subnet_privada_1_id, subnet_privada_2_id):
    """Ejercicio 5: Crear grupos de seguridad e instancias EC2 en cada subred"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 5: Creando grupos de seguridad e instancias ===")
    
    # Crear Security Groups para Subredes Públicas (Bastion)
    print("Creando Security Group GS-Bastion...")
    sg_bastion_response = ec2.create_security_group(
        GroupName='GS-Bastion',
        Description='Security Group para Bastion Hosts',
        VpcId=vpc_id
    )
    sg_bastion_id = sg_bastion_response['GroupId']
    ec2.create_tags(Resources=[sg_bastion_id], Tags=[{'Key': 'Name', 'Value': 'GS-Bastion'}])
    
    # Regla SSH para GS-Bastion
    ec2.authorize_security_group_ingress(
        GroupId=sg_bastion_id,
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
    )
    print(f"GS-Bastion creado: {sg_bastion_id}")
    
    # Crear Security Group para Subredes Privadas (App)
    print("Creando Security Group GS-App...")
    sg_app_response = ec2.create_security_group(
        GroupName='GS-App',
        Description='Security Group para App Servers',
        VpcId=vpc_id
    )
    sg_app_id = sg_app_response['GroupId']
    ec2.create_tags(Resources=[sg_app_id], Tags=[{'Key': 'Name', 'Value': 'GS-App'}])
    
    # Reglas para GS-App (SSH y ICMP solo desde GS-Bastion)
    ec2.authorize_security_group_ingress(
        GroupId=sg_app_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'UserIdGroupPairs': [{'GroupId': sg_bastion_id}]
            },
            {
                'IpProtocol': 'icmp',
                'FromPort': -1,
                'ToPort': -1,
                'UserIdGroupPairs': [{'GroupId': sg_bastion_id}]
            }
        ]
    )
    print(f"GS-App creado: {sg_app_id}")
    
    # Obtener AMI de Ubuntu
    print("Obteniendo AMI de Ubuntu...")
    images = ec2.describe_images(
        Filters=[
            {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
            {'Name': 'owner-id', 'Values': ['099720109477']}
        ],
        Owners=['099720109477']
    )
    ami_id = sorted(images['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]['ImageId']
    
    # Lanzar instancias Bastion en subredes públicas
    print("Lanzando Bastion-Host-1...")
    bastion_1_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        NetworkInterfaces=[{
            'SubnetId': subnet_publica_1_id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [sg_bastion_id]
        }],
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'Bastion-Host-1'}]
        }]
    )
    bastion_1_id = bastion_1_response['Instances'][0]['InstanceId']
    print(f"Bastion-Host-1 lanzado: {bastion_1_id}")
    
    print("Lanzando Bastion-Host-2...")
    bastion_2_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        NetworkInterfaces=[{
            'SubnetId': subnet_publica_2_id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [sg_bastion_id]
        }],
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'Bastion-Host-2'}]
        }]
    )
    bastion_2_id = bastion_2_response['Instances'][0]['InstanceId']
    print(f"Bastion-Host-2 lanzado: {bastion_2_id}")
    
    # Lanzar instancias App en subredes privadas
    print("Lanzando App-Server-1...")
    app_1_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        SecurityGroupIds=[sg_app_id],
        SubnetId=subnet_privada_1_id,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'App-Server-1'}]
        }]
    )
    app_1_id = app_1_response['Instances'][0]['InstanceId']
    print(f"App-Server-1 lanzado: {app_1_id}")
    
    print("Lanzando App-Server-2...")
    app_2_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        SecurityGroupIds=[sg_app_id],
        SubnetId=subnet_privada_2_id,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'App-Server-2'}]
        }]
    )
    app_2_id = app_2_response['Instances'][0]['InstanceId']
    print(f"App-Server-2 lanzado: {app_2_id}")
    
    print("✅ Instancias y grupos de seguridad creados exitosamente!")
    return {
        'sg_bastion_id': sg_bastion_id,
        'sg_app_id': sg_app_id,
        'bastion_1_id': bastion_1_id,
        'bastion_2_id': bastion_2_id,
        'app_1_id': app_1_id,
        'app_2_id': app_2_id
    }
def ejercicio6_nacl(vpc_id, subnet_publica_1_id, subnet_publica_2_id, subnet_privada_1_id, subnet_privada_2_id):
    """Ejercicio 6: Configurar ACLs específicas para subredes públicas y privadas"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 6: Configurando Network ACLs específicas ===")
    
    # NACL para Subredes Públicas (SSH e ICMP permitidos)
    print("Creando NACL para subredes públicas...")
    nacl_publica_response = ec2.create_network_acl(VpcId=vpc_id)
    nacl_publica_id = nacl_publica_response['NetworkAcl']['NetworkAclId']
    ec2.create_tags(Resources=[nacl_publica_id], Tags=[{'Key': 'Name', 'Value': 'NACL-Publica'}])
    
    # Reglas de entrada para NACL pública
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_publica_id, RuleNumber=100, Protocol='6',
        RuleAction='allow', PortRange={'From': 22, 'To': 22},
        CidrBlock='0.0.0.0/0', Egress=False
    )
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_publica_id, RuleNumber=110, Protocol='1',
        RuleAction='allow', IcmpTypeCode={'Type': -1, 'Code': -1},
        CidrBlock='0.0.0.0/0', Egress=False
    )
    
    # Reglas de salida para NACL pública
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_publica_id, RuleNumber=100, Protocol='6',
        RuleAction='allow', PortRange={'From': 1024, 'To': 65535},
        CidrBlock='0.0.0.0/0', Egress=True
    )
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_publica_id, RuleNumber=110, Protocol='1',
        RuleAction='allow', IcmpTypeCode={'Type': -1, 'Code': -1},
        CidrBlock='0.0.0.0/0', Egress=True
    )
    
    # NACL para Subredes Privadas (denegar tráfico externo)
    print("Creando NACL para subredes privadas...")
    nacl_privada_response = ec2.create_network_acl(VpcId=vpc_id)
    nacl_privada_id = nacl_privada_response['NetworkAcl']['NetworkAclId']
    ec2.create_tags(Resources=[nacl_privada_id], Tags=[{'Key': 'Name', 'Value': 'NACL-Privada'}])
    
    # Solo permitir tráfico interno de la VPC (10.0.0.0/16)
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_privada_id, RuleNumber=100, Protocol='6',
        RuleAction='allow', PortRange={'From': 22, 'To': 22},
        CidrBlock='10.0.0.0/16', Egress=False
    )
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_privada_id, RuleNumber=110, Protocol='1',
        RuleAction='allow', IcmpTypeCode={'Type': -1, 'Code': -1},
        CidrBlock='10.0.0.0/16', Egress=False
    )
    
    # Reglas de salida para subredes privadas
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_privada_id, RuleNumber=100, Protocol='6',
        RuleAction='allow', PortRange={'From': 1024, 'To': 65535},
        CidrBlock='0.0.0.0/0', Egress=True
    )
    
    # Asociar NACLs a subredes
    print("Asociando NACLs a subredes...")
    for subnet_id, nacl_id in [(subnet_publica_1_id, nacl_publica_id), (subnet_publica_2_id, nacl_publica_id),
                               (subnet_privada_1_id, nacl_privada_id), (subnet_privada_2_id, nacl_privada_id)]:
        try:
            nacls = ec2.describe_network_acls(Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}])
            if nacls['NetworkAcls'] and nacls['NetworkAcls'][0]['Associations']:
                current_association_id = nacls['NetworkAcls'][0]['Associations'][0]['NetworkAclAssociationId']
                ec2.replace_network_acl_association(AssociationId=current_association_id, NetworkAclId=nacl_id)
                print(f"NACL asociada a subred {subnet_id}")
            else:
                print(f"No se encontró asociación para subred {subnet_id}")
        except Exception as e:
            print(f"Error asociando NACL a subred {subnet_id}: {e}")
            continue
    
    print("✅ Network ACLs configuradas exitosamente!")
    return {'nacl_publica_id': nacl_publica_id, 'nacl_privada_id': nacl_privada_id}


def main():
    """Función principal que ejecuta todos los ejercicios dinámicamente"""
    recursos = {}
    
    # Ejercicio 1: Crear VPC
    print("\n" + "="*50)
    print("INICIANDO EJERCICIOS AWS")
    print("="*50)
    
    vpc_id = ejercicio1_crear_vpc()
    recursos['vpc_id'] = vpc_id
    
    # Ejercicio 2: Crear infraestructura de red
    recursos_red = ejercicio2_crear_infraestructura(vpc_id)
    recursos.update(recursos_red)
    
    # Ejercicio 3: Crear NAT Gateway
    recursos_nat = ejercicio3_nat(recursos['subnet_publica_1_id'])
    recursos.update(recursos_nat)
    
    # Ejercicio 4: Crear tablas de enrutamiento
    recursos_tablas = ejercicio4_tablas_enrutamiento(
        recursos['vpc_id'],
        recursos['igw_id'],
        recursos['nat_gateway_id'],
        recursos['subnet_publica_1_id'],
        recursos['subnet_publica_2_id'],
        recursos['subnet_privada_1_id'],
        recursos['subnet_privada_2_id']
    )
    recursos.update(recursos_tablas)
    
    # Ejercicio 5: Crear instancias EC2
    recursos_instancias = ejercicio5_instancias_ec2(
        recursos['vpc_id'],
        recursos['subnet_publica_1_id'],
        recursos['subnet_publica_2_id'],
        recursos['subnet_privada_1_id'],
        recursos['subnet_privada_2_id']
    )
    recursos.update(recursos_instancias)
    
    # Ejercicio 6: Configurar NACLs
    recursos_nacl = ejercicio6_nacl(
        recursos['vpc_id'],
        recursos['subnet_publica_1_id'],
        recursos['subnet_publica_2_id'],
        recursos['subnet_privada_1_id'],
        recursos['subnet_privada_2_id']
    )
    recursos.update(recursos_nacl)
    
    # Resumen final
    print("\n" + "="*50)
    print("RESUMEN FINAL")
    print("="*50)
    print(f"VPC ID: {recursos['vpc_id']}")
    print(f"NAT Gateway 1 ID: {recursos['nat_gateway_id']}")
    print(f"NAT Gateway 2 ID: {recursos['nat_gateway_2_id']}")
    print(f"Instancias creadas: 4 instancias EC2")
    print(f"NACLs configuradas: {len(recursos_nacl)} NACLs")
    print("✅ Todos los ejercicios completados exitosamente!")
    print("="*50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Ejecución interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()