#!/usr/bin/env python3
import boto3
import time

def get_ubuntu_ami(ec2_client):
    """Obtiene la AMI más reciente de Ubuntu 22.04 LTS"""
    response = ec2_client.describe_images(
        Filters=[
            {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
            {'Name': 'owner-id', 'Values': ['099720109477']},
            {'Name': 'state', 'Values': ['available']}
        ]
    )
    images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
    return images[0]['ImageId']

def create_vpc_infrastructure(region, vpc_configs):
    """Crea VPCs, subredes, IGW e instancias EC2 en una región"""
    ec2 = boto3.client('ec2', region_name=region)
    
    print(f"\n=== Creando VPCs en {region} ===")
    
    ubuntu_ami = get_ubuntu_ami(ec2)
    created_resources = []
    
    for config in vpc_configs:
        vpc_name = config['name']
        vpc_cidr = config['vpc_cidr']
        subnet_cidr = config['subnet_cidr']
        
        print(f"\n--- Creando {vpc_name} ---")
        
        # Crear VPC
        vpc_response = ec2.create_vpc(CidrBlock=vpc_cidr)
        vpc_id = vpc_response['Vpc']['VpcId']
        ec2.create_tags(Resources=[vpc_id], Tags=[{'Key': 'Name', 'Value': vpc_name}])
        
        # Habilitar DNS
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
        
        # Crear Internet Gateway
        igw_response = ec2.create_internet_gateway()
        igw_id = igw_response['InternetGateway']['InternetGatewayId']
        ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        ec2.create_tags(Resources=[igw_id], Tags=[{'Key': 'Name', 'Value': f'IGW-{vpc_name}'}])
        
        # Crear subred pública
        azs = ec2.describe_availability_zones(Filters=[{'Name': 'state', 'Values': ['available']}])
        az = azs['AvailabilityZones'][0]['ZoneName']
        
        subnet_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock=subnet_cidr, AvailabilityZone=az)
        subnet_id = subnet_response['Subnet']['SubnetId']
        ec2.create_tags(Resources=[subnet_id], Tags=[{'Key': 'Name', 'Value': f'Subnet-{vpc_name}'}])
        ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={'Value': True})
        
        # Configurar tabla de rutas
        route_tables = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        main_rt_id = route_tables['RouteTables'][0]['RouteTableId']
        ec2.create_route(RouteTableId=main_rt_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
        
        # Crear Security Group
        sg_response = ec2.create_security_group(
            GroupName=f'SG-{vpc_name}',
            Description=f'Security group for {vpc_name}',
            VpcId=vpc_id
        )
        sg_id = sg_response['GroupId']
        ec2.create_tags(Resources=[sg_id], Tags=[{'Key': 'Name', 'Value': f'SG-{vpc_name}'}])
        
        # Reglas de seguridad
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        
        # Crear instancia EC2
        print(f"Creando instancia en {vpc_name}...")
        instance_response = ec2.run_instances(
            ImageId=ubuntu_ami,
            MinCount=1,
            MaxCount=1,
            InstanceType='t3.micro',
            SubnetId=subnet_id,
            SecurityGroupIds=[sg_id],
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': f'Instance-{vpc_name}'}]
            }]
        )
        instance_id = instance_response['Instances'][0]['InstanceId']
        
        print(f"VPC: {vpc_id}, Subnet: {subnet_id}, Instance: {instance_id}")
        
        created_resources.append({
            'vpc_id': vpc_id,
            'subnet_id': subnet_id,
            'instance_id': instance_id,
            'igw_id': igw_id,
            'sg_id': sg_id,
            'route_table_id': main_rt_id,
            'vpc_cidr': vpc_cidr
        })
        
        time.sleep(10)
    
    return created_resources

def create_transit_gateway(region):
    """Crea Transit Gateway en Región 1"""
    ec2 = boto3.client('ec2', region_name=region)
    
    print(f"\n--- Creando Transit Gateway en {region} ---")
    
    tgw_response = ec2.create_transit_gateway(
        Description=f'Transit Gateway for {region}',
        Options={'AmazonSideAsn': 64512},
        TagSpecifications=[{
            'ResourceType': 'transit-gateway',
            'Tags': [{'Key': 'Name', 'Value': 'TGW-Region1'}]
        }]
    )
    tgw_id = tgw_response['TransitGateway']['TransitGatewayId']
    
    # Esperar a que esté disponible
    print(f"Esperando que TGW {tgw_id} esté disponible...")
    while True:
        response = ec2.describe_transit_gateways(TransitGatewayIds=[tgw_id])
        state = response['TransitGateways'][0]['State']
        if state == 'available':
            break
        time.sleep(10)
    
    print(f"Transit Gateway creado: {tgw_id}")
    return tgw_id

