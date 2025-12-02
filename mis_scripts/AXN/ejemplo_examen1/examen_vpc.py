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
    """Ejercicio 2: Crear subredes, IGW y configurar enrutamiento"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 2: Creando infraestructura de red ===")
    
    # Crear Subredes
    print("Creando Subred-Publica...")
    subnet_publica_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.0.1.0/24', AvailabilityZone='us-east-1a'
    )
    subnet_publica_id = subnet_publica_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_publica_id], Tags=[{'Key': 'Name', 'Value': 'Subred-Publica'}])
    print(f"Subred-Publica creada: {subnet_publica_id}")
    
    print("Creando Subred-App...")
    subnet_app_response = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock='10.0.2.0/24', AvailabilityZone='us-east-1a'
    )
    subnet_app_id = subnet_app_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_app_id], Tags=[{'Key': 'Name', 'Value': 'Subred-App'}])
    print(f"Subred-App creada: {subnet_app_id}")
    
    # Crear Internet Gateway
    print("Creando Internet Gateway...")
    igw_response = ec2.create_internet_gateway()
    igw_id = igw_response['InternetGateway']['InternetGatewayId']
    ec2.create_tags(Resources=[igw_id], Tags=[{'Key': 'Name', 'Value': 'Examen-IGW'}])
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    print(f"Internet Gateway creado y adjuntado: {igw_id}")
    
    # Configurar Enrutamiento
    print("Configurando enrutamiento...")
    route_table_response = ec2.create_route_table(VpcId=vpc_id)
    route_table_id = route_table_response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[route_table_id], Tags=[{'Key': 'Name', 'Value': 'RT-Subred-Publica'}])
    ec2.create_route(RouteTableId=route_table_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
    ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_publica_id)
    print(f"Tabla de enrutamiento creada y asociada: {route_table_id}")
    
    print(f"✅ Infraestructura de red creada exitosamente!")
    return {
        'subnet_publica_id': subnet_publica_id,
        'subnet_app_id': subnet_app_id,
        'igw_id': igw_id,
        'route_table_id': route_table_id
    }

def ejercicio3_crear_instancias(vpc_id, subnet_publica_id, subnet_app_id):
    """Ejercicio 3: Crear grupos de seguridad e instancias EC2"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 3: Creando grupos de seguridad e instancias ===")
    
    # Crear Security Group GS-Bastion
    print("Creando Security Group GS-Bastion...")
    sg_bastion_response = ec2.create_security_group(
        GroupName='GS-Bastion',
        Description='Security Group para Bastion Host',
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
    
    # Crear Security Group GS-App
    print("Creando Security Group GS-App...")
    sg_app_response = ec2.create_security_group(
        GroupName='GS-App',
        Description='Security Group para App Server',
        VpcId=vpc_id
    )
    sg_app_id = sg_app_response['GroupId']
    ec2.create_tags(Resources=[sg_app_id], Tags=[{'Key': 'Name', 'Value': 'GS-App'}])
    
    # Reglas para GS-App (SSH y ICMP desde GS-Bastion)
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
    
    # Lanzar instancia Bastion-Host
    print("Lanzando instancia Bastion-Host...")
    bastion_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        NetworkInterfaces=[{
            'SubnetId': subnet_publica_id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'Groups': [sg_bastion_id]
        }],
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'Bastion-Host'}]
        }]
    )
    bastion_id = bastion_response['Instances'][0]['InstanceId']
    print(f"Bastion-Host lanzado: {bastion_id}")
    
    # Lanzar instancia App-Server
    print("Lanzando instancia App-Server...")
    app_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        SecurityGroupIds=[sg_app_id],
        SubnetId=subnet_app_id,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'App-Server'}]
        }]
    )
    app_server_id = app_response['Instances'][0]['InstanceId']
    print(f"App-Server lanzado: {app_server_id}")
    
    print(f"✅ Instancias y grupos de seguridad creados exitosamente!")
    return {
        'sg_bastion_id': sg_bastion_id,
        'sg_app_id': sg_app_id,
        'bastion_id': bastion_id,
        'app_server_id': app_server_id
    }

