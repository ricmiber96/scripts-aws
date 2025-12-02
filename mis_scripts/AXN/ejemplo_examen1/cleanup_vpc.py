#!/usr/bin/env python3
import boto3

def main():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Buscar VPC por nombre
    print("Buscando VPC 'Examen-VPC-Ricardo'...")
    vpcs = ec2.describe_vpcs(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': ['Examen-VPC-Ricardo']
            }
        ]
    )
    
    if not vpcs['Vpcs']:
        print("❌ No se encontró la VPC 'Examen-VPC-Ricardo'")
        return
    
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    print(f"VPC encontrada: {vpc_id}")
    
    # 1. Terminar instancias EC2
    print("\nTerminando instancias EC2...")
    instances = ec2.describe_instances(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}, {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}]
    )
    instance_ids = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    if instance_ids:
        ec2.terminate_instances(InstanceIds=instance_ids)
        print(f"Instancias terminadas: {instance_ids}")
        
        # Esperar a que las instancias se terminen
        print("Esperando terminación de instancias...")
        waiter = ec2.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=instance_ids)
        print("Instancias terminadas exitosamente")
    
    # 2. Restaurar asociaciones de Network ACL y eliminar NACLs personalizadas
    print("\nEliminando Network ACLs personalizadas...")
    nacls = ec2.describe_network_acls(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    )
    
    # Encontrar NACL por defecto
    default_nacl_id = None
    for nacl in nacls['NetworkAcls']:
        if nacl['IsDefault']:
            default_nacl_id = nacl['NetworkAclId']
            break
    
    # Restaurar asociaciones y eliminar NACLs personalizadas
    for nacl in nacls['NetworkAcls']:
        if not nacl['IsDefault']:
            try:
                # Restaurar asociaciones a la NACL por defecto
                for assoc in nacl['Associations']:
                    ec2.replace_network_acl_association(
                        AssociationId=assoc['NetworkAclAssociationId'],
                        NetworkAclId=default_nacl_id
                    )
                # Eliminar NACL personalizada
                ec2.delete_network_acl(NetworkAclId=nacl['NetworkAclId'])
                print(f"Network ACL {nacl['NetworkAclId']} eliminada")
            except Exception as e:
                print(f"Error eliminando Network ACL: {e}")
    
    # 3. Eliminar grupos de seguridad
    print("\nEliminando grupos de seguridad...")
    security_groups = ec2.describe_security_groups(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    )
    
    # Primero eliminar todas las reglas que referencian otros Security Groups
    for sg in security_groups['SecurityGroups']:
        if sg['GroupName'] != 'default':
            try:
                # Eliminar reglas de entrada que referencian otros SGs
                for rule in sg['IpPermissions']:
                    if rule.get('UserIdGroupPairs'):
                        ec2.revoke_security_group_ingress(
                            GroupId=sg['GroupId'],
                            IpPermissions=[rule]
                        )
                # Eliminar reglas de salida que referencian otros SGs
                for rule in sg['IpPermissionsEgress']:
                    if rule.get('UserIdGroupPairs'):
                        ec2.revoke_security_group_egress(
                            GroupId=sg['GroupId'],
                            IpPermissions=[rule]
                        )
            except Exception as e:
                print(f"Error eliminando reglas de SG {sg['GroupId']}: {e}")
    
    # Luego eliminar los Security Groups
    for sg in security_groups['SecurityGroups']:
        if sg['GroupName'] != 'default':
            try:
                ec2.delete_security_group(GroupId=sg['GroupId'])
                print(f"Security Group {sg['GroupId']} eliminado")
            except Exception as e:
                print(f"Error eliminando Security Group: {e}")
    
    # 4. Eliminar NAT Gateways e IPs Elásticas
    print("\nEliminando NAT Gateways...")
    nat_gateways = ec2.describe_nat_gateways(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    )
    
    for nat_gw in nat_gateways['NatGateways']:
        if nat_gw['State'] not in ['deleted', 'deleting']:
            try:
                # Obtener AllocationId de la IP Elástica antes de eliminar NAT Gateway
                allocation_id = None
                for address in nat_gw['NatGatewayAddresses']:
                    if 'AllocationId' in address:
                        allocation_id = address['AllocationId']
                        break
                
                # Eliminar NAT Gateway
                ec2.delete_nat_gateway(NatGatewayId=nat_gw['NatGatewayId'])
                print(f"NAT Gateway {nat_gw['NatGatewayId']} eliminado")
                
                # Esperar a que el NAT Gateway se elimine
                print("Esperando eliminación del NAT Gateway...")
                waiter = ec2.get_waiter('nat_gateway_deleted')
                waiter.wait(NatGatewayIds=[nat_gw['NatGatewayId']])
                
                # Liberar IP Elástica
                if allocation_id:
                    ec2.release_address(AllocationId=allocation_id)
                    print(f"IP Elástica {allocation_id} liberada")
                    
            except Exception as e:
                print(f"Error eliminando NAT Gateway: {e}")
    
    # 5. Eliminar tablas de enrutamiento personalizadas
    print("\nEliminando tablas de enrutamiento...")
    route_tables = ec2.describe_route_tables(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    )
    for rt in route_tables['RouteTables']:
        if not rt['Associations'] or not any(assoc.get('Main') for assoc in rt['Associations']):
            try:
                # Desasociar de subredes
                for assoc in rt['Associations']:
                    if not assoc.get('Main'):
                        ec2.disassociate_route_table(AssociationId=assoc['RouteTableAssociationId'])
                # Eliminar tabla de enrutamiento
                ec2.delete_route_table(RouteTableId=rt['RouteTableId'])
                print(f"Tabla de enrutamiento {rt['RouteTableId']} eliminada")
            except Exception as e:
                print(f"Error eliminando tabla de enrutamiento: {e}")
    
    # 6. Desconectar y eliminar Internet Gateway
    print("\nEliminando Internet Gateway...")
    igws = ec2.describe_internet_gateways(
        Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
    )
    for igw in igws['InternetGateways']:
        try:
            ec2.detach_internet_gateway(
                InternetGatewayId=igw['InternetGatewayId'],
                VpcId=vpc_id
            )
            ec2.delete_internet_gateway(InternetGatewayId=igw['InternetGatewayId'])
            print(f"Internet Gateway {igw['InternetGatewayId']} eliminado")
        except Exception as e:
            print(f"Error eliminando IGW: {e}")
    
    # 7. Eliminar subredes
    print("\nEliminando subredes...")
    subnets = ec2.describe_subnets(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    )
    for subnet in subnets['Subnets']:
        try:
            ec2.delete_subnet(SubnetId=subnet['SubnetId'])
            print(f"Subred {subnet['SubnetId']} eliminada")
        except Exception as e:
            print(f"Error eliminando subred: {e}")
    
    # 8. Eliminar VPC
    print("\nEliminando VPC...")
    try:
        ec2.delete_vpc(VpcId=vpc_id)
        print(f"✅ VPC {vpc_id} y toda su infraestructura eliminada exitosamente!")
    except Exception as e:
        print(f"❌ Error eliminando VPC: {e}")

if __name__ == "__main__":
    main()