def attach_vpcs_to_tgw(region, tgw_id, vpc_resources):
    """Conecta las 2 VPCs de Región 1 al Transit Gateway"""
    ec2 = boto3.client('ec2', region_name=region)
    
    print(f"\n--- Conectando VPCs al TGW en {region} ---")
    
    attachments = []
    for resource in vpc_resources:
        vpc_id = resource['vpc_id']
        subnet_id = resource['subnet_id']
        
        attachment_response = ec2.create_transit_gateway_vpc_attachment(
            TransitGatewayId=tgw_id,
            VpcId=vpc_id,
            SubnetIds=[subnet_id],
            TagSpecifications=[{
                'ResourceType': 'transit-gateway-attachment',
                'Tags': [{'Key': 'Name', 'Value': f'TGW-Attachment-{vpc_id}'}]
            }]
        )
        attachment_id = attachment_response['TransitGatewayVpcAttachment']['TransitGatewayAttachmentId']
        attachments.append(attachment_id)
        
        print(f"VPC {vpc_id} conectada al TGW: {attachment_id}")
    
    # Esperar a que los attachments estén disponibles
    print("Esperando que los attachments estén disponibles...")
    for attachment_id in attachments:
        while True:
            response = ec2.describe_transit_gateway_vpc_attachments(TransitGatewayAttachmentIds=[attachment_id])
            state = response['TransitGatewayVpcAttachments'][0]['State']
            if state == 'available':
                break
            time.sleep(10)
    
    return attachments

def create_vpc_peering_connections(region1_resources, region2_resources):
    """Crea VPC Peering entre cada VPC de Región 1 y la VPC de Región 2"""
    ec2_region1 = boto3.client('ec2', region_name='us-east-1')
    ec2_region2 = boto3.client('ec2', region_name='us-west-2')
    
    print("\n--- Creando VPC Peering Connections ---")
    
    peering_connections = []
    region2_vpc = region2_resources[0]  # Solo hay 1 VPC en región 2
    
    for i, region1_vpc in enumerate(region1_resources):
        print(f"Creando peering entre {region1_vpc['vpc_id']} y {region2_vpc['vpc_id']}")
        
        # Crear peering connection
        peering_response = ec2_region1.create_vpc_peering_connection(
            VpcId=region1_vpc['vpc_id'],
            PeerVpcId=region2_vpc['vpc_id'],
            PeerRegion='us-west-2',
            TagSpecifications=[{
                'ResourceType': 'vpc-peering-connection',
                'Tags': [{'Key': 'Name', 'Value': f'Peering-R1VPC{i+1}-R2VPC'}]
            }]
        )
        peering_id = peering_response['VpcPeeringConnection']['VpcPeeringConnectionId']
        
        # Esperar a que esté en estado pendingAcceptance
        while True:
            response = ec2_region1.describe_vpc_peering_connections(VpcPeeringConnectionIds=[peering_id])
            state = response['VpcPeeringConnections'][0]['Status']['Code']
            if state == 'pending-acceptance':
                break
            time.sleep(5)
        
        # Aceptar desde región 2
        print(f"Aceptando peering {peering_id} desde región 2...")
        ec2_region2.accept_vpc_peering_connection(VpcPeeringConnectionId=peering_id)
        
        # Esperar a que esté activo
        while True:
            response = ec2_region1.describe_vpc_peering_connections(VpcPeeringConnectionIds=[peering_id])
            state = response['VpcPeeringConnections'][0]['Status']['Code']
            if state == 'active':
                break
            time.sleep(10)
        
        peering_connections.append({
            'peering_id': peering_id,
            'region1_vpc': region1_vpc,
            'region2_vpc': region2_vpc
        })
        
        print(f"Peering {peering_id} activo")
    
    return peering_connections

