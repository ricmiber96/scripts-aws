#!/usr/bin/env python3
import boto3
import time

def cleanup_region(region):
    """Limpia todos los recursos de Transit Gateway en una región"""
    ec2 = boto3.client('ec2', region_name=region)
    
    print(f"\n=== Limpiando recursos en {region} ===")
    
    # 1. Terminar instancias EC2
    print("1. Terminando instancias EC2...")
    try:
        instances = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'stopping', 'pending']},
                {'Name': 'tag:Name', 'Values': ['Instance-VPC-East-1', 'Instance-VPC-East-2', 'Instance-VPC-West-1']}
            ]
        )
        
        instance_ids = []
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance['InstanceId'])
        
        if instance_ids:
            ec2.terminate_instances(InstanceIds=instance_ids)
            print(f"   Terminando instancias: {instance_ids}")
            
            # Esperar terminación
            for instance_id in instance_ids:
                waiter = ec2.get_waiter('instance_terminated')
                waiter.wait(InstanceIds=[instance_id], WaiterConfig={'Delay': 15, 'MaxAttempts': 40})
            print("   ✅ Instancias terminadas")
        else:
            print("   No hay instancias para terminar")
    except Exception as e:
        print(f"   ⚠️ Error terminando instancias: {e}")

    # 2. Eliminar TGW Peering Attachments
    print("2. Eliminando TGW Peering Attachments...")
    try:
        peering_attachments = ec2.describe_transit_gateway_peering_attachments(
            Filters=[{'Name': 'state', 'Values': ['available', 'pending', 'pendingAcceptance']}]
        )
        
        for attachment in peering_attachments['TransitGatewayPeeringAttachments']:
            attachment_id = attachment['TransitGatewayAttachmentId']
            try:
                ec2.delete_transit_gateway_peering_attachment(TransitGatewayAttachmentId=attachment_id)
                print(f"   Eliminando TGW Peering: {attachment_id}")
                
                # Esperar eliminación
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
                print(f"   ✅ Peering eliminado: {attachment_id}")
            except Exception as e:
                print(f"   ⚠️ Error eliminando peering {attachment_id}: {e}")
    except Exception as e:
        print(f"   No hay peering attachments: {e}")

    # 3. Eliminar TGW VPC Attachments
    print("3. Eliminando TGW VPC Attachments...")
    try:
        vpc_attachments = ec2.describe_transit_gateway_vpc_attachments(
            Filters=[{'Name': 'state', 'Values': ['available', 'pending']}]
        )
        
        for attachment in vpc_attachments['TransitGatewayVpcAttachments']:
            attachment_id = attachment['TransitGatewayAttachmentId']
            try:
                ec2.delete_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attachment_id)
                print(f"   Eliminando TGW VPC Attachment: {attachment_id}")
                
                # Esperar eliminación
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
                print(f"   ✅ VPC Attachment eliminado: {attachment_id}")
            except Exception as e:
                print(f"   ⚠️ Error eliminando attachment {attachment_id}: {e}")
    except Exception as e:
        print(f"   No hay VPC attachments: {e}")

    # 4. Eliminar Transit Gateways
    print("4. Eliminando Transit Gateways...")
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
                print(f"   Eliminando TGW: {tgw_id}")
                
                # Esperar eliminación
                while True:
                    try:
                        response = ec2.describe_transit_gateways(TransitGatewayIds=[tgw_id])
                        state = response['TransitGateways'][0]['State']
                        if state in ['deleted', 'deleting']:
                            break
                        time.sleep(15)
                    except:
                        break
                print(f"   ✅ TGW eliminado: {tgw_id}")
            except Exception as e:
                print(f"   ⚠️ Error eliminando TGW {tgw_id}: {e}")
    except Exception as e:
        print(f"   No hay Transit Gateways: {e}")

    # 5. Eliminar VPCs y recursos asociados
    print("5. Eliminando VPCs y recursos asociados...")
    try:
        vpcs = ec2.describe_vpcs(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['VPC-East-1', 'VPC-East-2', 'VPC-West-1']}
            ]
        )
        
        for vpc in vpcs['Vpcs']:
            vpc_id = vpc['VpcId']
            vpc_name = next((tag['Value'] for tag in vpc.get('Tags', []) if tag['Key'] == 'Name'), vpc_id)
            print(f"   Eliminando VPC: {vpc_name} ({vpc_id})")
            
            try:
                # Eliminar Security Groups (excepto default)
                sgs = ec2.describe_security_groups(
                    Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
                )
                for sg in sgs['SecurityGroups']:
                    if sg['GroupName'] != 'default':
                        try:
                            ec2.delete_security_group(GroupId=sg['GroupId'])
                            print(f"     Security Group eliminado: {sg['GroupId']}")
                        except Exception as e:
                            print(f"     ⚠️ Error eliminando SG {sg['GroupId']}: {e}")
                
                # Eliminar subredes
                subnets = ec2.describe_subnets(
                    Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
                )
                for subnet in subnets['Subnets']:
                    try:
                        ec2.delete_subnet(SubnetId=subnet['SubnetId'])
                        print(f"     Subred eliminada: {subnet['SubnetId']}")
                    except Exception as e:
                        print(f"     ⚠️ Error eliminando subnet {subnet['SubnetId']}: {e}")
                
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
                        print(f"     Internet Gateway eliminado: {igw['InternetGatewayId']}")
                    except Exception as e:
                        print(f"     ⚠️ Error eliminando IGW {igw['InternetGatewayId']}: {e}")
                
                # Eliminar VPC
                time.sleep(5)
                ec2.delete_vpc(VpcId=vpc_id)
                print(f"   ✅ VPC eliminada: {vpc_name}")
                
            except Exception as e:
                print(f"   ⚠️ Error procesando VPC {vpc_id}: {e}")
                
    except Exception as e:
        print(f"   Error listando VPCs: {e}")

def main():
    """Función principal para limpiar toda la infraestructura"""
    print("=== SCRIPT DE LIMPIEZA - TRANSIT GATEWAY (3 VPCs) ===")
    print("Este script eliminará TODA la infraestructura creada por transit_gateway_3vpcs.py")
    print("\nRecursos que se eliminarán:")
    print("• Instancias EC2 en ambas regiones")
    print("• TGW Peering Attachments")
    print("• TGW VPC Attachments") 
    print("• Transit Gateways (TGW-East, TGW-West)")
    print("• VPCs (VPC-East-1, VPC-East-2, VPC-West-1)")
    print("• Security Groups, Subredes, Internet Gateways")
    
    print("\n⚠️  ADVERTENCIA: Esta acción es IRREVERSIBLE")
    
    # Confirmar antes de proceder
    confirm = input("\n¿Continuar con la eliminación? (escriba 'ELIMINAR' para confirmar): ")
    if confirm != 'ELIMINAR':
        print("❌ Operación cancelada")
        return
    
    # Limpiar ambas regiones
    regions = ['us-east-1', 'us-west-2']
    
    for region in regions:
        try:
            cleanup_region(region)
            print(f"✅ Limpieza completada en {region}")
        except Exception as e:
            print(f"❌ Error en {region}: {e}")
    
    print("\n=== LIMPIEZA COMPLETADA ===")
    print("✅ Todos los recursos han sido eliminados o marcados para eliminación")
    print("💡 Verifica en la consola AWS que no queden recursos activos")

if __name__ == "__main__":
    main()