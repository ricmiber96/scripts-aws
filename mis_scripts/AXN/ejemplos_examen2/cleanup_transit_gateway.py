#!/usr/bin/env python3
import boto3
import time

def cleanup_transit_gateway_infrastructure():
    """Elimina toda la infraestructura Transit Gateway multi-región"""
    ec2_east = boto3.client('ec2', region_name='us-east-1')
    ec2_west = boto3.client('ec2', region_name='us-west-2')
    
    print("=== Limpiando infraestructura Transit Gateway ===")
    
    try:
        # 1. Eliminar TGW Peering
        print("\n--- Eliminando TGW Peering ---")
        try:
            peerings = ec2_east.describe_transit_gateway_peering_attachments()
            for peering in peerings['TransitGatewayPeeringAttachments']:
                if peering['State'] in ['available', 'pending']:
                    peering_id = peering['TransitGatewayAttachmentId']
                    print(f"Eliminando peering: {peering_id}")
                    ec2_east.delete_transit_gateway_peering_attachment(TransitGatewayAttachmentId=peering_id)
                    
                    # Esperar eliminación del peering
                    print("Esperando eliminación del peering...")
                    while True:
                        try:
                            response = ec2_east.describe_transit_gateway_peering_attachments(TransitGatewayAttachmentIds=[peering_id])
                            state = response['TransitGatewayPeeringAttachments'][0]['State']
                            if state == 'deleted':
                                break
                        except:
                            break  # Attachment no existe, eliminado
                        time.sleep(10)
        except Exception as e:
            print(f"Error eliminando peering: {e}")
        
        # 2. Eliminar TGW Attachments y VPCs por región
        regions = [
            ('us-east-1', ec2_east, ['VPC-East-1', 'VPC-East-2']),
            ('us-west-2', ec2_west, ['VPC-West-1', 'VPC-West-2'])
        ]
        
        tgw_ids = []
        
        for region, ec2_client, vpc_names in regions:
            print(f"\n--- Limpiando recursos en {region} ---")
            
            # Obtener TGW ID
            try:
                tgws = ec2_client.describe_transit_gateways()
                for tgw in tgws['TransitGateways']:
                    if tgw['State'] in ['available', 'pending']:
                        tgw_id = tgw['TransitGatewayId']
                        tgw_ids.append((region, ec2_client, tgw_id))
                        
                        # Eliminar VPC attachments
                        attachments = ec2_client.describe_transit_gateway_vpc_attachments(
                            Filters=[{'Name': 'transit-gateway-id', 'Values': [tgw_id]}]
                        )
                        
                        for attachment in attachments['TransitGatewayVpcAttachments']:
                            if attachment['State'] in ['available', 'pending']:
                                attachment_id = attachment['TransitGatewayAttachmentId']
                                print(f"Eliminando attachment: {attachment_id}")
                                ec2_client.delete_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attachment_id)
                        
                        # Esperar eliminación de attachments
                        attachment_ids = [att['TransitGatewayAttachmentId'] for att in attachments['TransitGatewayVpcAttachments'] if att['State'] in ['available', 'pending']]
                        if attachment_ids:
                            print("Esperando eliminación de attachments...")
                            for att_id in attachment_ids:
                                while True:
                                    try:
                                        response = ec2_client.describe_transit_gateway_vpc_attachments(TransitGatewayAttachmentIds=[att_id])
                                        state = response['TransitGatewayVpcAttachments'][0]['State']
                                        if state == 'deleted':
                                            break
                                    except:
                                        break  # Attachment no existe
                                    time.sleep(10)
            except Exception as e:
                print(f"Error eliminando attachments en {region}: {e}")
            
            # Eliminar VPCs específicas
            for vpc_name in vpc_names:
                try:
                    vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': [vpc_name]}])
                    
                    for vpc in vpcs['Vpcs']:
                        vpc_id = vpc['VpcId']
                        print(f"Limpiando {vpc_name}: {vpc_id}")
                        
                        # Terminar instancias
                        instances = ec2_client.describe_instances(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                        instance_ids = []
                        for reservation in instances['Reservations']:
                            for instance in reservation['Instances']:
                                if instance['State']['Name'] != 'terminated':
                                    instance_ids.append(instance['InstanceId'])
                                    print(f"Terminando instancia: {instance['InstanceId']}")
                                    ec2_client.terminate_instances(InstanceIds=[instance['InstanceId']])
                        
                        # Esperar terminación
                        if instance_ids:
                            print("Esperando terminación de instancias...")
                            ec2_client.get_waiter('instance_terminated').wait(InstanceIds=instance_ids)
                        
                        # Eliminar Security Groups
                        sgs = ec2_client.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                        for sg in sgs['SecurityGroups']:
                            if sg['GroupName'] != 'default':
                                print(f"Eliminando SG: {sg['GroupId']}")
                                ec2_client.delete_security_group(GroupId=sg['GroupId'])
                        
                        # Eliminar subredes
                        subnets = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                        for subnet in subnets['Subnets']:
                            print(f"Eliminando subred: {subnet['SubnetId']}")
                            ec2_client.delete_subnet(SubnetId=subnet['SubnetId'])
                        
                        # Desconectar y eliminar IGW
                        igws = ec2_client.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])
                        for igw in igws['InternetGateways']:
                            igw_id = igw['InternetGatewayId']
                            print(f"Desconectando IGW: {igw_id}")
                            ec2_client.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
                            print(f"Eliminando IGW: {igw_id}")
                            ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)
                        
                        # Eliminar VPC
                        print(f"Eliminando VPC: {vpc_id}")
                        ec2_client.delete_vpc(VpcId=vpc_id)
                        
                except Exception as e:
                    print(f"Error eliminando {vpc_name}: {e}")
        
        # 3. Eliminar Transit Gateways
        print("\n--- Eliminando Transit Gateways ---")
        for region, ec2_client, tgw_id in tgw_ids:
            try:
                print(f"Eliminando TGW {tgw_id} en {region}")
                ec2_client.delete_transit_gateway(TransitGatewayId=tgw_id)
            except Exception as e:
                print(f"Error eliminando TGW {tgw_id}: {e}")
        
        print("\n✅ Limpieza completada!")
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")

def main():
    cleanup_transit_gateway_infrastructure()

if __name__ == "__main__":
    main()