#!/usr/bin/env python3
import boto3
import time

def cleanup_region(region):
    """Limpia todos los recursos de Transit Gateway en una región"""
    ec2 = boto3.client('ec2', region_name=region)
    
    print(f"\n=== Limpiando recursos en {region} ===")
    
    # 1. Terminar instancias EC2
    print("Terminando instancias EC2...")
    instances = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'stopping', 'pending']},
            {'Name': 'tag:Name', 'Values': ['Instance-VPC-R1-B', 'Instance-VPC-R2-A', 'Instance-VPC-West-1']}
        ]
    )
    
    instance_ids = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    if instance_ids:
        ec2.terminate_instances(InstanceIds=instance_ids)
        print(f"Terminando instancias: {instance_ids}")
        
        # Esperar a que las instancias se terminen
        print("Esperando que las instancias se terminen...")
        for instance_id in instance_ids:
            while True:
                try:
                    response = ec2.describe_instances(InstanceIds=[instance_id])
                    state = response['Reservations'][0]['Instances'][0]['State']['Name']
                    if state == 'terminated':
                        break
                    time.sleep(10)
                except:
                    break
    
    # 2. Eliminar rutas personalizadas de las tablas de rutas
    print("Eliminando rutas personalizadas...")
    try:
        route_tables = ec2.describe_route_tables(
            Filters=[{'Name': 'tag:Name', 'Values': ['*VPC-East*', '*VPC-West*']}]
        )
        
        for rt in route_tables['RouteTables']:
            rt_id = rt['RouteTableId']
            for route in rt['Routes']:
                # Eliminar rutas que no sean locales ni la ruta por defecto
                if (route.get('GatewayId') != 'local' and 
                    route.get('DestinationCidrBlock') not in ['0.0.0.0/0'] and
                    route.get('TransitGatewayId')):
                    try:
                        ec2.delete_route(
                            RouteTableId=rt_id,
                            DestinationCidrBlock=route['DestinationCidrBlock']
                        )
                        print(f"  Ruta eliminada: {route['DestinationCidrBlock']} de {rt_id}")
                    except Exception as e:
                        print(f"  Error eliminando ruta: {e}")
    except Exception as e:
        print(f"Error eliminando rutas: {e}")
    
    # 3. Eliminar TGW Peering Attachments
    print("Eliminando TGW Peering Attachments...")
    try:
        peering_attachments = ec2.describe_transit_gateway_peering_attachments(
            Filters=[{'Name': 'state', 'Values': ['available', 'pending', 'pendingAcceptance']}]
        )
        
        for attachment in peering_attachments['TransitGatewayPeeringAttachments']:
            attachment_id = attachment['TransitGatewayAttachmentId']
            try:
                ec2.delete_transit_gateway_peering_attachment(TransitGatewayAttachmentId=attachment_id)
                print(f"Eliminando TGW Peering: {attachment_id}")
                
                # Esperar a que se elimine
                while True:
                    try:
                        response = ec2.describe_transit_gateway_peering_attachments(
                            TransitGatewayAttachmentIds=[attachment_id]
                        )
                        state = response['TransitGatewayPeeringAttachments'][0]['State']
                        if state in ['deleted', 'deleting']:
                            break
                        time.sleep(10)
                    except:
                        break
            except Exception as e:
                print(f"Error eliminando peering {attachment_id}: {e}")
    except Exception as e:
        print(f"No hay peering attachments o error: {e}")
    
    # 4. Eliminar TGW VPC Attachments
    print("Eliminando TGW VPC Attachments...")
    try:
        vpc_attachments = ec2.describe_transit_gateway_vpc_attachments(
            Filters=[{'Name': 'state', 'Values': ['available', 'pending']}]
        )
        
        for attachment in vpc_attachments['TransitGatewayVpcAttachments']:
            attachment_id = attachment['TransitGatewayAttachmentId']
            try:
                ec2.delete_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attachment_id)
                print(f"Eliminando TGW VPC Attachment: {attachment_id}")
                
                # Esperar a que se elimine
                while True:
                    try:
                        response = ec2.describe_transit_gateway_vpc_attachments(
                            TransitGatewayAttachmentIds=[attachment_id]
                        )
                        state = response['TransitGatewayVpcAttachments'][0]['State']
                        if state in ['deleted', 'deleting']:
                            break
                        time.sleep(10)
                    except:
                        break
            except Exception as e:
                print(f"Error eliminando attachment {attachment_id}: {e}")
    except Exception as e:
        print(f"No hay VPC attachments o error: {e}")
    
    # 5. Eliminar Transit Gateways
    print("Eliminando Transit Gateways...")
    try:
        tgws = ec2.describe_transit_gateways(
            Filters=[
                {'Name': 'state', 'Values': ['available']},
                {'Name': 'tag:Name', 'Values': ['TGW-East', 'TGW-West']}
            ]
        )
        
        for tgw in tgws['TransitGateways']:
            tgw_id = tgw['TransitGatewayId']
            try:
                ec2.delete_transit_gateway(TransitGatewayId=tgw_id)
                print(f"Eliminando TGW: {tgw_id}")
                
                # Esperar a que se elimine
                while True:
                    try:
                        response = ec2.describe_transit_gateways(TransitGatewayIds=[tgw_id])
                        state = response['TransitGateways'][0]['State']
                        if state in ['deleted', 'deleting']:
                            break
                        time.sleep(15)
                    except:
                        break
            except Exception as e:
                print(f"Error eliminando TGW {tgw_id}: {e}")
    except Exception as e:
        print(f"No hay Transit Gateways o error: {e}")
    
    # 6. Eliminar VPCs y recursos asociados
    print("Eliminando VPCs y recursos asociados...")
    vpcs = ec2.describe_vpcs(
        Filters=[
            {'Name': 'tag:Name', 'Values': ['VPC-East-1', 'VPC-East-2', 'VPC-West-1']}
        ]
    )
    
    for vpc in vpcs['Vpcs']:
        vpc_id = vpc['VpcId']
        print(f"Eliminando VPC: {vpc_id}")
        
        try:
            # Eliminar Security Groups (excepto el default)
            sgs = ec2.describe_security_groups(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            for sg in sgs['SecurityGroups']:
                if sg['GroupName'] != 'default':
                    try:
                        ec2.delete_security_group(GroupId=sg['GroupId'])
                        print(f"  Security Group eliminado: {sg['GroupId']}")
                    except Exception as e:
                        print(f"  Error eliminando SG {sg['GroupId']}: {e}")
            
            # Eliminar subredes
            subnets = ec2.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            for subnet in subnets['Subnets']:
                try:
                    ec2.delete_subnet(SubnetId=subnet['SubnetId'])
                    print(f"  Subred eliminada: {subnet['SubnetId']}")
                except Exception as e:
                    print(f"  Error eliminando subnet {subnet['SubnetId']}: {e}")
            
            # Desconectar y eliminar Internet Gateway
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
                    print(f"  Internet Gateway eliminado: {igw['InternetGatewayId']}")
                except Exception as e:
                    print(f"  Error eliminando IGW {igw['InternetGatewayId']}: {e}")
            
            # Eliminar VPC
            time.sleep(5)
            try:
                ec2.delete_vpc(VpcId=vpc_id)
                print(f"  VPC eliminada: {vpc_id}")
            except Exception as e:
                print(f"  Error eliminando VPC {vpc_id}: {e}")
                
        except Exception as e:
            print(f"Error procesando VPC {vpc_id}: {e}")

def main():
    """Función principal para limpiar toda la infraestructura"""
    print("=== Iniciando limpieza de infraestructura Transit Gateway (3 VPCs) ===")
    print("⚠️  ADVERTENCIA: Este script eliminará TODOS los recursos creados")
    
    # Confirmar antes de proceder
    confirm = input("¿Continuar con la eliminación? (escriba 'ELIMINAR' para confirmar): ")
    if confirm != 'ELIMINAR':
        print("Operación cancelada")
        return
    
    # Limpiar ambas regiones
    regions = ['us-east-1', 'us-west-2']
    
    for region in regions:
        try:
            cleanup_region(region)
            print(f"✅ Limpieza completada en {region}")
        except Exception as e:
            print(f"❌ Error en {region}: {e}")
    
    print("\n=== Limpieza completada ===")
    print("Todos los recursos han sido eliminados o marcados para eliminación")

if __name__ == "__main__":
    main()d}")
            except Exception as e:
                print(f"  Error eliminando VPC {vpc_id}: {e}")
                
        except Exception as e:
            print(f"Error procesando VPC {vpc_id}: {e}")

def main():
    print("=== Iniciando limpieza de infraestructura Transit Gateway (3 VPCs) ===")
    
    regions = ['us-east-1', 'us-west-2']
    
    try:
        for region in regions:
            cleanup_region(region)
        
        print("\n✅ Limpieza completada exitosamente!")
        print("🗑️ Todos los recursos de Transit Gateway han sido eliminados")
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")

if __name__ == "__main__":
    main()