def ejercicio4_crear_nat_gateway(vpc_id, subnet_publica_id, subnet_app_id):
    """Ejercicio 4: Implementación de NAT Gateway para Salida Privada"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 4: Implementación de NAT Gateway para Salida Privada ===")
    
    # Crear IP Elástica
    print("Creando IP Elástica...")
    eip_response = ec2.allocate_address(
        Domain='vpc',
        TagSpecifications=[{
            'ResourceType': 'elastic-ip',
            'Tags': [{'Key': 'Name', 'Value': 'Examen-NAT-EIP'}]
        }]
    )
    elastic_ip_alloc = eip_response['AllocationId']
    print(f"IP Elástica creada: {elastic_ip_alloc}")
    
    # Crear NAT Gateway
    print("Creando NAT Gateway...")
    nat_gw_response = ec2.create_nat_gateway(
        SubnetId=subnet_publica_id,
        AllocationId=elastic_ip_alloc
    )
    nat_gw_id = nat_gw_response['NatGateway']['NatGatewayId']
    
    # Etiquetar NAT Gateway
    ec2.create_tags(Resources=[nat_gw_id], Tags=[{'Key': 'Name', 'Value': 'Examen-NAT-GW'}])
    print(f"NAT Gateway creado: {nat_gw_id}")
    
    # Esperar a que el NAT Gateway esté disponible
    print("Esperando a que el NAT Gateway esté disponible...")
    waiter = ec2.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_gw_id])
    
    # Obtener la tabla de rutas privada
    route_tables = ec2.describe_route_tables(
        Filters=[
            {'Name': 'vpc-id', 'Values': [vpc_id]},
            {'Name': 'association.subnet-id', 'Values': [subnet_app_id]}
        ]
    )
    
    if route_tables['RouteTables']:
        rt_privada_id = route_tables['RouteTables'][0]['RouteTableId']
    else:
        # Si no hay tabla específica, usar la tabla por defecto
        default_rt = ec2.describe_route_tables(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'association.main', 'Values': ['true']}
            ]
        )
        rt_privada_id = default_rt['RouteTables'][0]['RouteTableId']
    
    # Agregar ruta hacia el NAT Gateway
    print("Configurando ruta hacia NAT Gateway...")
    ec2.create_route(
        RouteTableId=rt_privada_id,
        DestinationCidrBlock='0.0.0.0/0',
        NatGatewayId=nat_gw_id
    )
    
    print("✅ NAT Gateway configurado exitosamente!")
    print("El App-Server ahora tiene salida a internet a través del NAT Gateway")
    return {
        'nat_gw_id': nat_gw_id,
        'elastic_ip_alloc': elastic_ip_alloc
    }


def ejercicio5_configurar_nacl_fallo_ping(vpc_id, subnet_app_id):
    """Ejercicio 5 ALTERNATIVO: NACL que bloquea respuestas ICMP para demostrar comportamiento stateless"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 5: Configurando Network ACL (FALLO PING) ===")
    
    # Crear Network ACL
    print("Creando Network ACL...")
    nacl_response = ec2.create_network_acl(VpcId=vpc_id)
    nacl_id = nacl_response['NetworkAcl']['NetworkAclId']
    ec2.create_tags(Resources=[nacl_id], Tags=[{'Key': 'Name', 'Value': 'NACL-Fallo-Ping'}])
    print(f"Network ACL creada: {nacl_id}")
    
    # Asociar NACL a Subred-App
    print("Asociando NACL a Subred-App...")
    nacls = ec2.describe_network_acls(Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_app_id]}])
    current_association_id = nacls['NetworkAcls'][0]['Associations'][0]['NetworkAclAssociationId']
    
    ec2.replace_network_acl_association(
        AssociationId=current_association_id,
        NetworkAclId=nacl_id
    )
    print("NACL asociada a Subred-App")
    
    # Reglas de entrada (Inbound) - PERMITIR TODO
    print("Configurando reglas de entrada...")
    # SSH (puerto 22)
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_id,
        RuleNumber=100,
        Protocol='6',  # TCP
        RuleAction='allow',
        PortRange={'From': 22, 'To': 22},
        CidrBlock='0.0.0.0/0',
        Egress=False
    )
    
    # ICMP de entrada - PERMITIR (para recibir ping)
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_id,
        RuleNumber=110,
        Protocol='1',  # ICMP
        RuleAction='allow',
        IcmpTypeCode={'Type': -1, 'Code': -1},
        CidrBlock='0.0.0.0/0',
        Egress=False
    )
    
    # Reglas de salida (Outbound) - BLOQUEAR ICMP
    print("Configurando reglas de salida (SIN ICMP)...")
    # Puertos efímeros para respuestas SSH (1024-65535) - PERMITIR
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_id,
        RuleNumber=100,
        Protocol='6',  # TCP
        RuleAction='allow',
        PortRange={'From': 1024, 'To': 65535},
        CidrBlock='0.0.0.0/0',
        Egress=True
    )
    
    # *** NO AÑADIR REGLA ICMP DE SALIDA - ESTO CAUSA EL FALLO ***
    # Las respuestas ICMP serán bloqueadas, demostrando el comportamiento stateless
    
    print("⚠️  Network ACL configurada SIN reglas ICMP de salida")
    print("⚠️  El ping FALLARÁ porque las respuestas ICMP están bloqueadas")
    print("⚠️  Esto demuestra el comportamiento STATELESS de las NACLs")
    return {'nacl_id': nacl_id}


