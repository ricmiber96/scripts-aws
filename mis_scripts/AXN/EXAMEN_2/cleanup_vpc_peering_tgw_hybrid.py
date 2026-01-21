#!/usr/bin/env python3
import boto3
import time

def cleanup_region(region, vpc_names):
    """Limpia recursos en una región específica"""
    ec2 = boto3.client('ec2', region_name=region)
    print(f"\n=== Limpiando {region} ===")
    
    # 1. Terminar instancias EC2
    print("1. Terminando instancias EC2...")
    try:
        instances = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'stopping', 'pending']},
                {'Name': 'tag:Name', 'Values': [f'Instance-{name}' for name in vpc_names]}
            ]
        )
        
        instance_ids = []
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance['InstanceId'])
        
        if instance_ids:
            ec2.terminate_instances(InstanceIds=instance_ids)
            print(f"   Terminando: {instance_ids}")
            
            for instance_id in instance_ids:
                waiter = ec2.get_waiter('instance_terminated')
                waiter.wait(InstanceIds=[instance_id], WaiterConfig={'Delay': 15, 'MaxAttempts': 40})
            print("   ✅ Instancias terminadas")
        else:
            print("   No hay instancias")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")

def cleanup_vpc_peering():
    """Elimina todas las VPC Peering connections"""
    ec2_east = boto3.client('ec2', region_name='us-east-1')
    print("\n2. Eliminando VPC Peering Connections...")
    
    try:
        peerings = ec2_east.describe_vpc_peering_connections(
            Filters=[
                {'Name': 'status-code', 'Values': ['active', 'pending-acceptance']},
                {'Name': 'tag:Name', 'Values': ['Peering-R1VPC1-R2VPC', 'Peering-R1VPC2-R2VPC']}
            ]
        )
        
        for peering in peerings['VpcPeeringConnections']:
            peering_id = peering['VpcPeeringConnectionId']
            try:
                ec2_east.delete_vpc_peering_connection(VpcPeeringConnectionId=peering_id)
                print(f"   ✅ Peering eliminado: {peering_id}")
            except Exception as e:
                print(f"   ⚠️ Error eliminando {peering_id}: {e}")
    except Exception as e:
        print(f"   Error: {e}")

def cleanup_transit_gateway():
    """Elimina Transit Gateway y attachments en us-east-1"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    print("\n3. Eliminando Transit Gateway...")
    
    # Eliminar VPC Attachments
    try:
        attachments = ec2.describe_transit_gateway_vpc_attachments(
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        
        for attachment in attachments['TransitGatewayVpcAttachments']:
            attachment_id = attachment['TransitGatewayAttachmentId']
            try:
                ec2.delete_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attachment_id)
                print(f"   Eliminando attachment: {attachment_id}")
                
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
                print(f"   ⚠️ Error: {e}")
    except Exception as e:
        print(f"   No attachments: {e}")
    
    # Eliminar Transit Gateway
    try:
        tgws = ec2.describe_transit_gateways(
            Filters=[
                {'Name': 'state', 'Values': ['available']},
                {'Name': 'tag:Name', 'Values': ['TGW-Region1']}
            ]
        )
        
        for tgw in tgws['TransitGateways']:
            tgw_id = tgw['TransitGatewayId']
            try:
                ec2.delete_transit_gateway(TransitGatewayId=tgw_id)
                print(f"   ✅ TGW eliminado: {tgw_id}")
            except Exception as e:
                print(f"   ⚠️ Error: {e}")
    except Exception as e:
        print(f"   No TGW: {e}")

def cleanup_vpcs(region, vpc_names):
    """Elimina VPCs y recursos asociados"""
    ec2 = boto3.client('ec2', region_name=region)
    print(f"\n4. Eliminando VPCs en {region}...")
    
    try:
        vpcs = ec2.describe_vpcs(
            Filters=[{'Name': 'tag:Name', 'Values': vpc_names}]
        )
        
        for vpc in vpcs['Vpcs']:
            vpc_id = vpc['VpcId']
            vpc_name = next((tag['Value'] for tag in vpc.get('Tags', []) if tag['Key'] == 'Name'), vpc_id)
            print(f"   Eliminando {vpc_name} ({vpc_id})")
            
            # Security Groups
            sgs = ec2.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            for sg in sgs['SecurityGroups']:
                if sg['GroupName'] != 'default':
                    try:
                        ec2.delete_security_group(GroupId=sg['GroupId'])
                    except Exception as e:
                        print(f"     ⚠️ SG error: {e}")
            
            # Subredes
            subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            for subnet in subnets['Subnets']:
                try:
                    ec2.delete_subnet(SubnetId=subnet['SubnetId'])
                except Exception as e:
                    print(f"     ⚠️ Subnet error: {e}")
            
            # Internet Gateways
            igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])
            for igw in igws['InternetGateways']:
                try:
                    ec2.detach_internet_gateway(InternetGatewayId=igw['InternetGatewayId'], VpcId=vpc_id)
                    ec2.delete_internet_gateway(InternetGatewayId=igw['InternetGatewayId'])
                except Exception as e:
                    print(f"     ⚠️ IGW error: {e}")
            
            # VPC
            time.sleep(5)
            try:
                ec2.delete_vpc(VpcId=vpc_id)
                print(f"   ✅ VPC eliminada: {vpc_name}")
            except Exception as e:
                print(f"   ⚠️ VPC error: {e}")
                
    except Exception as e:
        print(f"   Error: {e}")

def main():
    """Función principal de limpieza"""
    print("=== LIMPIEZA INFRAESTRUCTURA HÍBRIDA VPC PEERING + TGW ===")
    print("\nRecursos a eliminar:")
    print("• Instancias EC2 (ambas regiones)")
    print("• VPC Peering Connections")
    print("• Transit Gateway y attachments")
    print("• VPCs: VPC-R1-A, VPC-R1-B (us-east-1) y VPC-R2-A (us-west-2)")
    print("• Security Groups, Subredes, IGWs")
    
    confirm = input("\n¿Continuar? (escriba 'ELIMINAR'): ")
    if confirm != 'ELIMINAR':
        print("❌ Cancelado")
        return
    
    # Definir VPCs por región
    region1_vpcs = ['VPC-R1-A', 'VPC-R1-B']
    region2_vpcs = ['VPC-R2-A']
    
    try:
        # Limpiar instancias
        cleanup_region('us-east-1', region1_vpcs)
        cleanup_region('us-west-2', region2_vpcs)
        
        # Limpiar peering
        cleanup_vpc_peering()
        
        # Limpiar TGW
        cleanup_transit_gateway()
        
        # Limpiar VPCs
        cleanup_vpcs('us-east-1', region1_vpcs)
        cleanup_vpcs('us-west-2', region2_vpcs)
        
        print("\n✅ LIMPIEZA COMPLETADA")
        
    except Exception as e:
        print(f"\n❌ Error general: {e}")

if __name__ == "__main__":
    main()