#!/usr/bin/env python3
import boto3
import time

def cleanup_juice_shop_infrastructure():
    """Elimina toda la infraestructura de Juice Shop"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    elbv2 = boto3.client('elbv2', region_name='us-east-1')
    wafv2 = boto3.client('wafv2', region_name='us-east-1')
    
    print("=== Limpiando infraestructura Juice Shop ===")
    
    try:
        # 1. Desasociar y eliminar Web ACL
        try:
            web_acls = wafv2.list_web_acls(Scope='REGIONAL')
            for web_acl in web_acls['WebACLs']:
                if web_acl['Name'] == 'JuiceShop-WebACL':
                    web_acl_arn = web_acl['ARN']
                    web_acl_id = web_acl['Id']
                    
                    # Obtener ALB para desasociar
                    albs = elbv2.describe_load_balancers()
                    for alb in albs['LoadBalancers']:
                        if alb['LoadBalancerName'] == 'JuiceShop-ALB':
                            try:
                                wafv2.disassociate_web_acl(ResourceArn=alb['LoadBalancerArn'])
                                print("Web ACL desasociada del ALB")
                            except:
                                pass
                    
                    # Eliminar Web ACL
                    wafv2.delete_web_acl(
                        Scope='REGIONAL',
                        Id=web_acl_id,
                        LockToken=wafv2.get_web_acl(Scope='REGIONAL', Id=web_acl_id)['LockToken']
                    )
                    print(f"Web ACL eliminada: {web_acl_arn}")
        except Exception as e:
            print(f"Error eliminando Web ACL: {e}")
        
        # 2. Eliminar ALB y Target Groups
        try:
            albs = elbv2.describe_load_balancers()
            for alb in albs['LoadBalancers']:
                if alb['LoadBalancerName'] == 'JuiceShop-ALB':
                    alb_arn = alb['LoadBalancerArn']
                    
                    # Eliminar listeners
                    listeners = elbv2.describe_listeners(LoadBalancerArn=alb_arn)
                    for listener in listeners['Listeners']:
                        elbv2.delete_listener(ListenerArn=listener['ListenerArn'])
                    
                    # Eliminar ALB
                    elbv2.delete_load_balancer(LoadBalancerArn=alb_arn)
                    print(f"ALB eliminado: {alb_arn}")
                    
                    # Esperar a que se elimine
                    time.sleep(10)
            
            # Eliminar Target Groups
            tgs = elbv2.describe_target_groups()
            for tg in tgs['TargetGroups']:
                if tg['TargetGroupName'] == 'JuiceShop-TG':
                    elbv2.delete_target_group(TargetGroupArn=tg['TargetGroupArn'])
                    print(f"Target Group eliminado: {tg['TargetGroupArn']}")
        except Exception as e:
            print(f"Error eliminando ALB/TG: {e}")
        
        # 3. Obtener VPC de Juice Shop
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['JuiceShop-VPC']}])
        
        for vpc in vpcs['Vpcs']:
            vpc_id = vpc['VpcId']
            print(f"Limpiando VPC: {vpc_id}")
            
            # Terminar instancias
            instances = ec2.describe_instances(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            instance_ids = []
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] != 'terminated':
                        instance_ids.append(instance['InstanceId'])
                        print(f"Terminando instancia: {instance['InstanceId']}")
                        ec2.terminate_instances(InstanceIds=[instance['InstanceId']])
            
            # Esperar terminación
            if instance_ids:
                print("Esperando terminación de instancias...")
                ec2.get_waiter('instance_terminated').wait(InstanceIds=instance_ids)
            
            # Eliminar Security Groups
            sgs = ec2.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            for sg in sgs['SecurityGroups']:
                if sg['GroupName'] != 'default':
                    print(f"Eliminando SG: {sg['GroupId']}")
                    ec2.delete_security_group(GroupId=sg['GroupId'])
            
            # Eliminar subredes
            subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            for subnet in subnets['Subnets']:
                print(f"Eliminando subred: {subnet['SubnetId']}")
                ec2.delete_subnet(SubnetId=subnet['SubnetId'])
            
            # Desconectar y eliminar IGW
            igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])
            for igw in igws['InternetGateways']:
                igw_id = igw['InternetGatewayId']
                print(f"Desconectando IGW: {igw_id}")
                ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
                print(f"Eliminando IGW: {igw_id}")
                ec2.delete_internet_gateway(InternetGatewayId=igw_id)
            
            # Eliminar VPC
            print(f"Eliminando VPC: {vpc_id}")
            ec2.delete_vpc(VpcId=vpc_id)
        
        print("\n✅ Limpieza completada!")
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")

def main():
    cleanup_juice_shop_infrastructure()

if __name__ == "__main__":
    main()