def ejercicio5_configurar_nacl(vpc_id, subnet_app_id):
    """Ejercicio 4: Crear y configurar Network ACL"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    print("=== EJERCICIO 5: Configurando Network ACL ===")
    
    # Crear Network ACL
    print("Creando Network ACL...")
    nacl_response = ec2.create_network_acl(VpcId=vpc_id)
    nacl_id = nacl_response['NetworkAcl']['NetworkAclId']
    ec2.create_tags(Resources=[nacl_id], Tags=[{'Key': 'Name', 'Value': 'NACL-Prueba'}])
    print(f"Network ACL creada: {nacl_id}")
    
    # Asociar NACL a Subred-App
    print("Asociando NACL a Subred-App...")
    # Primero obtener la asociación actual
    nacls = ec2.describe_network_acls(Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_app_id]}])
    current_association_id = nacls['NetworkAcls'][0]['Associations'][0]['NetworkAclAssociationId']
    
    # Reemplazar la asociación
    ec2.replace_network_acl_association(
        AssociationId=current_association_id,
        NetworkAclId=nacl_id
    )
    print("NACL asociada a Subred-App")
    
    # Reglas de entrada (Inbound)
    print("Configurando reglas de entrada...")
    # SSH (puerto 22)
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_id,
        RuleNumber=100,
        Protocol='6',  # TCP
        RuleAction='allow',
        PortRange={'From': 22, 'To': 22},
        CidrBlock='0.0.0.0/0',
        Egress=False
    )
    
    # ICMP
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_id,
        RuleNumber=110,
        Protocol='1',  # ICMP
        RuleAction='allow',
        IcmpTypeCode={'Type': -1, 'Code': -1},
        CidrBlock='0.0.0.0/0',
        Egress=False
    )
    
    # Reglas de salida (Outbound)
    print("Configurando reglas de salida...")
    # Puertos efímeros para respuestas SSH (1024-65535)
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_id,
        RuleNumber=100,
        Protocol='6',  # TCP
        RuleAction='allow',
        PortRange={'From': 1024, 'To': 65535},
        CidrBlock='0.0.0.0/0',
        Egress=True
    )
    
    # ICMP de salida
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_id,
        RuleNumber=110,
        Protocol='1',  # ICMP
        RuleAction='allow',
        IcmpTypeCode={'Type': -1, 'Code': -1},
        CidrBlock='0.0.0.0/0',
        Egress=True
    )
    
    print(f"✅ Network ACL configurada exitosamente!")
    return {'nacl_id': nacl_id}

def main():
    # Ejecutar ejercicios
    vpc_id = ejercicio1_crear_vpc()
    recursos_red = ejercicio2_crear_infraestructura(vpc_id)
    recursos_instancias = ejercicio3_crear_instancias(
        vpc_id, 
        recursos_red['subnet_publica_id'], 
        recursos_red['subnet_app_id']
    )
# EJEMPLO DE CONEXION A INSTANCIAS CREADAS
# Descargar llave privada vockey.pem (o similar): 
# chmod 400 labsuser.pem
# ssh-add vockey.pem (o similar). 
#Conexion a instancia Bastion  ssh -A ubuntu@<IP_PUBLICA_BASTION>. 
# Dentro del Bastión conexion a la instancia sin ip publica
# ssh -A -i vockey.pem ubuntu@54.211.50.100
    recursos_nat = ejercicio4_crear_nat_gateway(
        vpc_id,
        recursos_red['subnet_publica_id'],
        recursos_red['subnet_app_id']
    )
    # Usar la función normal o la de fallo según se necesite
    recursos_nacl = ejercicio5_configurar_nacl(vpc_id, recursos_red['subnet_app_id'])
    # recursos_nacl = ejercicio5_configurar_nacl_fallo_ping(vpc_id, recursos_red['subnet_app_id'])  # Para demostrar fallo


    # -----------------------------------------------------------------
    #ESTO ES UNA VERSION DE PRUEBA PARA CORRER EL EXAMEN CON VPC FIJA
    # -----------------------------------------------------------------

    # VERSION MANUAL CON VPC FIJA
    # vpc_id = ejercicio1_crear_vpc()
    # recursos_red = ejercicio2_crear_infraestructura("vpc-09423e96689d2aabd")
    # recursos_instancias = ejercicio3_crear_instancias(
    #     "vpc-09423e96689d2aabd", 
    #     "subnet-0c4559cc057f2b282", 
    #     "subnet-005d4d3a189a6ec00"
    # )

# EJEMPLO DE CONEXION A INSTANCIAS CREADAS
# Descargar llave privada vockey.pem (o similar): 
# chmod 400 labsuser.pem
# ssh-add vockey.pem (o similar). 
#Conexion a instancia Bastion  ssh -A ubuntu@<IP_PUBLICA_BASTION>. 
# Dentro del Bastión conexion a la instancia sin ip publica
# ssh -A -i labsuser.pem ubuntu@54.80.59.24


    # recursos_nat = ejercicio4_crear_nat_gateway(
    #     "vpc-09423e96689d2aabd", 
    #     "subnet-0c4559cc057f2b282", 
    #     "subnet-005d4d3a189a6ec00"
    # )
    
    # recursos_nacl = ejercicio5_configurar_nacl("vpc-09423e96689d2aabd", "subnet-005d4d3a189a6ec00")
    
    # Resumen final
    print("\n=== RESUMEN FINAL ===")
    print(f"VPC ID: {vpc_id}")
    print(f"Subred-Publica ID: {recursos_red['subnet_publica_id']}")
    print(f"Subred-App ID: {recursos_red['subnet_app_id']}")
    print(f"Internet Gateway ID: {recursos_red['igw_id']}")
    print(f"Tabla de Enrutamiento ID: {recursos_red['route_table_id']}")
    print(f"Security Group Bastion ID: {recursos_instancias['sg_bastion_id']}")
    print(f"Security Group App ID: {recursos_instancias['sg_app_id']}")
    print(f"Bastion-Host ID: {recursos_instancias['bastion_id']}")
    print(f"App-Server ID: {recursos_instancias['app_server_id']}")
    print(f"NAT Gateway ID: {recursos_nat['nat_gw_id']}")
    print(f"IP Elástica NAT: {recursos_nat['elastic_ip_alloc']}")
    print(f"Network ACL ID: {recursos_nacl['nacl_id']}")
    print("\nNota: App-Server tiene salida a internet a través del NAT Gateway")
    print("Nota: NACL-Prueba está asociada a Subred-App con reglas stateless para SSH e ICMP")

if __name__ == "__main__":
    main()

