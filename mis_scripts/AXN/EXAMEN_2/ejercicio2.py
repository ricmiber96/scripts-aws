import boto3
import time
import sys

# --- CONFIGURACIÓN ---
REGION = 'us-east-1'
VPC_CIDR = '10.0.0.0/16'
PUBLIC_SUBNET_CIDR = '10.0.1.0/24'
PRIVATE_SUBNET_CIDR = '10.0.2.0/24'

ec2 = boto3.client('ec2', region_name=REGION)

def create_secured_infrastructure():
    print(f"--- Iniciando despliegue de VPC Segura en {REGION} ---")

    # 1. Crear VPC
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR, TagSpecifications=[{'ResourceType': 'vpc', 'Tags': [{'Key': 'Name', 'Value': 'VPC-Seguridad-Estricta'}]}])
    vpc_id = vpc['Vpc']['VpcId']
    ec2.get_waiter('vpc_available').wait(VpcIds=[vpc_id])
    print(f"✅ VPC Creada: {vpc_id}")

    # 2. Crear Subredes
    # Pública
    pub_sub = ec2.create_subnet(VpcId=vpc_id, CidrBlock=PUBLIC_SUBNET_CIDR, AvailabilityZone=f'{REGION}a', TagSpecifications=[{'ResourceType': 'subnet', 'Tags': [{'Key': 'Name', 'Value': 'Subnet-Publica'}]}])
    pub_sub_id = pub_sub['Subnet']['SubnetId']
    
    # Privada
    priv_sub = ec2.create_subnet(VpcId=vpc_id, CidrBlock=PRIVATE_SUBNET_CIDR, AvailabilityZone=f'{REGION}a', TagSpecifications=[{'ResourceType': 'subnet', 'Tags': [{'Key': 'Name', 'Value': 'Subnet-Privada'}]}])
    priv_sub_id = priv_sub['Subnet']['SubnetId']
    print(f"✅ Subredes creadas: Publica ({pub_sub_id}), Privada ({priv_sub_id})")

    # 3. Internet Gateway (Para la pública)
    igw = ec2.create_internet_gateway(TagSpecifications=[{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'Name', 'Value': 'IGW-Seguro'}]}])
    igw_id = igw['InternetGateway']['InternetGatewayId']
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    
    # Tabla de rutas pública
    rt = ec2.create_route_table(VpcId=vpc_id, TagSpecifications=[{'ResourceType': 'route-table', 'Tags': [{'Key': 'Name', 'Value': 'RT-Publica'}]}])
    rt_id = rt['RouteTable']['RouteTableId']
    ec2.create_route(RouteTableId=rt_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
    ec2.associate_route_table(RouteTableId=rt_id, SubnetId=pub_sub_id)
    print("✅ Conectividad a Internet configurada para Subred Pública")

    # ---------------------------------------------------------
    # 4. CONFIGURACIÓN DE NACLs (El núcleo del ejercicio)
    # ---------------------------------------------------------
    
    # --- A. NACL PÚBLICA ---
    # Objetivo: Solo permitir HTTP/HTTPS desde internet.
    # Nota Técnica: Como las NACL son Stateless, si permitimos entrada al 80, 
    # debemos permitir SALIDA a los puertos efímeros (1024-65535) para que el servidor pueda responder al cliente.
    
    nacl_pub = ec2.create_network_acl(VpcId=vpc_id, TagSpecifications=[{'ResourceType': 'network-acl', 'Tags': [{'Key': 'Name', 'Value': 'NACL-Publica-Estricta'}]}])
    nacl_pub_id = nacl_pub['NetworkAcl']['NetworkAclId']

    # REGLAS DE ENTRADA (Inbound)
    # 100: Permitir HTTP (80) desde cualquier lugar
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_pub_id, RuleNumber=100, Protocol='6', RuleAction='allow', Egress=False, 
        CidrBlock='0.0.0.0/0', PortRange={'From': 80, 'To': 80}
    )
    # 110: Permitir HTTPS (443) desde cualquier lugar
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_pub_id, RuleNumber=110, Protocol='6', RuleAction='allow', Egress=False, 
        CidrBlock='0.0.0.0/0', PortRange={'From': 443, 'To': 443}
    )
    # 120: Permitir tráfico de retorno desde la Subred Privada (para que la privada pueda hablarle)
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_pub_id, RuleNumber=120, Protocol='-1', RuleAction='allow', Egress=False, 
        CidrBlock=PRIVATE_SUBNET_CIDR
    )
    # (Implícito: Deny All para el resto, incluido SSH puerto 22 desde internet)

    # REGLAS DE SALIDA (Outbound)
    # 100: Permitir puertos efímeros hacia Internet (Para responder a las peticiones web)
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_pub_id, RuleNumber=100, Protocol='6', RuleAction='allow', Egress=True, 
        CidrBlock='0.0.0.0/0', PortRange={'From': 1024, 'To': 65535}
    )
    # 110: Permitir todo el tráfico hacia la Subred Privada
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_pub_id, RuleNumber=110, Protocol='-1', RuleAction='allow', Egress=True, 
        CidrBlock=PRIVATE_SUBNET_CIDR
    )

    # Reemplazar la asociación de la NACL por defecto con esta nueva
    assoc_pub = ec2.describe_network_acls(Filters=[{'Name': 'association.subnet-id', 'Values': [pub_sub_id]}])['NetworkAcls'][0]['Associations'][0]['NetworkAclAssociationId']
    ec2.replace_network_acl_association(AssociationId=assoc_pub, NetworkAclId=nacl_pub_id)
    print(f"✅ NACL Pública ({nacl_pub_id}) configurada y asociada.")


    # --- B. NACL PRIVADA ---
    # Objetivo: Solo permitir comunicación con la subred pública. Aislamiento total de internet directo.
    
    nacl_priv = ec2.create_network_acl(VpcId=vpc_id, TagSpecifications=[{'ResourceType': 'network-acl', 'Tags': [{'Key': 'Name', 'Value': 'NACL-Privada-Aislada'}]}])
    nacl_priv_id = nacl_priv['NetworkAcl']['NetworkAclId']

    # REGLAS DE ENTRADA (Inbound)
    # 100: Permitir TODO desde la Subred Pública
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_priv_id, RuleNumber=100, Protocol='-1', RuleAction='allow', Egress=False, 
        CidrBlock=PUBLIC_SUBNET_CIDR
    )
    # (Implícito: Deniega cualquier entrada directa desde 0.0.0.0/0 u otras IPs)

    # REGLAS DE SALIDA (Outbound)
    # 100: Permitir TODO hacia la Subred Pública
    ec2.create_network_acl_entry(
        NetworkAclId=nacl_priv_id, RuleNumber=100, Protocol='-1', RuleAction='allow', Egress=True, 
        CidrBlock=PUBLIC_SUBNET_CIDR
    )
    # (Implícito: Deniega salida directa a internet)

    # Reemplazar asociación
    assoc_priv = ec2.describe_network_acls(Filters=[{'Name': 'association.subnet-id', 'Values': [priv_sub_id]}])['NetworkAcls'][0]['Associations'][0]['NetworkAclAssociationId']
    ec2.replace_network_acl_association(AssociationId=assoc_priv, NetworkAclId=nacl_priv_id)
    print(f"✅ NACL Privada ({nacl_priv_id}) configurada y asociada.")

    print("\n--- RESUMEN DE SEGURIDAD ---")
    print("1. Subred Pública: Solo acepta puertos 80/443 desde Internet. Bloquea SSH y otros.")
    print(f"2. Subred Privada: Solo acepta tráfico de {PUBLIC_SUBNET_CIDR}.")
    print("3. Las reglas son Stateless (NACL), garantizando el cumplimiento a nivel de red.")

if __name__ == '__main__':
    create_secured_infrastructure()