def configure_tgw_routes(tgw_id, region1_resources):
    """Configura rutas en el Transit Gateway para comunicación entre VPCs locales"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("\n--- Configurando rutas TGW ---")
    
    # Las rutas se propagan automáticamente entre las VPCs conectadas al TGW
    # Solo necesitamos esperar a que se propaguen
    time.sleep(30)
    print("Rutas TGW configuradas automáticamente")

def configure_peering_routes(peering_connections):
    """Configura rutas para VPC Peering"""
    ec2_region1 = boto3.client('ec2', region_name='us-east-1')
    ec2_region2 = boto3.client('ec2', region_name='us-west-2')
    
    print("\n--- Configurando rutas VPC Peering ---")
    
    for peering in peering_connections:
        peering_id = peering['peering_id']
        region1_vpc = peering['region1_vpc']
        region2_vpc = peering['region2_vpc']
        
        # Ruta en región 1 hacia región 2
        try:
            ec2_region1.create_route(
                RouteTableId=region1_vpc['route_table_id'],
                DestinationCidrBlock=region2_vpc['vpc_cidr'],
                VpcPeeringConnectionId=peering_id
            )
            print(f"Ruta configurada: {region1_vpc['vpc_id']} -> {region2_vpc['vpc_cidr']}")
        except Exception as e:
            if "RouteAlreadyExists" not in str(e):
                print(f"Error configurando ruta: {e}")
        
        # Ruta en región 2 hacia región 1
        try:
            ec2_region2.create_route(
                RouteTableId=region2_vpc['route_table_id'],
                DestinationCidrBlock=region1_vpc['vpc_cidr'],
                VpcPeeringConnectionId=peering_id
            )
            print(f"Ruta configurada: {region2_vpc['vpc_id']} -> {region1_vpc['vpc_cidr']}")
        except Exception as e:
            if "RouteAlreadyExists" not in str(e):
                print(f"Error configurando ruta: {e}")

def main():
    print("=== Iniciando despliegue híbrido TGW + VPC Peering ===")
    
    # Configuraciones de VPCs
    region1_configs = [
        {'name': 'VPC-R1-A', 'vpc_cidr': '10.1.0.0/16', 'subnet_cidr': '10.1.0.0/24'},
        {'name': 'VPC-R1-B', 'vpc_cidr': '10.2.0.0/16', 'subnet_cidr': '10.2.0.0/24'}
    ]
    
    region2_configs = [
        {'name': 'VPC-R2', 'vpc_cidr': '192.168.0.0/16', 'subnet_cidr': '192.168.1.0/24'}
    ]
    
    try:
        # 1. Crear VPCs en ambas regiones
        region1_resources = create_vpc_infrastructure('us-east-1', region1_configs)
        region2_resources = create_vpc_infrastructure('us-west-2', region2_configs)
        
        # 2. Crear Transit Gateway en Región 1
        tgw_id = create_transit_gateway('us-east-1')
        
        # 3. Conectar las 2 VPCs de Región 1 al TGW
        attach_vpcs_to_tgw('us-east-1', tgw_id, region1_resources)
        
        # 4. Crear VPC Peering entre cada VPC de Región 1 y la VPC de Región 2
        peering_connections = create_vpc_peering_connections(region1_resources, region2_resources)
        
        # 5. Configurar rutas
        configure_tgw_routes(tgw_id, region1_resources)
        configure_peering_routes(peering_connections)
        
        print("\n=== RESUMEN DE RECURSOS CREADOS ===")
        print(f"Transit Gateway (Región 1): {tgw_id}")
        
        print("\nVPCs Región 1 (US-EAST-1):")
        for i, resource in enumerate(region1_resources):
            print(f"  {region1_configs[i]['name']}: {resource['vpc_id']}")
        
        print("\nVPCs Región 2 (US-WEST-2):")
        for i, resource in enumerate(region2_resources):
            print(f"  {region2_configs[i]['name']}: {resource['vpc_id']}")
        
        print("\nVPC Peering Connections:")
        for i, peering in enumerate(peering_connections):
            print(f"  Peering {i+1}: {peering['peering_id']}")
        
        print("\n✅ Infraestructura híbrida creada exitosamente!")
        print("🔗 Conectividad:")
        print("   - VPCs en Región 1 conectadas via Transit Gateway")
        print("   - VPC en Región 2 conectada a cada VPC de Región 1 via VPC Peering")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()